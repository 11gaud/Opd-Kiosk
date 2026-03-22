import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models as db_models
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.dashboard.decorators import module_required, staff_required
from apps.dashboard.forms import DAYS, DoctorForm, DoctorScheduleDayForm, PatientEditForm, WeeklyPatternForm
from apps.kiosk.models import QueueEntry, Transaction
from apps.patients.models import Patient
from apps.services.models import Doctor, DoctorSchedule, QueueCounter, Service


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

@method_decorator(staff_required, name='dispatch')
class DashboardHomeView(View):
    template = 'dashboard/home.html'

    def get(self, request):
        today = timezone.localdate()
        services = Service.objects.filter(is_active=True)
        counters = QueueCounter.objects.filter(date=today).select_related('service')
        counter_map = {c.service_id: c for c in counters}

        queue_stats = []
        for svc in services:
            c = counter_map.get(svc.pk)
            queue_stats.append({
                'service': svc,
                'issued': c.count if c else 0,
                'serving': c.currently_serving if c else 0,
                'waiting': (c.count - c.currently_serving) if c else 0,
            })

        total_transactions = Transaction.objects.filter(created_at__date=today).count()
        available_doctors = Doctor.objects.filter(
            availability=Doctor.Availability.AVAILABLE
        ).count()

        return render(request, self.template, {
            'queue_stats': queue_stats,
            'total_transactions': total_transactions,
            'available_doctors': available_doctors,
            'today': today,
        })


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

@method_decorator([staff_required, module_required('patients')], name='dispatch')
class PatientListView(View):
    template = 'dashboard/patients/list.html'

    def get(self, request):
        qs = Patient.objects.all()
        q = request.GET.get('q', '').strip()
        sex = request.GET.get('sex', '')
        if q:
            qs = qs.filter(
                db_models.Q(last_name__icontains=q) |
                db_models.Q(first_name__icontains=q) |
                db_models.Q(hrn_number__icontains=q) |
                db_models.Q(phone_number__icontains=q)
            )
        if sex in ('M', 'F'):
            qs = qs.filter(sex=sex)
        paginator = Paginator(qs, 25)
        page = paginator.get_page(request.GET.get('page'))
        return render(request, self.template, {'page_obj': page, 'q': q, 'sex': sex})


@method_decorator([staff_required, module_required('patients')], name='dispatch')
class PatientDetailView(View):
    template = 'dashboard/patients/detail.html'

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        transactions = (
            patient.transactions
            .select_related('doctor')
            .prefetch_related('services')
            .order_by('-created_at')
        )
        return render(request, self.template, {
            'patient': patient,
            'transactions': transactions,
        })


@method_decorator([staff_required, module_required('patients')], name='dispatch')
class PatientEditView(View):
    template = 'dashboard/patients/edit.html'

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        form = PatientEditForm(instance=patient)
        return render(request, self.template, {'form': form, 'patient': patient})

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        form = PatientEditForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient {patient.full_name} updated.')
            return redirect('dashboard:patient_detail', pk=pk)
        return render(request, self.template, {'form': form, 'patient': patient})


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------

@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorListView(View):
    template = 'dashboard/doctors/list.html'

    def get(self, request):
        qs = Doctor.objects.all()
        availability_filter = request.GET.get('availability', '')
        if availability_filter:
            qs = qs.filter(availability=availability_filter)
        return render(request, self.template, {
            'doctors': qs,
            'availability_choices': Doctor.Availability.choices,
            'current_filter': availability_filter,
        })


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorCreateView(View):
    template = 'dashboard/doctors/form.html'

    def get(self, request):
        return render(request, self.template, {'form': DoctorForm(), 'action': 'Add'})

    def post(self, request):
        form = DoctorForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'{doctor.full_name} added.')
            return redirect('dashboard:doctor_list')
        return render(request, self.template, {'form': form, 'action': 'Add'})


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorEditView(View):
    template = 'dashboard/doctors/form.html'

    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        return render(request, self.template, {
            'form': DoctorForm(instance=doctor),
            'doctor': doctor,
            'action': 'Edit',
        })

    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'{doctor.full_name} updated.')
            return redirect('dashboard:doctor_list')
        return render(request, self.template, {'form': form, 'doctor': doctor, 'action': 'Edit'})


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorToggleAvailabilityView(View):
    """HTMX POST — cycles availability, returns updated doctor row partial."""

    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        cycle = {
            Doctor.Availability.AVAILABLE:   Doctor.Availability.UNAVAILABLE,
            Doctor.Availability.UNAVAILABLE: Doctor.Availability.ON_LEAVE,
            Doctor.Availability.ON_LEAVE:    Doctor.Availability.AVAILABLE,
        }
        doctor.availability = cycle.get(doctor.availability, Doctor.Availability.AVAILABLE)
        doctor.save(update_fields=['availability'])
        return render(request, 'dashboard/partials/_doctor_row.html', {'doctor': doctor})


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorScheduleView(View):
    template = 'dashboard/doctors/schedule.html'

    def _get_context(self, doctor, year, month):
        schedules = DoctorSchedule.objects.filter(
            doctor=doctor, date__year=year, date__month=month
        )
        schedule_map = {s.date: s for s in schedules}
        # Build week_rows: list of list of {'day': date, 'schedule': obj_or_none}
        raw_weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
        week_rows = [
            [{'day': d, 'schedule': schedule_map.get(d)} for d in week]
            for week in raw_weeks
        ]
        # prev/next month navigation
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1
        return {
            'doctor': doctor,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'week_rows': week_rows,
            'prev_year': prev_year, 'prev_month': prev_month,
            'next_year': next_year, 'next_month': next_month,
            'day_headers': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'days': DAYS,
        }

    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        today = timezone.localdate()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        return render(request, self.template, self._get_context(doctor, year, month))

    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        year = int(request.POST.get('year', 2026))
        form = WeeklyPatternForm(request.POST)
        if form.is_valid():
            cal = calendar.Calendar(firstweekday=0)
            for month in range(1, 13):
                for week in cal.monthdatescalendar(year, month):
                    for day_date in week:
                        if day_date.year != year or day_date.month != month:
                            continue
                        weekday_name = DAYS[day_date.weekday()]
                        start = form.cleaned_data.get(f'{weekday_name}_start')
                        end = form.cleaned_data.get(f'{weekday_name}_end')
                        is_off = form.cleaned_data.get(f'{weekday_name}_off', False)
                        DoctorSchedule.objects.update_or_create(
                            doctor=doctor, date=day_date,
                            defaults={'start_time': start, 'end_time': end, 'is_off': is_off},
                        )
            messages.success(request, f'Weekly pattern applied to all of {year}.')
        today = timezone.localdate()
        return redirect(f"{request.path}?year={year}&month={today.month}")


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorScheduleSaveDayView(View):
    """HTMX POST — saves/updates one day's schedule, returns updated day cell partial."""

    def post(self, request, pk, date_str):
        doctor = get_object_or_404(Doctor, pk=pk)
        try:
            day_date = date.fromisoformat(date_str)
        except ValueError:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest()
        form = DoctorScheduleDayForm(request.POST)
        if form.is_valid():
            DoctorSchedule.objects.update_or_create(
                doctor=doctor, date=day_date,
                defaults={
                    'start_time': form.cleaned_data.get('start_time'),
                    'end_time': form.cleaned_data.get('end_time'),
                    'is_off': form.cleaned_data.get('is_off', False),
                    'note': form.cleaned_data.get('note', ''),
                },
            )
        schedule = DoctorSchedule.objects.filter(doctor=doctor, date=day_date).first()
        return render(request, 'dashboard/partials/_schedule_day.html', {
            'doctor': doctor,
            'day': day_date,
            'schedule': schedule,
            'current_month': day_date.month,
        })


@method_decorator([staff_required, module_required('doctors')], name='dispatch')
class DoctorScheduleToggleDayOffView(View):
    """HTMX POST — toggles is_off for a single day, returns updated day cell."""

    def post(self, request, pk, date_str):
        doctor = get_object_or_404(Doctor, pk=pk)
        try:
            day_date = date.fromisoformat(date_str)
        except ValueError:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest()
        schedule = DoctorSchedule.objects.filter(doctor=doctor, date=day_date).first()
        if schedule is None:
            schedule = DoctorSchedule.objects.create(doctor=doctor, date=day_date, is_off=True)
        elif schedule.is_off:
            schedule.delete()
            schedule = None
        else:
            schedule.is_off = True
            schedule.start_time = None
            schedule.end_time = None
            schedule.save(update_fields=['is_off', 'start_time', 'end_time'])
        return render(request, 'dashboard/partials/_schedule_day.html', {
            'doctor': doctor,
            'day': day_date,
            'schedule': schedule,
            'current_month': day_date.month,
        })


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

@method_decorator([staff_required, module_required('queue')], name='dispatch')
class QueueBoardView(View):
    template = 'dashboard/queue/list.html'

    def get(self, request):
        today = timezone.localdate()
        services = Service.objects.filter(is_active=True)
        counters = QueueCounter.objects.filter(date=today).select_related('service')
        counter_map = {c.service_id: c for c in counters}

        # Fetch all today's QueueEntry records grouped by service
        entries = (
            QueueEntry.objects
            .filter(arrived_at__date=today)
            .select_related('transaction__patient', 'service')
            .order_by('arrived_at')
        )
        entry_map = {}
        for e in entries:
            entry_map.setdefault(e.service_id, []).append(e)

        rows = []
        for svc in services:
            c = counter_map.get(svc.pk)
            row = _build_queue_row(svc, c)
            row['entries'] = entry_map.get(svc.pk, [])
            rows.append(row)

        return render(request, self.template, {'rows': rows, 'today': today})


@method_decorator([staff_required, module_required('queue')], name='dispatch')
class QueueCallNextView(View):
    """HTMX POST — advances currently_serving, marks QueueEntry as Called, returns updated row partial."""

    def post(self, request, service_pk):
        service = get_object_or_404(Service, pk=service_pk)
        counter = QueueCounter.call_next(service)

        # Mark the corresponding QueueEntry as Processing automatically
        if counter.currently_serving > 0:
            now = timezone.now()
            queue_number = f"{service.prefix}-{counter.currently_serving:03d}"
            QueueEntry.objects.filter(
                service=service,
                queue_number=queue_number,
                status=QueueEntry.Status.WAITING,
            ).update(
                status=QueueEntry.Status.PROCESSING,
                called_at=now,
                processed_at=now,
            )

        today = timezone.localdate()
        entries = list(
            QueueEntry.objects
            .filter(arrived_at__date=today, service=service)
            .select_related('transaction__patient')
            .order_by('arrived_at')
        )
        row = _build_queue_row(service, counter)
        row['entries'] = entries
        return render(request, 'dashboard/partials/_queue_row.html', {'row': row})


@method_decorator([staff_required, module_required('queue')], name='dispatch')
class QueueResetView(View):
    """Plain POST — resets today's queue for a service."""

    def post(self, request, service_pk):
        service = get_object_or_404(Service, pk=service_pk)
        QueueCounter.reset_today(service)
        messages.success(request, f'Queue for {service.label} has been reset.')
        return redirect('dashboard:queue_board')


@method_decorator([staff_required, module_required('queue')], name='dispatch')
class QueueEntryStatusView(View):
    """HTMX POST — updates a QueueEntry status, returns updated entry row partial."""

    def post(self, request, pk):
        entry = get_object_or_404(QueueEntry, pk=pk)
        action = request.POST.get('action')
        now = timezone.now()
        transitions = {
            'process': (QueueEntry.Status.PROCESSING, {'processed_at': now}),
            'done':    (QueueEntry.Status.DONE,       {'done_at': now}),
            'no_show': (QueueEntry.Status.NO_SHOW,    {}),
        }
        if action in transitions:
            new_status, extra = transitions[action]
            QueueEntry.objects.filter(pk=pk).update(status=new_status, **extra)
            entry.refresh_from_db()
        return render(request, 'dashboard/partials/_queue_entry_row.html', {'entry': entry})


def _build_queue_row(service, counter):
    issued = counter.count if counter else 0
    serving = counter.currently_serving if counter else 0
    waiting = issued - serving
    serving_label = (
        f"{service.prefix}-{serving:03d}" if serving > 0 else '—'
    )
    return {
        'service': service,
        'counter': counter,
        'issued': issued,
        'serving': serving,
        'waiting': waiting,
        'serving_label': serving_label,
    }


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@method_decorator([staff_required, module_required('transactions')], name='dispatch')
class TransactionListView(View):
    template = 'dashboard/transactions/list.html'

    def get(self, request):
        today = timezone.localdate()
        date_str = request.GET.get('date', str(today))
        try:
            filter_date = date.fromisoformat(date_str)
        except ValueError:
            filter_date = today

        qs = (
            Transaction.objects
            .filter(created_at__date=filter_date)
            .select_related('patient', 'doctor')
            .prefetch_related('services')
            .order_by('-created_at')
        )

        payment_filter = request.GET.get('payment', '')
        if payment_filter:
            qs = qs.filter(payment_method=payment_filter)

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(patient__first_name__icontains=q) |
                Q(patient__last_name__icontains=q) |
                Q(patient__hrn_number__icontains=q)
            )

        return render(request, self.template, {
            'transactions': qs,
            'filter_date': filter_date,
            'payment_choices': Transaction.PaymentMethod.choices,
            'current_payment': payment_filter,
            'q': q,
        })


# ---------------------------------------------------------------------------
# Reports & Analytics
# ---------------------------------------------------------------------------

@method_decorator([staff_required, module_required('reports')], name='dispatch')
class ReportsView(View):
    template = 'dashboard/reports.html'

    def get(self, request):
        today = timezone.localdate()
        # Default range: first day of current month → today
        default_start = today.replace(day=1)
        try:
            start_date = date.fromisoformat(request.GET.get('start', str(default_start)))
        except ValueError:
            start_date = default_start
        try:
            end_date = date.fromisoformat(request.GET.get('end', str(today)))
        except ValueError:
            end_date = today

        base_qs = Transaction.objects.filter(created_at__date__range=(start_date, end_date))

        total = base_qs.count()
        new_patients = base_qs.filter(patient_type='new').count()
        returning = base_qs.filter(patient_type='existing').count()

        # Payment breakdown with percentages
        payment_rows = list(
            base_qs.values('payment_method')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        payment_label_map = dict(Transaction.PaymentMethod.choices)
        for row in payment_rows:
            row['label'] = payment_label_map.get(row['payment_method'], row['payment_method'])
            row['pct'] = round(row['count'] / total * 100) if total else 0

        # Service breakdown with percentages
        service_rows = list(
            Service.objects
            .filter(transactions__created_at__date__range=(start_date, end_date))
            .annotate(count=Count('transactions'))
            .order_by('-count')
            .values('label', 'icon', 'count')
        )
        for row in service_rows:
            row['pct'] = round(row['count'] / total * 100) if total else 0

        # Doctor breakdown
        doctor_rows = list(
            Doctor.objects
            .filter(transactions__created_at__date__range=(start_date, end_date))
            .annotate(count=Count('transactions'))
            .order_by('-count')
            .values('first_name', 'last_name', 'specialization', 'count')
        )
        for row in doctor_rows:
            row['full_name'] = f"Dr. {row['first_name']} {row['last_name']}"

        # Daily trend
        daily_trend = list(
            base_qs
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        max_day_count = max((d['count'] for d in daily_trend), default=1)

        top_service = service_rows[0]['icon'] + ' ' + service_rows[0]['label'] if service_rows else '—'

        # --- Timing stats (from QueueEntry) ---
        done_entries = list(
            QueueEntry.objects
            .filter(
                arrived_at__date__range=(start_date, end_date),
                done_at__isnull=False,
            )
            .select_related('transaction__patient')
            .only('arrived_at', 'done_at',
                  'transaction__patient__first_name',
                  'transaction__patient__last_name')
        )

        fastest_entry = None
        slowest_entry = None
        if done_entries:
            def duration_secs(e):
                return (e.done_at - e.arrived_at).total_seconds()

            done_entries.sort(key=duration_secs)
            fastest_entry = done_entries[0]
            slowest_entry = done_entries[-1]

        # Earliest / latest patient arrivals (time-of-day from Transaction)
        from django.db.models import Min, Max
        arrival_agg = base_qs.aggregate(earliest=Min('created_at'), latest=Max('created_at'))

        def fmt_duration(entry):
            if entry is None:
                return None
            secs = int((entry.done_at - entry.arrived_at).total_seconds())
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            if h:
                return f"{h}h {m}m {s}s"
            if m:
                return f"{m}m {s}s"
            return f"{s}s"

        def patient_name(entry):
            if entry is None:
                return '—'
            p = entry.transaction.patient
            return f"{p.last_name}, {p.first_name}"

        timing = {
            'earliest_arrival': arrival_agg['earliest'],
            'latest_arrival':   arrival_agg['latest'],
            'fastest_entry':    fastest_entry,
            'slowest_entry':    slowest_entry,
            'fastest_duration': fmt_duration(fastest_entry),
            'slowest_duration': fmt_duration(slowest_entry),
            'fastest_patient':  patient_name(fastest_entry),
            'slowest_patient':  patient_name(slowest_entry),
        }

        return render(request, self.template, {
            'start_date': start_date,
            'end_date': end_date,
            'total': total,
            'new_patients': new_patients,
            'returning': returning,
            'top_service': top_service,
            'payment_rows': payment_rows,
            'service_rows': service_rows,
            'doctor_rows': doctor_rows,
            'daily_trend': daily_trend,
            'max_day_count': max_day_count,
            'timing': timing,
        })
