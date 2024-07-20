from django.contrib import admin

from .models import ApartmentBuilding, Flat, Tariff,  WaterCounter


class FlatInline(admin.TabularInline):
    model = Flat
    extra = 1


class WaterCounterInline(admin.TabularInline):
    model =  WaterCounter
    extra = 1


@admin.register(ApartmentBuilding)
class ApartmentBuildingAdmin(admin.ModelAdmin):
    inlines = [FlatInline]
    list_display = ('id', 'total_area', 'address')
    fields = ('total_area', 'address')
    list_filter = ('address',)
    search_fields = ('address',)
    ordering = ('address',)


@admin.register(Flat)
class FlatAdmin(admin.ModelAdmin): 
    inlines = [WaterCounterInline]   
    list_display = ('id', 'number', 'area', 'apartment_building')
    fields = ('number', 'area', 'apartment_building', 'number_of_registered')
    list_filter = ('apartment_building',)
    search_fields = ('number', 'apartment_building__address')
    ordering = ('number',)


@admin.register(Tariff)
class TafiffAdmin(admin.ModelAdmin):
    list_display = ('id', 'tariff_type', 'price')
    fields = ('tariff_type', 'price')
    list_filter = ('tariff_type',)
    search_fields = ('tariff_type',)


@admin.register(WaterCounter)
class WaterCounerAdmin(admin.ModelAdmin):
    list_display = ('id', 'serial_number', 'verification_date', 'type_water_counter', 'flat', 'tariff')
    fields = ('serial_number', 'verification_date', 'type_water_counter', 'meters', 'flat', 'tariff')
    list_filter = ('type_water_counter', 'flat', 'tariff', 'verification_date',)
    search_fields = ('serial_number', 'flat__number', 'tariff', 'verification_date',)
    date_hierarchy = 'verification_date'
    ordering = ('serial_number',)
