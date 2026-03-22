import base64
import uuid

from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.patients.models import Patient
from django.utils import timezone
from apps.services.models import Doctor, DoctorSchedule, QueueCounter, Service
from apps.kiosk.forms import PaymentForm, PersonalInfoForm
from apps.kiosk.models import Transaction, QueueEntry
from apps.kiosk.session import KioskSession


# ---------------------------------------------------------------------------
# Start / Reset
# ---------------------------------------------------------------------------

class StartView(View):
    def get(self, request):
        KioskSession(request).clear()
        return redirect('kiosk:step1')


class ResetSessionView(View):
    def post(self, request):
        KioskSession(request).clear()
        return redirect('kiosk:start')


# ---------------------------------------------------------------------------
# Step 1 — Service Selection
# ---------------------------------------------------------------------------

class Step1ServicesView(View):
    template = 'kiosk/step1_services.html'

    def get(self, request):
        session = KioskSession(request)
        services = Service.objects.filter(is_active=True)
        return render(request, self.template, {
            'services': services,
            'selected': session.get('selected_services', []),
            'step': 1,
        })

    def post(self, request):
        selected = request.POST.getlist('services')
        if not selected:
            messages.error(request, 'Please select at least one service.')
            return redirect('kiosk:step1')
        session = KioskSession(request)
        session.set('selected_services', selected)
        session.advance_to(2)
        return redirect('kiosk:step2')


# ---------------------------------------------------------------------------
# Step 2 — Patient Type
# ---------------------------------------------------------------------------

class Step2PatientTypeView(View):
    template = 'kiosk/step2_patient_type.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.get('selected_services'):
            return redirect('kiosk:step1')
        return render(request, self.template, {'step': 2, 'back_url': 'kiosk:step1'})

    def post(self, request):
        patient_type = request.POST.get('patient_type')
        if patient_type not in ('new', 'existing'):
            return redirect('kiosk:step2')
        session = KioskSession(request)
        session.set('patient_type', patient_type)
        session.advance_to(3)
        if patient_type == 'existing':
            return redirect('kiosk:step3')
        return redirect('kiosk:step4')


# ---------------------------------------------------------------------------
# Step 3 — Patient Lookup (existing patients)
# ---------------------------------------------------------------------------

class Step3LookupView(View):
    template = 'kiosk/step3_patient_lookup.html'

    def get(self, request):
        session = KioskSession(request)
        if session.get('patient_type') != 'existing':
            return redirect('kiosk:step2')
        return render(request, self.template, {'step': 3, 'back_url': 'kiosk:step2'})

    def post(self, request):
        patient_id = request.POST.get('patient_id')
        try:
            patient = Patient.objects.get(pk=patient_id)
            session = KioskSession(request)
            session.set('patient_id', patient.pk)
            session.set('personal_info', {
                'first_name': patient.first_name,
                'middle_name': patient.middle_name,
                'last_name': patient.last_name,
                'birthdate': str(patient.birthdate),
                'sex': patient.sex,
                'phone_number': patient.phone_number,
                'address': patient.address,
                'civil_status': patient.civil_status,
                'religion': patient.religion,
                'hrn_number': patient.hrn_number or '',
            })
            session.advance_to(5)
            return redirect('kiosk:step5')
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return redirect('kiosk:step3')


class PatientSearchView(View):
    """HTMX endpoint — returns partial HTML list of matching patients."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        patients = Patient.objects.none()
        if len(query) >= 2:
            patients = (
                Patient.objects.filter(last_name__icontains=query) |
                Patient.objects.filter(hrn_number__icontains=query)
            ).distinct()[:10]
        return render(request, 'partials/_patient_results.html', {
            'patients': patients,
            'query': query,
        })


# ---------------------------------------------------------------------------
# Step 4 — Personal Info (new patients)
# ---------------------------------------------------------------------------

class Step4PersonalInfoView(View):
    template = 'kiosk/step4_personal_info.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.get('selected_services'):
            return redirect('kiosk:step1')
        form = PersonalInfoForm(initial=session.get('personal_info', {}))
        return render(request, self.template, {'form': form, 'step': 4, 'back_url': 'kiosk:step2'})

    def post(self, request):
        form = PersonalInfoForm(request.POST)
        if form.is_valid():
            session = KioskSession(request)
            data = form.cleaned_data.copy()
            data['birthdate'] = str(data['birthdate'])
            session.set('personal_info', data)
            session.advance_to(5)
            return redirect('kiosk:step5')
        return render(request, self.template, {'form': form, 'step': 4})


# ---------------------------------------------------------------------------
# Step 5 — Payment Method
# ---------------------------------------------------------------------------

class Step5PaymentView(View):
    template = 'kiosk/step5_payment.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.get('personal_info') and not session.get('patient_id'):
            return redirect('kiosk:step1')
        initial = {
            'payment_method': session.get('payment_method', ''),
            'hmo_provider': session.get('hmo_provider', ''),
            'hmo_membership_id': session.get('hmo_membership_id', ''),
            'corporate_company': session.get('corporate_company', ''),
            'government_program': session.get('government_program', ''),
        }
        form = PaymentForm(initial=initial)
        patient_type = session.get('patient_type', 'new')
        back_url = 'kiosk:step3' if patient_type == 'existing' else 'kiosk:step4'
        return render(request, self.template, {'form': form, 'step': 5, 'back_url': back_url})

    def post(self, request):
        form = PaymentForm(request.POST)
        if form.is_valid():
            session = KioskSession(request)
            session.update(form.cleaned_data)
            session.advance_to(6)
            if session.includes_consult():
                return redirect('kiosk:step6')
            return redirect('kiosk:step7')
        return render(request, self.template, {'form': form, 'step': 5})


# ---------------------------------------------------------------------------
# Step 6 — Doctor Selection (Consult only)
# ---------------------------------------------------------------------------

class Step6DoctorView(View):
    template = 'kiosk/step6_doctor.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.includes_consult():
            return redirect('kiosk:step7')
        today = timezone.localdate()
        doctors = Doctor.objects.filter(
            availability=Doctor.Availability.AVAILABLE,
            schedules__date=today,
            schedules__is_off=False,
        )
        return render(request, self.template, {
            'doctors': doctors,
            'selected_doctor_id': session.get('doctor_id'),
            'step': 6,
            'back_url': 'kiosk:step5',
        })

    def post(self, request):
        doctor_id = request.POST.get('doctor_id')
        session = KioskSession(request)
        if doctor_id and doctor_id != 'none':
            try:
                session.set('doctor_id', int(doctor_id))
            except (ValueError, TypeError):
                session.set('doctor_id', None)
        else:
            session.set('doctor_id', None)
        session.advance_to(7)
        return redirect('kiosk:step7')


# ---------------------------------------------------------------------------
# Step 7 — Signature & Consent
# ---------------------------------------------------------------------------

class Step7SignatureView(View):
    template = 'kiosk/step7_signature.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.get('payment_method'):
            return redirect('kiosk:step5')
        back_url = 'kiosk:step6' if session.includes_consult() else 'kiosk:step5'
        return render(request, self.template, {'step': 7, 'back_url': back_url})

    def post(self, request):
        session = KioskSession(request)
        if not session.get('signature_saved'):
            messages.error(request, 'Please provide your signature before continuing.')
            return redirect('kiosk:step7')
        session.advance_to(8)
        return redirect('kiosk:step8')


class SaveSignatureView(View):
    """AJAX POST: receives base64 PNG, saves to media/signatures/tmp/, stores path in session."""

    def post(self, request):
        data_url = request.POST.get('signature_data_url', '')
        if not data_url.startswith('data:image/png;base64,'):
            return JsonResponse({'error': 'Invalid signature data'}, status=400)

        base64_data = data_url.split(',')[1]
        try:
            image_data = base64.b64decode(base64_data)
        except Exception:
            return JsonResponse({'error': 'Failed to decode signature'}, status=400)

        filename = f"sig_{uuid.uuid4().hex}.png"
        saved_path = default_storage.save(
            f'signatures/tmp/{filename}',
            ContentFile(image_data, name=filename),
        )

        session = KioskSession(request)
        session.set('signature_path', saved_path)
        session.set('signature_saved', True)

        return JsonResponse({'status': 'ok'})


# ---------------------------------------------------------------------------
# Step 8 — Summary / Review
# ---------------------------------------------------------------------------

class Step8SummaryView(View):
    template = 'kiosk/step8_summary.html'

    def get(self, request):
        session = KioskSession(request)
        if not session.get('signature_saved'):
            return redirect('kiosk:step7')

        s = session._data()
        services = Service.objects.filter(code__in=s.get('selected_services', []))
        doctor = None
        if s.get('doctor_id'):
            try:
                doctor = Doctor.objects.get(pk=s['doctor_id'])
            except Doctor.DoesNotExist:
                pass

        payment_labels = {
            'selfpay': 'Self-Pay',
            'hmo': 'HMO / Insurance',
            'corporate': 'Corporate',
            'government_assistance': 'Government Assistance',
        }

        return render(request, self.template, {
            'session_data': s,
            'services': services,
            'doctor': doctor,
            'payment_label': payment_labels.get(s.get('payment_method', ''), ''),
            'step': 8,
            'back_url': 'kiosk:step7',
        })


# ---------------------------------------------------------------------------
# Confirm Transaction (AJAX POST from Step 8)
# ---------------------------------------------------------------------------

class ConfirmTransactionView(View):
    def post(self, request):
        session = KioskSession(request)
        s = session._data()

        if not s.get('signature_saved'):
            return JsonResponse({'error': 'Signature missing'}, status=400)

        with db_transaction.atomic():
            # 1. Get or create patient
            if s.get('patient_type') == 'existing' and s.get('patient_id'):
                patient = Patient.objects.get(pk=s['patient_id'])
            else:
                info = s.get('personal_info', {})
                patient = Patient.objects.create(
                    first_name=info.get('first_name', ''),
                    middle_name=info.get('middle_name', ''),
                    last_name=info.get('last_name', ''),
                    birthdate=info.get('birthdate'),
                    sex=info.get('sex', 'M'),
                    phone_number=info.get('phone_number', ''),
                    address=info.get('address', ''),
                    civil_status=info.get('civil_status', ''),
                    religion=info.get('religion', ''),
                    hrn_number=info.get('hrn_number') or None,
                )

            # 2. Generate queue numbers
            services = list(Service.objects.filter(code__in=s.get('selected_services', [])))
            queue_numbers = {}
            for svc in services:
                queue_numbers[svc.code] = QueueCounter.next_number(svc)

            # 3. Get doctor
            doctor = None
            if s.get('doctor_id'):
                try:
                    doctor = Doctor.objects.get(pk=s['doctor_id'])
                except Doctor.DoesNotExist:
                    pass

            # 4. Create Transaction
            txn = Transaction.objects.create(
                patient=patient,
                patient_type=s.get('patient_type', 'new'),
                payment_method=s.get('payment_method', 'selfpay'),
                hmo_provider=s.get('hmo_provider', ''),
                hmo_membership_id=s.get('hmo_membership_id', ''),
                corporate_company=s.get('corporate_company', ''),
                government_program=s.get('government_program', ''),
                doctor=doctor,
                queue_numbers=queue_numbers,
                kiosk_identifier=request.META.get('REMOTE_ADDR', ''),
                is_complete=True,
            )
            txn.services.set(services)

            # 5. Create QueueEntry for each service (tracks arrival + status flow)
            for svc in services:
                QueueEntry.objects.create(
                    transaction=txn,
                    service=svc,
                    queue_number=queue_numbers[svc.code],
                )

            # 6. Move signature from tmp to permanent location
            sig_path = s.get('signature_path')
            if sig_path and default_storage.exists(sig_path):
                content = default_storage.open(sig_path).read()
                new_name = f'{txn.pk}_{uuid.uuid4().hex}.png'
                txn.signature_image.save(new_name, ContentFile(content), save=True)
                default_storage.delete(sig_path)

        # Store minimal info for ticket page
        session.clear()
        session.set('ticket_txn_id', txn.pk)

        return JsonResponse({'status': 'ok', 'redirect': '/step/9/'})


# ---------------------------------------------------------------------------
# Step 9 — Queue Ticket
# ---------------------------------------------------------------------------

class Step9TicketView(View):
    template = 'kiosk/step9_ticket.html'

    def get(self, request):
        session = KioskSession(request)
        txn_id = session.get('ticket_txn_id')
        if not txn_id:
            return redirect('kiosk:start')
        txn = get_object_or_404(
            Transaction.objects.select_related('patient', 'doctor').prefetch_related('services'),
            pk=txn_id,
        )
        return render(request, self.template, {'txn': txn, 'step': 9})


# ---------------------------------------------------------------------------
# Public Queue Display Board
# ---------------------------------------------------------------------------

class QueueDisplayView(View):
    """Public TV-screen queue board — no login required."""
    template = 'kiosk/queue_display.html'

    def get(self, request):
        from apps.services.models import QueueCounter, Service
        from django.utils import timezone

        today = timezone.localdate()
        services = Service.objects.filter(is_active=True)
        counters = QueueCounter.objects.filter(date=today).select_related('service')
        counter_map = {c.service_id: c for c in counters}

        # Recently called entries per service
        recent_entries = (
            QueueEntry.objects
            .filter(arrived_at__date=today,
                    status__in=[QueueEntry.Status.CALLED, QueueEntry.Status.PROCESSING, QueueEntry.Status.DONE])
            .select_related('transaction__patient', 'service')
            .order_by('service_id', '-called_at')
        )
        recent_map = {}
        for e in recent_entries:
            recent_map.setdefault(e.service_id, [])
            if len(recent_map[e.service_id]) < 3:
                recent_map[e.service_id].append(e)

        rows = []
        for svc in services:
            c = counter_map.get(svc.pk)
            serving = c.currently_serving if c else 0
            rows.append({
                'service': svc,
                'serving_label': f"{svc.prefix}-{serving:03d}" if serving > 0 else '—',
                'waiting': (c.count - serving) if c else 0,
                'recently_called': recent_map.get(svc.pk, []),
            })

        return render(request, self.template, {'rows': rows})
