from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from django.db.models import Count

from .models import ApartmentBuilding, Flat
from .serializers import ApartmentBuildingSerializer, FlatSerializer, ApartmentBuildingCreateSerializer, FlatCreateSerializer


# class ApartmentBuildingListView(generics.ListAPIView):
#     queryset = ApartmentBuilding.objects.all()
#     serializer_class = ApartmentBuildingListSerializer


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
    request=ApartmentBuildingCreateSerializer,
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    

@extend_schema(
    request=ApartmentBuildingCreateSerializer,
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)