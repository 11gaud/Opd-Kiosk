from django import template
from apps.dashboard.decorators import has_module_access

register = template.Library()


@register.filter
def can_access(user, module):
    """Usage: {% if request.user|can_access:'queue' %}"""
    return has_module_access(user, module)


@register.filter
def get_field(form, field_name):
    """Render a form field by name: {{ form|get_field:'can_access_queue' }}"""
    return form[field_name]
