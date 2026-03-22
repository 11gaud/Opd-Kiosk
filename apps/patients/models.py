from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class Patient(TimeStampedModel):
    class Sex(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    class CivilStatus(models.TextChoices):
        SINGLE = 'single', 'Single'
        MARRIED = 'married', 'Married'
        WIDOWED = 'widowed', 'Widowed'
        SEPARATED = 'separated', 'Separated'

    hrn_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name='HRN Number')
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    birthdate = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    civil_status = models.CharField(max_length=20, choices=CivilStatus.choices, blank=True)
    religion = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['hrn_number']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)

    @property
    def age(self):
        today = timezone.localdate()
        born = self.birthdate
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
