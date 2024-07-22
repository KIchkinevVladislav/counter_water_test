from rest_framework import status
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.db.models import Count

from .models import ApartmentBuilding, Flat, WaterCounter
from .serializers import (ApartmentBuildingSerializer, 
                        FlatSerializer, 
                        ApartmentBuildingCreateSerializer, 
                        FlatCreateSerializer,
                        WaterCounterCreateSerializer,
                        MeterReadingSerializer,
                        CalculatorPaymentSerializer,)
from .calculator import get_calculation_progress
from .task import calculate_payment_task


class FlatFilter(django_filters.FilterSet):
    """
    Фильтрация для возможности получения только тех квартив, в которых нет счетчиков воды
    """
    no_water_counters = django_filters.BooleanFilter(method='filter_no_water_counters', label='Отсутствие счетчиков')

    class Meta:
        model = Flat
        fields = []

    def filter_no_water_counters(self, queryset, name, value):
        if value:
            return queryset.annotate(
                has_counters=Count('water_counters')
            ).filter(has_counters=0)
        return queryset
    

@extend_schema(
        tags=['Data'],
        description='Получение данны о доме, находящихся в нем квартирах и переданных показаниях',
        parameters=[
            OpenApiParameter('ordering', description='Поле для сортировки, можно указать номер квартиры, например, "number" или "-number" для убывания.', required=False, type=str),
            OpenApiParameter('no_water_counters', description='Получить только те квартиры, где нет счетчиков воды', required=False, type=bool),
        ]
    )
class ApartmentBuildingDetailView(generics.RetrieveAPIView):
    queryset = ApartmentBuilding.objects.all()
    serializer_class = ApartmentBuildingSerializer
    ordering_fields = ['flats__number']
    ordering = ['flats__number']

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        building = self.get_object()
            
        flats = Flat.objects.filter(apartment_building=building)
            
        flats_filtered = FlatFilter(request.GET, queryset=flats).qs

        ordering = request.GET.get('ordering', 'number')
        if ordering:
            flats_filtered = flats_filtered.order_by(ordering)

        flat_serializer = FlatSerializer(flats_filtered, many=True)

        building_data = ApartmentBuildingSerializer(building).data
        building_data['flats'] = flat_serializer.data

        return Response(building_data)
    

@extend_schema(
    tags=['Data'],
    request=ApartmentBuildingCreateSerializer,
    description='Внесение в бд записи об объекте многоквартирного жилого дома',
    examples=[
                OpenApiExample(
                    'Example Request',
                    value={
                        "total_area": "11252.40",
                        "address": "Санкт-Петербург, ул. Почтамтская, д. 2/9"
                    }
                )
            ]
)
class ApartmentBuildingCreateView(generics.CreateAPIView):
    queryset = ApartmentBuilding.objects.all()
    serializer_class = ApartmentBuildingCreateSerializer


@extend_schema(
    tags=['Data'],
    request=FlatCreateSerializer,
    description='Внесение в бд записи об объекте квартиры',
    examples=[
                OpenApiExample(
                    'Example Request',
                    value={
                        "number": 101,
                        "number_of_registered": 2, 
                        "area": "45.00",
                        "apartment_building": 1
                    }
                )
            ]
)
class FlatCreateView(generics.CreateAPIView):
    queryset = Flat.objects.all()
    serializer_class = FlatCreateSerializer


@extend_schema(
    tags=['Data'],
    request=WaterCounterCreateSerializer,
    description='Внесение в бд записи о счетчике',
    examples=[
                OpenApiExample(
                    'Example Request',
                    value={
                        "serial_number": "1234567890",
                        "verification_date": "2024-01-01",
                        "type_water_counter": "cold",
                        "apartment_building_id": 1,
                        "flat_number": 5
                    }
                )
            ]
)
class WaterCounterCreateView(generics.CreateAPIView):
    queryset = WaterCounter.objects.all()
    serializer_class = WaterCounterCreateSerializer


@extend_schema(
    tags=['Data'],
    request=MeterReadingSerializer,
    description='Передача показаний счетчика воды',
    examples=[
        OpenApiExample(
            'Example Request',
            value={
                "serial_number": "1234567890",
                "meter_reading_value": 110
            }
        )
    ],
)
class AddMeterReadingView(generics.CreateAPIView):
    serializer_class = MeterReadingSerializer


@extend_schema(
    tags=['Calculator'],
    request=CalculatorPaymentSerializer,
    description='Расчет платы за водоснабжение и содержание общего имущества. В настоящее время расчет возможен только для 2024 года',
    examples=[
        OpenApiExample(
            'Example Request',
            value={
                "apartment_building_id": 1,
                "year": "2024",
                "month": "07"
            }
        )
    ],
)
class CalculatePaymentView(APIView):
    def post(self, request):
        serializer = CalculatorPaymentSerializer(data=request.data)
        if serializer.is_valid():
            apartment_building_id = serializer.validated_data['apartment_building_id']
            year = serializer.validated_data['year']
            month = serializer.validated_data['month']
            
            # Запускаем задачу в Celery
            calculate_payment_task.delay(apartment_building_id, year, month)
            
            return Response({"status": "success", "message": "Расчет запущен."}, status=status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Calculator'],
    description='Получение данных о прогрессе расчета кварплаты. Передайте ID дома, для которого запущен расчет',
)
class CalculationProgressView(APIView):
    def get(self, request, apartment_building_id, *args, **kwargs):
        if not ApartmentBuilding.objects.filter(id=apartment_building_id).exists():
            return Response({"status": "error", "message": "Apartment building with this ID does not exist."}, status=status.HTTP_404_NOT_FOUND)
        
        progress = get_calculation_progress(apartment_building_id)
        if isinstance(progress, dict) and 'status' in progress and progress['status'] == 'error':
            return Response(progress, status=status.HTTP_404_NOT_FOUND)
        
        return Response(progress, status=status.HTTP_200_OK)
