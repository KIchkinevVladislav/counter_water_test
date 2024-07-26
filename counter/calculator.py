from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import time

from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

from .models import Flat, Tariff

# нормативы потребления на квадратный метр
NORM_COLD_WATER = Decimal(6.935)
NORM_HOT_WATER = Decimal(4.745)


"""
Здесь есть ряд допущение, в частности, что всегда есть горячая вода, но в целом логика следующая:
- если нет счетчиков, считаем по нормативу потребления
- если просрочена поверка счетчика - по нормативу
- если нет показаний за текущий месяц - по нормативу
- если нет показаний за предыдущий, то считаем как новый счетчик
- только при наличии показаний на месяц расчета и предыдущий, считаем разницу
В бд по дому 1 есть записи для каждого из этих случаев.
"""
def calculator_payment(apartment_building_id: int, year: str, month: str):
    try:
        flats = Flat.objects.filter(apartment_building_id=apartment_building_id)
        initialize_progress(apartment_building_id, flats.count())

        tariffs = get_tariffs()
        current_date = datetime.now().date()
        year_month_key = f"{year}-{month.zfill(2)}"

        for flat in flats:
            if flat.calculations and year_month_key in flat.calculations:
                continue

            maintenance_cost = calculate_maintenance_cost(flat, tariffs['maintenance_of_common_property'])
            cold_water_usage, hot_water_usage = calculate_water_usage(flat, current_date, year, month)

            cold_water_price = cold_water_usage * tariffs['cold_water_for_flat']
            hot_water_price = hot_water_usage * tariffs['hot_water_for_flat']

            save_calculation(flat, year_month_key, maintenance_cost, cold_water_price, hot_water_price)
            update_progress(apartment_building_id)

    except ObjectDoesNotExist as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def initialize_progress(apartment_building_id: int, total_flats: int):
    progress = {'total': total_flats, 'completed': 0}
    save_calculation_progress(apartment_building_id, progress)


def get_tariffs():
    return {
        'maintenance_of_common_property': Tariff.objects.get(tariff_type='maintenance_of_common_property').price,
        'cold_water_for_flat': Tariff.objects.get(tariff_type='cold_water_for_flat').price,
        'hot_water_for_flat': Tariff.objects.get(tariff_type='hot_water_for_flat').price,
    }


def calculate_maintenance_cost(flat, maintenance_cost_per_square_meter):
    return flat.area * maintenance_cost_per_square_meter


def calculate_water_usage(flat, current_date, year, month):
    cold_water_usage = Decimal(0)
    hot_water_usage = Decimal(0)
    cold_water_counter_exists = False
    hot_water_counter_exists = False

    for counter in flat.water_counters.all():

        if counter.type_water_counter == 'cold':
            cold_water_counter_exists = True
        if counter.type_water_counter == 'hot':
            hot_water_counter_exists = True

        expiration_date = counter_expiration_date(counter)

        if current_date > expiration_date:
            if counter.type_water_counter == 'cold':
                cold_water_usage += NORM_COLD_WATER * flat.number_of_registered
            else:
                hot_water_usage += NORM_HOT_WATER * flat.number_of_registered
 
        else:
            usage = calculate_usage(flat, counter, year, month)

            if counter.type_water_counter == 'cold':
                cold_water_usage += usage
            else:
                hot_water_usage += usage
    
    if not cold_water_counter_exists:
        cold_water_usage += NORM_COLD_WATER * flat.number_of_registered

    if not hot_water_counter_exists:
        hot_water_usage += NORM_HOT_WATER * flat.number_of_registered

    return cold_water_usage, hot_water_usage


def calculate_usage(flat, counter, year, month):
    if counter.meters:
        if len(counter.meters) == 1:
            return single_meter_usage(flat, counter, year, month)
        else:
            return multiple_meter_usage(flat, counter, year, month)
    else:
        return NORM_COLD_WATER * flat.number_of_registered if counter.type_water_counter == 'cold' else NORM_HOT_WATER * flat.number_of_registered


def single_meter_usage(flat, counter, year, month):
    only_reading = counter.meters[0]
    only_reading_date = datetime.strptime(only_reading['meter_reading_date'], "%Y-%m-%d").date()
    if only_reading_date.year == int(year) and only_reading_date.month == int(month):
        return max(Decimal(only_reading['meter_reading_value']) - Decimal(0), Decimal(0))
    else:
        return NORM_COLD_WATER * flat.number_of_registered if counter.type_water_counter == 'cold' else NORM_HOT_WATER * flat.number_of_registered


def multiple_meter_usage(flat, counter, year, month):
    last = counter.meters[-1]
    last_reading_date = datetime.strptime(last['meter_reading_date'], "%Y-%m-%d").date()
    if last_reading_date.year == int(year) and last_reading_date.month == int(month):
        current_reading = Decimal(last['meter_reading_value'])
        previous = counter.meters[-2]
        last_reading = Decimal(previous['meter_reading_value'])
        return max(current_reading - last_reading, Decimal(0))
    else:
        return NORM_COLD_WATER * flat.number_of_registered if counter.type_water_counter == 'cold' else NORM_HOT_WATER * flat.number_of_registered


def save_calculation(flat, year_month_key, maintenance_cost, cold_water_price, hot_water_price):
    calculation_data = {
        year_month_key: {
            'maintenance_of_common_property': float(maintenance_cost),
            'cold_water_usage_price': float(cold_water_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'hot_water_usage_price': float(hot_water_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
    }
    if not flat.calculations:
        flat.calculations = calculation_data
    else:
        flat.calculations[year_month_key] = calculation_data[year_month_key]
    flat.save()


def update_progress(apartment_building_id: int):
    progress = get_calculation_progress(apartment_building_id)
    progress['completed'] += 1
    save_calculation_progress(apartment_building_id, progress)


def counter_expiration_date(counter):
    if counter.type_water_counter == 'cold':
        return counter.verification_date + timedelta(days=6*365)
    else:
        return counter.verification_date + timedelta(days=4*365)


def save_calculation_progress(apartment_building_id, progress):
    cache_key = f"calculation_progress_{apartment_building_id}"
    cache.set(cache_key, progress, timeout=60)


def get_calculation_progress(apartment_building_id):
    cache_key = f"calculation_progress_{apartment_building_id}"
    progress = cache.get(cache_key)
    if progress:
        return progress
    else:
        return {"status": "error", "message": "No progress found."}
    