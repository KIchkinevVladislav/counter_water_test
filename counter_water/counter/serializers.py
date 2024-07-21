from rest_framework import serializers
from .models import ApartmentBuilding, Flat, WaterCounter


class WaterCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterCounter
        fields = ['serial_number', 'verification_date', 'type_water_counter', 'meters']


class FlatSerializer(serializers.ModelSerializer):
    water_counters = WaterCounterSerializer(many=True)

    class Meta:
        model = Flat
        fields = ['number', 'number_of_registered', 'area', 'water_counters']


class ApartmentBuildingSerializer(serializers.ModelSerializer):
    flats = FlatSerializer(many=True, read_only=True)

    class Meta:
        model = ApartmentBuilding
        fields = ['total_area', 'address', 'flats']


class ApartmentBuildingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentBuilding
        fields = ['total_area', 'address']

    def validate_total_area(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total area must be a positive number.")
        return value

    def create(self, validated_data):
        return ApartmentBuilding.objects.create(**validated_data)


class FlatCreateSerializer(serializers.ModelSerializer):
    apartment_building = serializers.PrimaryKeyRelatedField(queryset=ApartmentBuilding.objects.all())

    class Meta:
        model = Flat
        fields = ['number', 'number_of_registered', 'area', 'apartment_building']

    def validate_number_of_registered(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of registered must be a positive number.")
        return value
    

class WaterCounterCreateSerializer(serializers.ModelSerializer):
    apartment_building_id = serializers.PrimaryKeyRelatedField(queryset=ApartmentBuilding.objects.all(), write_only=True)
    flat_number = serializers.IntegerField(write_only=True)

    type_water_counter = serializers.ChoiceField(choices=WaterCounter.TYPE_COUNTER, error_messages={
        'invalid_choice': "Invalid type of water counter. Choose from 'cold' or 'hot'."
    })

    class Meta:
        model = WaterCounter
        fields = ['serial_number', 'verification_date', 'type_water_counter', 'apartment_building_id', 'flat_number']

    def validate(self, data):
        apartment_building_id = data.get('apartment_building_id')
        flat_number = data.get('flat_number')

        try:
            flat = Flat.objects.get(apartment_building_id=apartment_building_id, number=flat_number)
            data['flat'] = flat
        except Flat.DoesNotExist:
            raise serializers.ValidationError("The specified flat number does not exist in the given building.")
        
        return data

    def create(self, validated_data):
        validated_data.pop('apartment_building_id')
        validated_data.pop('flat_number')
        return super().create(validated_data)

# class ApartmentBuildingListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ApartmentBuilding
#         fields = ['id', 'address']