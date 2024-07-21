from rest_framework import generics
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Count, Q

from .models import ApartmentBuilding, Flat
from .serializers import ApartmentBuildingSerializer, ApartmentBuildingListSerializer, FlatSerializer


class ApartmentBuildingListView(generics.ListAPIView):
    queryset = ApartmentBuilding.objects.all()
    serializer_class = ApartmentBuildingListSerializer


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
    

class ApartmentBuildingDetailView(generics.RetrieveAPIView):
    queryset = ApartmentBuilding.objects.all()
    serializer_class = ApartmentBuildingSerializer
    ordering_fields = ['flats__number']
    ordering = ['flats__number']

    @extend_schema(
        parameters=[
            OpenApiParameter('ordering', description='Поле для сортировки, можно указать номер квартиры, например, "number" или "-number" для убывания.', required=False, type=str),
            OpenApiParameter('no_water_counters', description='Получить только те квартиры, где нет счетчиков воды', required=False, type=bool),
        ]
    )

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