from django.urls import path
from .views import (ApartmentBuildingDetailView, 
                    ApartmentBuildingCreateView, 
                    FlatCreateView,
                    WaterCounterCreateView,
                    AddMeterReadingView,
                    CalculatePaymentView,
                    CalculationProgressView,)

app_name = 'counter'

urlpatterns = [
    # path('apartment-buildings/', ApartmentBuildingListView.as_view(), name='apartment-building-list'),
    path('apartment-building/<int:pk>/', ApartmentBuildingDetailView.as_view(), name='apartment_building_detail'),
    path('create/apartment-building/', ApartmentBuildingCreateView.as_view(), name='apartment_building_create'),
    path('create/flat/', FlatCreateView.as_view(), name='flat-create'),
    path('create/water_counter/', WaterCounterCreateView.as_view(), name='water_counter_create'),
    path('add-meter-reading', AddMeterReadingView.as_view(), name='add_meter_reading'),
    path('calculate-payment', CalculatePaymentView.as_view(), name='calculate_payment'),
    path('calculate-progress/<int:apartment_building_id>/', CalculationProgressView.as_view(), name='calculate_progress'),
]


