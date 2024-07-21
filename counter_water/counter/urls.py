from django.urls import path
from .views import ApartmentBuildingDetailView

app_name = 'counter'

urlpatterns = [
    # path('apartment-buildings/', ApartmentBuildingListView.as_view(), name='apartment-building-list'),
    path('apartment-building/<int:pk>/', ApartmentBuildingDetailView.as_view(), name='apartment-building-detail'),
]

