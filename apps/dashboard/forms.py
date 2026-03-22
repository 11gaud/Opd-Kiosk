from django import forms
from apps.patients.models import Patient
from apps.services.models import Doctor

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

DASH_INPUT = (
    'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-blue-500'
)
DASH_SELECT = (
    'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
)
DASH_TEXTAREA = (
    'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none'
)


class PatientEditForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'hrn_number', 'first_name', 'middle_name', 'last_name',
            'birthdate', 'sex', 'phone_number', 'address',
            'civil_status', 'religion',
        ]
        widgets = {
            'hrn_number':   forms.TextInput(attrs={'class': DASH_INPUT}),
            'first_name':   forms.TextInput(attrs={'class': DASH_INPUT}),
            'middle_name':  forms.TextInput(attrs={'class': DASH_INPUT}),
            'last_name':    forms.TextInput(attrs={'class': DASH_INPUT}),
            'birthdate':    forms.DateInput(attrs={'class': DASH_INPUT, 'type': 'date'}),
            'sex':          forms.Select(attrs={'class': DASH_SELECT}),
            'phone_number': forms.TextInput(attrs={'class': DASH_INPUT}),
            'address':      forms.Textarea(attrs={'class': DASH_TEXTAREA, 'rows': 3}),
            'civil_status': forms.Select(attrs={'class': DASH_SELECT}),
            'religion':     forms.TextInput(attrs={'class': DASH_INPUT}),
        }


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = [
            'first_name', 'last_name', 'specialization',
            'room_number', 'schedule_notes', 'availability',
        ]
        widgets = {
            'first_name':     forms.TextInput(attrs={'class': DASH_INPUT}),
            'last_name':      forms.TextInput(attrs={'class': DASH_INPUT}),
            'specialization': forms.TextInput(attrs={'class': DASH_INPUT}),
            'room_number':    forms.TextInput(attrs={'class': DASH_INPUT}),
            'schedule_notes': forms.TextInput(attrs={'class': DASH_INPUT}),
            'availability':   forms.Select(attrs={'class': DASH_SELECT}),
        }


class DoctorScheduleDayForm(forms.Form):
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': DASH_INPUT}),
    )
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': DASH_INPUT}),
    )
    is_off = forms.BooleanField(required=False)
    note = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'class': DASH_INPUT, 'placeholder': 'Optional note'}),
    )


class WeeklyPatternForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for day in DAYS:
            self.fields[f'{day}_start'] = forms.TimeField(
                required=False,
                label=f'{day.capitalize()} Start',
                widget=forms.TimeInput(attrs={'type': 'time', 'class': DASH_INPUT}),
            )
            self.fields[f'{day}_end'] = forms.TimeField(
                required=False,
                label=f'{day.capitalize()} End',
                widget=forms.TimeInput(attrs={'type': 'time', 'class': DASH_INPUT}),
            )
            self.fields[f'{day}_off'] = forms.BooleanField(
                required=False,
                label='Day Off',
            )
