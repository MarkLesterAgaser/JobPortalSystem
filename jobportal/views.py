from django.contrib import messages
from django.db.models import Count, ProtectedError, Q
from django.utils.dateparse import parse_date
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import CourseForm, EmployerForm, EnrollmentForm, JobCategoryForm
from .models import Application, Course, Employer, Enrollment, Hiring, JobCategory, JobPost


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

def course_list(request):
    courses = Course.objects.annotate(
        record_total=Count('enrollments')
    ).order_by('id')
    return render(request, 'jobportal/course_list.html', {
        'courses': courses,
        'mode': request.GET.get('mode', ''),
    })


def course_add(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'{course.course_name} was added.')
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'jobportal/course_form.html', {
        'form': form, 'title': 'Add course',
    })


def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course was updated.')
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'jobportal/course_form.html', {
        'form': form, 'title': 'Edit course',
    })


@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    name = course.course_name
    try:
        course.delete()
        messages.success(request, f'{name} was deleted.')
    except ProtectedError:
        messages.error(request, f'{name} cannot be deleted because records still use it.')
    return redirect('course_list')

def enrollment_list(request):
    enrollments = Enrollment.objects.select_related('course').order_by('id')
    return render(request, 'jobportal/enrollment_list.html', {
        'enrollments': enrollments,
    })


def enrollment_add(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enrollment was saved.')
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm()
    return render(request, 'jobportal/enrollment_form.html', {
        'form': form, 'title': 'Student enrollment',
    })


def enrollment_edit(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enrollment was updated.')
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(instance=enrollment)
    return render(request, 'jobportal/enrollment_form.html', {
        'form': form, 'title': 'Edit enrollment',
    })


@require_POST
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    enrollment.delete()
    messages.success(request, 'Enrollment was deleted.')
    return redirect('enrollment_list')