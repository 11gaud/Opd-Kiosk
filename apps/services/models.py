from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone
from apps.core.models import TimeStampedModel


class Service(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=100)
    prefix = models.CharField(max_length=10)
    icon = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.label


class Doctor(TimeStampedModel):
    class Availability(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNAVAILABLE = 'unavailable', 'Unavailable'
        ON_LEAVE = 'on_leave', 'On Leave'

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=150)
    room_number = models.CharField(max_length=20, blank=True)
    schedule_notes = models.CharField(max_length=200, blank=True)
    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
    )

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} — {self.specialization}"

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"


class QueueCounter(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='counters')
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)
    currently_serving = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('service', 'date')]
        indexes = [
            models.Index(fields=['service', 'date']),
        ]

    def __str__(self):
        return f"{self.service.prefix} — {self.date} — #{self.count}"

    @classmethod
    def next_number(cls, service):
        today = timezone.localdate()
        with db_transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(
                service=service,
                date=today,
                defaults={'count': 0, 'currently_serving': 0},
            )
            counter.count += 1
            counter.save(update_fields=['count'])
            return f"{service.prefix}-{counter.count:03d}"

    @classmethod
    def call_next(cls, service):
        today = timezone.localdate()
        with db_transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(
                service=service,
                date=today,
                defaults={'count': 0, 'currently_serving': 0},
            )
            if counter.currently_serving < counter.count:
                counter.currently_serving += 1
                counter.save(update_fields=['currently_serving'])
        return counter

    @classmethod
    def reset_today(cls, service):
        today = timezone.localdate()
        cls.objects.filter(service=service, date=today).update(count=0, currently_serving=0)


class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_off = models.BooleanField(default=False)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [('doctor', 'date')]
        ordering = ['date']

    def __str__(self):
        return f"{self.doctor.full_name} — {self.date}"
