from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect


def staff_required(view_func):
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='dashboard:login',
    )(view_func)



def has_module_access(user, module):
    """Return True if user may access the given module slug."""
    if user.is_superuser:
        return True
    try:
        return user.profile.can_access(module)
    except Exception:
        return True  # no profile → allow by default


def module_required(module):
    """Decorator that blocks access when the user lacks the given module permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_module_access(request.user, module):
                messages.error(request, "You don't have permission to access that section.")
                return redirect('dashboard:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
