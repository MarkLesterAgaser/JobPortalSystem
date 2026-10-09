from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import EmployerForm
from .models import Employer


def employer_list(request):
    employers = Employer.objects.all().order_by('company_name')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if query:
        employers = employers.filter(
            Q(company_name__icontains=query)
            | Q(contact_person__icontains=query)
            | Q(email__icontains=query)
        )
    if status in ('active', 'inactive'):
        employers = employers.filter(status=status)

    return render(request, 'jobportal/employer_list.html', {
        'employers': employers,
        'query': query,
        'status': status,
    })


def employer_add(request):
    if request.method == 'POST':
        form = EmployerForm(request.POST)
        if form.is_valid():
            employer = form.save()
            messages.success(request, f'{employer.company_name} was registered.')
            return redirect('employer_detail', pk=employer.pk)
    else:
        form = EmployerForm()
    return render(request, 'jobportal/employer_form.html', {
        'form': form, 'title': 'Register Employer',
    })


def employer_edit(request, pk):
    employer = get_object_or_404(Employer, pk=pk)
    if request.method == 'POST':
        form = EmployerForm(request.POST, instance=employer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Employer was updated.')
            return redirect('employer_detail', pk=employer.pk)
    else:
        form = EmployerForm(instance=employer)
    return render(request, 'jobportal/employer_form.html', {
        'form': form, 'title': 'Edit Employer',
    })


def employer_detail(request, pk):
    employer = get_object_or_404(Employer, pk=pk)
    return render(request, 'jobportal/employer_detail.html', {'employer': employer})


@require_POST
def employer_toggle(request, pk):
    employer = get_object_or_404(Employer, pk=pk)
    employer.status = 'inactive' if employer.status == 'active' else 'active'
    employer.save()
    messages.success(request, f'{employer.company_name} is now {employer.status}.')
    return redirect('employer_detail', pk=employer.pk)