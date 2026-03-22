from django import forms

INPUT_CLASS = 'w-full border-2 border-slate-200 focus:border-blue-500 rounded-xl px-4 py-3 text-base outline-none transition bg-white text-slate-800 placeholder-slate-400'
SELECT_CLASS = 'w-full appearance-none border-2 border-slate-200 focus:border-blue-500 rounded-xl pl-4 pr-10 py-3 text-base outline-none transition bg-white text-slate-800 cursor-pointer'
TEXTAREA_CLASS = 'w-full border-2 border-slate-200 focus:border-blue-500 rounded-xl px-4 py-3 text-base outline-none transition bg-white text-slate-800 placeholder-slate-400 resize-none'

CIVIL_STATUS_CHOICES = [
    ('', '-- Select --'),
    ('single', 'Single'),
    ('married', 'Married'),
    ('widowed', 'Widowed'),
    ('separated', 'Separated'),
]

SEX_CHOICES = [
    ('', '-- Select --'),
    ('M', 'Male'),
    ('F', 'Female'),
]

PAYMENT_CHOICES = [
    ('selfpay', 'Self-Pay'),
    ('hmo', 'HMO / Insurance'),
    ('corporate', 'Corporate'),
    ('government_assistance', 'Government Assistance'),
]


class PersonalInfoForm(forms.Form):
    first_name = forms.CharField(max_length=100, label='First Name',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Juan'}))
    middle_name = forms.CharField(max_length=100, required=False, label='Middle Name',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Optional'}))
    last_name = forms.CharField(max_length=100, label='Last Name (Surname)',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Dela Cruz'}))
    birthdate = forms.DateField(label='Date of Birth',
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))
    age = forms.IntegerField(required=False, widget=forms.HiddenInput())
    sex = forms.ChoiceField(choices=SEX_CHOICES, label='Sex',
        widget=forms.Select(attrs={'class': SELECT_CLASS}))
    phone_number = forms.CharField(max_length=20, label='Phone Number',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. 09xx-xxx-xxxx', 'type': 'tel'}))
    address = forms.CharField(label='Address',
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'rows': '3',
                                     'placeholder': 'House/Unit No., Street, Barangay, City, Province'}))
    civil_status = forms.ChoiceField(choices=CIVIL_STATUS_CHOICES, required=False, label='Civil Status',
        widget=forms.Select(attrs={'class': SELECT_CLASS}))
    religion = forms.CharField(max_length=100, required=False, label='Religion',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Optional'}))
    hrn_number = forms.CharField(max_length=50, required=False, label='HRN Number',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Hospital Record Number (if known)'}))

    def clean_sex(self):
        value = self.cleaned_data.get('sex')
        if not value:
            raise forms.ValidationError('Please select sex.')
        return value


class PaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'sr-only peer'}),
        label='Payment Type',
    )
    hmo_provider = forms.CharField(max_length=100, required=False, label='HMO / Insurance Provider',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. PhilHealth, Maxicare'}))
    hmo_membership_id = forms.CharField(max_length=100, required=False, label='Membership ID',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Membership / Policy number'}))
    corporate_company = forms.CharField(max_length=100, required=False, label='Company Name',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Enter company name'}))
    government_program = forms.CharField(max_length=100, required=False, label='Program / Agency',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. PhilHealth, 4Ps, PCSO'}))

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('payment_method')
        if method == 'hmo':
            if not cleaned.get('hmo_provider'):
                self.add_error('hmo_provider', 'HMO provider is required.')
            if not cleaned.get('hmo_membership_id'):
                self.add_error('hmo_membership_id', 'Membership ID is required.')
        elif method == 'corporate':
            if not cleaned.get('corporate_company'):
                self.add_error('corporate_company', 'Company name is required.')
        elif method == 'government_assistance':
            if not cleaned.get('government_program'):
                self.add_error('government_program', 'Program / Agency is required.')
        return cleaned
