from celery import shared_task
from .calculator import calculator_payment

@shared_task
def calculate_payment_task(apartment_building_id, year, month):
    return calculator_payment(apartment_building_id, year, month)