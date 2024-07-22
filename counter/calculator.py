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

        # реализуем храние прогресса в кэше
        total_flats = flats.count()
        progress = {
            'total': total_flats,
            'completed': 0
        }
        save_calculation_progress(apartment_building_id, progress)

        tariff_common = Tariff.objects.get(tariff_type='maintenance_of_common_property')
        tariff_cold_water = Tariff.objects.get(tariff_type='cold_water_for_flat')
        tariff_hot_water = Tariff.objects.get(tariff_type='hot_water_for_flat')

        maintenance_cost_per_square_meter = tariff_common.price
        cold_water_price = tariff_cold_water.price
        hot_water_price = tariff_hot_water.price   

        current_date = datetime.now().date() 

        year_month_key = f"{year}-{month.zfill(2)}"

        for flat in flats:
            
            if flat.calculations and year_month_key in flat.calculations:
                continue

            # расчет платы за содержание имущества
            maintenance_cost = flat.area * maintenance_cost_per_square_meter

            cold_water_usage = Decimal(0)
            hot_water_usage = Decimal(0)

            cold_water_counter_exists = False
            hot_water_counter_exists = False

            for counter in flat.water_counters.all():
                # Определяем время эксплуатации счетчика по типу
                if counter.type_water_counter == 'cold':
                    cold_water_counter_exists = True
                    expiration_date = counter.verification_date + timedelta(days=6*365)
                else:
                    hot_water_counter_exists = True
                    expiration_date = counter.verification_date + timedelta(days=4*365)

                if current_date <= expiration_date:
                    # если не просрочен счетчик
                    if counter.meters:
                    # если существуют показания вообще
                        if len(counter.meters) == 1:
                            # Если есть только одно показание
                            only_reading = counter.meters[0]
                            only_reading_date = datetime.strptime(only_reading['meter_reading_date'], "%Y-%m-%d").date()
                            if only_reading_date.year == int(year) and only_reading_date.month == int(month):
                                # Показание есть за текущий месяц
                                current_reading = Decimal(only_reading['meter_reading_value'])
                                last_reading = Decimal(0)  # Предыдущие показания считаем равными 0 (новый счетчик)
                                if counter.type_water_counter == 'cold':
                                    cold_water_usage += max(current_reading - last_reading, Decimal(0))
                                else:
                                    hot_water_usage += max(current_reading - last_reading, Decimal(0))
                            else:
                                # Если это показаний не за текущий месяц, считаем по нормативу
                                if counter.type_water_counter == 'cold':
                                    cold_water_usage += NORM_COLD_WATER * flat.number_of_registered
                                else:
                                    hot_water_usage += NORM_HOT_WATER * flat.number_of_registered
                        else:
                            # проверяем что за последние показания
                            last = counter.meters[-1]
                            last_reading_date = datetime.strptime(last['meter_reading_date'], "%Y-%m-%d").date()
                            
                            # если они совпадают с месяцев расчета, то запоминаем и берем предыдущие
                            if last_reading_date.year == int(year) and last_reading_date.month == int(month):
                                current_reading = Decimal(last['meter_reading_value'])
                                previous = counter.meters[-2]
                                last_reading = Decimal(previous['meter_reading_value'])

                                # считаем разницу
                                if counter.type_water_counter == 'cold':
                                    cold_water_usage += max(current_reading - last_reading, Decimal(0))
                                else:
                                    hot_water_usage += max(current_reading - last_reading, Decimal(0))
                            else: 
                                # если последни не за текущий месяц, то по нормативу
                                if counter.type_water_counter == 'cold':
                                    cold_water_usage += NORM_COLD_WATER * flat.number_of_registered
                                else:
                                    hot_water_usage += NORM_HOT_WATER * flat.number_of_registered
                    else:
                        # если нет показаний вообще, никогда не передавались
                        if counter.type_water_counter == 'cold':
                            cold_water_usage += NORM_COLD_WATER * flat.number_of_registered
                        else:
                            hot_water_usage += NORM_HOT_WATER * flat.number_of_registered
                else:
                    # если счетчик просрочен
                    if counter.type_water_counter == 'cold':
                        cold_water_usage += NORM_COLD_WATER * flat.number_of_registered
                    else:
                        hot_water_usage += NORM_HOT_WATER * flat.number_of_registered

            # если вообще нет счетчиков
            if not cold_water_counter_exists:
                cold_water_usage += NORM_COLD_WATER * flat.number_of_registered

            if not hot_water_counter_exists:
                hot_water_usage += NORM_HOT_WATER * flat.number_of_registered

            cold_water_usage_price = cold_water_usage * cold_water_price
            hot_water_usage_price = hot_water_usage * hot_water_price

            cold_water_usage_price = cold_water_usage_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            hot_water_usage_price = hot_water_usage_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            calculation_data = {
                year_month_key: {
                    'maintenance_of_common_property': float(maintenance_cost),
                    'cold_water_usage_price': float(cold_water_usage_price),
                    'hot_water_usage_price': float(hot_water_usage_price)
                }
            }

            if not flat.calculations:
                flat.calculations = calculation_data
            else:
                flat.calculations[year_month_key] = calculation_data[year_month_key]

            flat.save()
            progress['completed'] += 1
            save_calculation_progress(apartment_building_id, progress)

    except ObjectDoesNotExist as e:
        return {"status": "error", "message": str(e)}    
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
    