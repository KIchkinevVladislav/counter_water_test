from rest_framework import serializers
from .models import ApartmentBuilding, Flat, WaterCounter


class WaterCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterCounter
        fields = ['serial_number', 'verification_date', 'type_water_counter', 'meters']

class FlatSerializer(serializers.ModelSerializer):
    water_counters = WaterCounterSerializer(many=True, read_only=True)

    class Meta:
        model = Flat
        fields = ['number', 'number_of_registered', 'area', 'water_counters']

class ApartmentBuildingSerializer(serializers.ModelSerializer):
    flats = FlatSerializer(many=True, read_only=True)

    class Meta:
        model = ApartmentBuilding
        fields = ['total_area', 'address', 'flats']


class ApartmentBuildingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentBuilding
        fields = ['id', 'address']