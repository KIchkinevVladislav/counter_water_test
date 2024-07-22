import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


from .models import ApartmentBuilding, Flat, WaterCounter
from .serializers import FlatCreateSerializer



class ApartmentBuildingDetailViewTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        
        self.apartment_building = ApartmentBuilding.objects.create(
            total_area = 1256.80,
            address = 'Санкт-Петербург, Гражданский проспект, д. 14'
        )
        
        self.flat_withoutcounter = Flat.objects.create(
            apartment_building=self.apartment_building,
            number='101',
            area = 56.12,
            number_of_registered = 1,
            calculations = {}
        )
        self.flat_with_counter = Flat.objects.create(
            apartment_building=self.apartment_building,
            number='102',
            area = 56.12,
            number_of_registered = 1,
            calculations = {}
        )
        WaterCounter.objects.create(
            flat=self.flat_with_counter,
            verification_date = '2024-12-20',
            serial_number = '12345678',
            type_water_counter = 'cold',
            meters = []
        )
    
    def test_get_apartment_building_details(self):
        url = reverse('counter:apartment_building_detail', args=[self.apartment_building.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['flats']), 2)

    def test_filter_flats_without_water_counters(self):
        url = reverse('counter:apartment_building_detail', args=[self.apartment_building.id])
        response = self.client.get(url, {'no_water_counters': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        
        flats = data['flats']
        self.assertEqual(len(flats), 1)
        self.assertEqual(flats[0]['number'], 101)

    def test_get_apartment_building_details_not_exist(self):
        url = reverse('counter:apartment_building_detail', args=[2])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class FlatCreateSerializerTests(TestCase):

    def setUp(self):
        self.apartment_building = ApartmentBuilding.objects.create(
            total_area = 1256.80,
            address = 'Санкт-Петербург, Гражданский проспект, д. 14'
        )

        self.flat_withoutcounter = Flat.objects.create(
            apartment_building=self.apartment_building,
            number='102',
            area = 56.12,
            number_of_registered = 1,
            calculations = {}
        )

    def test_valid_flat_data(self):
        data = {
            'number': 101,
            'number_of_registered': 2,
            'area': '45.00',
            'apartment_building': self.apartment_building.id
        }
        serializer = FlatCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        flat = serializer.save()
        self.assertEqual(flat.number, 101)
        self.assertEqual(flat.number_of_registered, 2)
        self.assertEqual(flat.area, Decimal('45.00'))
        self.assertEqual(flat.apartment_building, self.apartment_building)

    def test_invalid_number_of_registered(self):
        data = {
            'number': 101,
            'number_of_registered': 0,
            'area': '45.00',
            'apartment_building': self.apartment_building.id
        }
        serializer = FlatCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('number_of_registered', serializer.errors)
        self.assertEqual(serializer.errors['number_of_registered'][0], "Number of registered must be a positive number.")


    def test_number_if_exist(self):
        data = {
            'number': 102,
            'number_of_registered': 1,
            'area': '45.00',
            'apartment_building': self.apartment_building.id
        }
        serializer = FlatCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
