from django.contrib import messages
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import EmployerForm, JobCategoryForm, JobPostForm, JobRequirementForm
from .models import Application, Employer, Hiring, JobCategory, JobPost, JobRequirement


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

def employer_profile(request, pk):
    employer = get_object_or_404(Employer, pk=pk)
    job_posts = employer.job_posts.all().order_by('-created_at')
    active_jobs = job_posts.filter(status='published')
    closed_jobs = job_posts.filter(status__in=['closed', 'filled'])
    applicant_count = (
        Application.objects.filter(job_post__employer=employer)
        .values('applicant').distinct().count()
    )
    hire_count = Hiring.objects.filter(
        application__job_post__employer=employer, status='hired'
    ).count()
    return render(request, 'jobportal/employer_profile.html', {
        'employer': employer,
        'active_jobs': active_jobs,
        'closed_jobs': closed_jobs,
        'applicant_count': applicant_count,
        'hire_count': hire_count,
    })

def employer_job_history(request, pk):
    employer = get_object_or_404(Employer, pk=pk)
    jobs = employer.job_posts.annotate(
        applicant_total=Count('applications')
    ).order_by('-created_at')

    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status in dict(JobPost.STATUS_CHOICES):
        jobs = jobs.filter(status=status)
    else:
        status = ''

    try:
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
    except ValueError:
        start = end = None
    if start:
        jobs = jobs.filter(created_at__date__gte=start)
    if end:
        jobs = jobs.filter(created_at__date__lte=end)

    return render(request, 'jobportal/employer_job_history.html', {
        'employer': employer,
        'jobs': jobs,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': JobPost.STATUS_CHOICES,
    })

def category_list(request):
    categories = JobCategory.objects.annotate(
        job_total=Count('jobpost')
    ).order_by('name')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if query:
        categories = categories.filter(name__icontains=query)
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)

    return render(request, 'jobportal/category_list.html', {
        'categories': categories,
        'query': query,
        'status': status,
    })


def category_add(request):
    if request.method == 'POST':
        form = JobCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'{category.name} was added.')
            return redirect('category_list')
    else:
        form = JobCategoryForm()
    return render(request, 'jobportal/category_form.html', {
        'form': form, 'title': 'Add category',
    })


def category_edit(request, pk):
    category = get_object_or_404(JobCategory, pk=pk)
    if request.method == 'POST':
        form = JobCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category was updated.')
            return redirect('category_list')
    else:
        form = JobCategoryForm(instance=category)
    return render(request, 'jobportal/category_form.html', {
        'form': form, 'title': 'Edit category',
    })


@require_POST
def category_toggle(request, pk):
    category = get_object_or_404(JobCategory, pk=pk)
    category.is_active = not category.is_active
    category.save()
    state = 'active' if category.is_active else 'inactive'
    messages.success(request, f'{category.name} is now {state}.')
    return redirect('category_list')


def jobpost_list(request):
    jobs = JobPost.objects.select_related('employer', 'category').annotate(
        requirement_total=Count('requirements', distinct=True),
        applicant_total=Count('applications', distinct=True),
    ).order_by('-created_at')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(employer__company_name__icontains=query)
        )
    if status in dict(JobPost.STATUS_CHOICES):
        jobs = jobs.filter(status=status)
    else:
        status = ''

    return render(request, 'jobportal/jobpost_list.html', {
        'jobs': jobs,
        'query': query,
        'status': status,
        'status_choices': JobPost.STATUS_CHOICES,
    })


def jobpost_add(request):
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save()
            messages.success(request, f'{job.title} was added.')
            return redirect('jobpost_list')
    else:
        form = JobPostForm()
    return render(request, 'jobportal/jobpost_form.html', {
        'form': form, 'title': 'Add job post',
    })


def jobpost_edit(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job post was updated.')
            return redirect('jobpost_list')
    else:
        form = JobPostForm(instance=job)
    return render(request, 'jobportal/jobpost_form.html', {
        'form': form, 'title': 'Edit job post',
    })


def jobpost_delete(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f'{title} was deleted.')
        return redirect('jobpost_list')
    return render(request, 'jobportal/jobpost_confirm_delete.html', {'job': job})


def jobpost_requirements(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    if request.method == 'POST':
        form = JobRequirementForm(request.POST)
        if form.is_valid():
            requirement = form.save(commit=False)
            requirement.job_post = job
            requirement.save()
            messages.success(request, 'Requirement was added.')
            return redirect('jobpost_requirements', pk=job.pk)
    else:
        form = JobRequirementForm()
    return render(request, 'jobportal/jobpost_requirements.html', {
        'job': job,
        'requirements': job.requirements.all(),
        'form': form,
    })


@require_POST
def requirement_delete(request, pk):
    requirement = get_object_or_404(JobRequirement, pk=pk)
    job_pk = requirement.job_post_id
    requirement.delete()
    messages.success(request, 'Requirement was deleted.')
    return redirect('jobpost_requirements', pk=job_pk)