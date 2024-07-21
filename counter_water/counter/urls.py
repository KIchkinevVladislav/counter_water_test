from django.urls import path
from .views import (ApartmentBuildingDetailView, 
                    ApartmentBuildingCreateView, 
                    FlatCreateView,
                    WaterCounterCreateView,
                    AddMeterReadingView)

app_name = 'counter'

urlpatterns = [
    # path('apartment-buildings/', ApartmentBuildingListView.as_view(), name='apartment-building-list'),
    path('apartment-building/<int:pk>/', ApartmentBuildingDetailView.as_view(), name='apartment-building-detail'),
    path('create/apartment-building/', ApartmentBuildingCreateView.as_view(), name='apartment-building-create'),
    path('create/flat/', FlatCreateView.as_view(), name='flat-create'),
    path('create/water_counter/', WaterCounterCreateView.as_view(), name='water_counter-create'),
    path('add-meter-reading', AddMeterReadingView.as_view(), name='add-meter-reading'),
]


