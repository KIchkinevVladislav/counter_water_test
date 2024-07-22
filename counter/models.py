from django.db import models


class ApartmentBuilding(models.Model):
    """
    Class describing the fields of the "ApartmentBuilding" object 
    in the database
    """
    total_area = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Общая площадь дома')
    address = models.CharField(max_length=256, unique=True, verbose_name='Адрес дома')

    def __str__(self) -> str:
        return f'Многоквартирный жилой дом, расположенный по адресу: {self.address}'    
    
    class Meta():
        verbose_name = 'Многоквартирный жилой дом'
        verbose_name_plural = 'Многоквартирные жилые дома'


class Flat(models.Model):
    """
    Class describing the fields of the "Flat" object 
    in the database
    """
    number = models.PositiveIntegerField(verbose_name='Номер квартиры')
    # количество зарегистрированных нужно для расчета по нормативу, считаем всегда зарегистрированным собственника
    number_of_registered = models.PositiveIntegerField(default=1, verbose_name="Количество зарегистрированных лиц")
    area = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Площадь квартиры')
    apartment_building = models.ForeignKey(to=ApartmentBuilding, on_delete=models.CASCADE, verbose_name='Дом, где расположена квартира', related_name='flats')
    calculations = models.JSONField(default=dict, blank=True, verbose_name="Расчеты")
    
    def __str__(self) -> str:
        return f'Квартира № {self.number}, по адресу: {self.apartment_building.address}'
    
    class Meta():
        constraints = [
            models.UniqueConstraint(fields=['number', 'apartment_building'], name='unique_flat_in_building')
        ]

        verbose_name = 'Квартира'
        verbose_name_plural = 'Квартиры'


class Tariff(models.Model):
    """
    Class describing the fields of the "Tariff" object 
    in the database
    """
    TYPE_TARIFF = (
        ('cold_water_for_flat', 'холодное водоснабжение в квартире'),
        ('hot_water_for_flat', 'горячее водоснабжение в квартире'),
        ('maintenance_of_common_property', 'содержание общего имущества'),
    )
    tariff_type = models.CharField(max_length=124, choices=TYPE_TARIFF, verbose_name='Тип тарифа водоснабжения')
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Стоимость одного кубического метра')

    def __str__(self) -> str:
        return f'Тип тарифа: {self.get_tariff_type_display()}. Стоимость одного кубического метра {self.price}'

    class Meta():
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'


class WaterCounter(models.Model):
    """
    Class describing the fields of the "WaterCouner" object 
    in the database
    """
    TYPE_COUNTER = (
        ('cold', 'холодное'),
        ('hot', 'горячее'),
    )
    serial_number = models.CharField(max_length=10, verbose_name='Серийный номер счетчика')
    verification_date = models.DateField(verbose_name='Дата поверки')
    type_water_counter = models.CharField(max_length=8, choices=TYPE_COUNTER, verbose_name='Тип водоснабжения')
    meters = models.JSONField(default=list, null=True, blank=True, verbose_name='Показания счетчика')
    flat = models.ForeignKey(to=Flat, on_delete=models.CASCADE, verbose_name='Квартира', related_name='water_counters')

    MAX_METERS = 12 

    def add_meters(self,  meter_reading_date: str, meter_reading_value: int, max_meters: int = MAX_METERS):
        new_reading = {'meter_reading_date':  meter_reading_date, 'meter_reading_value': meter_reading_value}
        self.meters.append(new_reading)
        if len(self.meters) >  max_meters:
            self.meters.pop(0)
        self.save()

    def __str__(self) -> str:
        return f'Счетчик воды № {self.serial_number}. Тип водоснабжения: {self.get_type_water_counter_display()}'
    
    class Meta():
        constraints = [
            models.UniqueConstraint(fields=['serial_number', 'flat'], name='unique_water_counter_in_flat')
        ]

        verbose_name = 'Счетчик'
        verbose_name_plural = 'Счетчики'
