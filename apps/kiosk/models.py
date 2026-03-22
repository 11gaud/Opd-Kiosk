from django.db import models
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient
from apps.services.models import Service, Doctor


class Transaction(TimeStampedModel):
    class PatientType(models.TextChoices):
        NEW = 'new', 'New Patient'
        EXISTING = 'existing', 'Existing Patient'

    class PaymentMethod(models.TextChoices):
        SELFPAY = 'selfpay', 'Self-Pay'
        HMO = 'hmo', 'HMO / Insurance'
        CORPORATE = 'corporate', 'Corporate'
        GOVERNMENT = 'government_assistance', 'Government Assistance'

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='transactions')
    services = models.ManyToManyField(Service, related_name='transactions')
    doctor = models.ForeignKey(Doctor, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')

    patient_type = models.CharField(max_length=10, choices=PatientType.choices)
    payment_method = models.CharField(max_length=25, choices=PaymentMethod.choices)

    # Payment sub-details (filled depending on payment_method)
    hmo_provider = models.CharField(max_length=100, blank=True)
    hmo_membership_id = models.CharField(max_length=100, blank=True)
    corporate_company = models.CharField(max_length=100, blank=True)
    government_program = models.CharField(max_length=100, blank=True)

    signature_image = models.ImageField(upload_to='signatures/%Y/%m/%d/', null=True, blank=True)
    queue_numbers = models.JSONField(default=dict)
    kiosk_identifier = models.CharField(max_length=50, blank=True)
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Txn #{self.pk} — {self.patient} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class QueueEntry(models.Model):
    class Status(models.TextChoices):
        WAITING    = 'waiting',    'Waiting'
        CALLED     = 'called',     'Called'
        PROCESSING = 'processing', 'Processing'
        DONE       = 'done',       'Done'
        NO_SHOW    = 'no_show',    'No Show'

    transaction  = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='queue_entries')
    service      = models.ForeignKey(Service, on_delete=models.CASCADE)
    queue_number = models.CharField(max_length=20)
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    arrived_at   = models.DateTimeField(auto_now_add=True)
    called_at    = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    done_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['arrived_at']
        indexes = [models.Index(fields=['service', 'queue_number'])]

    def __str__(self):
        return f"{self.queue_number} — {self.transaction.patient} — {self.get_status_display()}"
