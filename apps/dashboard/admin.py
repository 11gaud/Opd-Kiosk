from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from apps.dashboard.models import UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Module Access'
    verbose_name_plural = 'Module Access'
    fieldsets = (
        ('Dashboard Modules', {
            'fields': (
                'can_access_queue',
                'can_access_patients',
                'can_access_doctors',
                'can_access_transactions',
                'can_access_reports',
            ),
            'description': 'Select which dashboard modules this user can access. Superusers always have full access.',
        }),
    )


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)


# Re-register User with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
