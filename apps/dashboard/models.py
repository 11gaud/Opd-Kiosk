from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

MODULE_FIELDS = [
    'can_access_queue',
    'can_access_patients',
    'can_access_doctors',
    'can_access_transactions',
    'can_access_reports',
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    can_access_queue        = models.BooleanField(default=True)
    can_access_patients     = models.BooleanField(default=True)
    can_access_doctors      = models.BooleanField(default=True)
    can_access_transactions = models.BooleanField(default=True)
    can_access_reports      = models.BooleanField(default=True)

    def __str__(self):
        return f'Profile({self.user.username})'

    def can_access(self, module):
        return getattr(self, f'can_access_{module}', True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
