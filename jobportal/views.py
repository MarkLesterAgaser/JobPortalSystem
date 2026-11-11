from datetime import date

from django.contrib import messages
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import (
    ApplicantEducationForm, ApplicantForm, ApplicantProfileInfoForm,
    ApplicantSkillsExperienceForm, EmployerForm, JobCategoryForm,
    JobPostForm, JobRequirementForm,
)
from .models import (
    Applicant, ApplicantProfile, Application, Employer, Hiring,
    JobCategory, JobPost, JobRequirement,
)


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


def next_applicant_number():
    last = Applicant.objects.order_by('-id').first()
    number_id = last.id + 1 if last else 1
    number = f'APP-{number_id:04d}'
    while Applicant.objects.filter(applicant_number=number).exists():
        number_id += 1
        number = f'APP-{number_id:04d}'
    return number


def get_profile(applicant):
    profile, created = ApplicantProfile.objects.get_or_create(applicant=applicant)
    return profile


def applicant_list(request):
    applicants = Applicant.objects.all().order_by('last_name', 'first_name')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if query:
        applicants = applicants.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(applicant_number__icontains=query)
            | Q(email__icontains=query)
        )
    if status in ('active', 'inactive'):
        applicants = applicants.filter(status=status)
    else:
        status = ''

    return render(request, 'jobportal/applicant_list.html', {
        'applicants': applicants,
        'query': query,
        'status': status,
    })


def applicant_add(request):
    if request.method == 'POST':
        form = ApplicantForm(request.POST)
        if form.is_valid():
            applicant = form.save(commit=False)
            applicant.applicant_number = next_applicant_number()
            applicant.save()
            get_profile(applicant)
            messages.success(request, f'{applicant} was registered as {applicant.applicant_number}.')
            return redirect('applicant_list')
    else:
        form = ApplicantForm()
    return render(request, 'jobportal/applicant_form.html', {
        'form': form, 'title': 'Register applicant',
    })


def applicant_edit(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    if request.method == 'POST':
        form = ApplicantForm(request.POST, instance=applicant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Applicant was updated.')
            return redirect('applicant_list')
    else:
        form = ApplicantForm(instance=applicant)
    return render(request, 'jobportal/applicant_form.html', {
        'form': form, 'title': 'Edit applicant',
    })


@require_POST
def applicant_toggle(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    applicant.status = 'inactive' if applicant.status == 'active' else 'active'
    applicant.save()
    messages.success(request, f'{applicant} is now {applicant.status}.')
    return redirect('applicant_list')


def applicant_profile(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    profile = get_profile(applicant)
    checks = [
        ('Career objective', applicant.career_objective),
        ('Education', profile.education),
        ('Skills', profile.skills),
        ('Work experience', profile.work_experience),
        ('Certifications', profile.certifications),
        ('Training', profile.training),
        ('References', profile.references),
    ]
    missing = [label for label, value in checks if not value.strip()]
    completion = round((len(checks) - len(missing)) * 100 / len(checks))
    return render(request, 'jobportal/applicant_profile.html', {
        'applicant': applicant,
        'profile': profile,
        'completion': completion,
        'missing': missing,
        'application_total': applicant.applications.count(),
    })


def edit_profile_section(request, pk, form_class, title, message):
    applicant = get_object_or_404(Applicant, pk=pk)
    profile = get_profile(applicant)
    if request.method == 'POST':
        form = form_class(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, message)
            return redirect('applicant_profile', pk=applicant.pk)
    else:
        form = form_class(instance=profile)
    return render(request, 'jobportal/applicant_section_form.html', {
        'form': form, 'title': title, 'applicant': applicant,
    })


def applicant_profile_edit(request, pk):
    return edit_profile_section(
        request, pk, ApplicantProfileInfoForm,
        'Edit training and references', 'Training and references were saved.',
    )


def applicant_education(request, pk):
    return edit_profile_section(
        request, pk, ApplicantEducationForm,
        'Edit education', 'Education was saved.',
    )


def applicant_skills(request, pk):
    return edit_profile_section(
        request, pk, ApplicantSkillsExperienceForm,
        'Edit skills and experience', 'Skills and experience were saved.',
    )


STATUS_ACTIONS = {
    'publish': ('draft', 'published'),
    'close': ('published', 'closed'),
    'fill': ('published', 'filled'),
}


@require_POST
def jobpost_set_status(request, pk, action):
    job = get_object_or_404(JobPost, pk=pk)
    needed, new_status = STATUS_ACTIONS[action]
    if job.status != needed:
        messages.error(request, f'Only a {needed} job post can use this action.')
    elif action == 'publish' and job.employer.status != 'active':
        messages.error(request, 'The employer is inactive. Activate the employer first.')
    elif action == 'publish' and job.application_deadline < date.today():
        messages.error(request, 'The deadline is in the past. Edit the job post first.')
    elif action == 'publish' and not job.requirements.exists():
        messages.error(request, 'Add at least one requirement before you publish.')
    else:
        job.status = new_status
        job.save()
        messages.success(request, f'{job.title} is now {job.get_status_display().lower()}.')
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('jobpost_list')


def job_search(request):
    jobs = JobPost.objects.select_related('employer', 'category').filter(
        status='published', application_deadline__gte=date.today()
    ).order_by('-created_at')
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    employment_type = request.GET.get('employment_type', '')
    location = request.GET.get('location', '').strip()
    min_salary = request.GET.get('min_salary', '').strip()

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(employer__company_name__icontains=query)
        )
    if category.isdigit():
        jobs = jobs.filter(category_id=category)
    else:
        category = ''
    if employment_type in dict(JobPost.EMPLOYMENT_TYPE_CHOICES):
        jobs = jobs.filter(employment_type=employment_type)
    else:
        employment_type = ''
    if location:
        jobs = jobs.filter(location__icontains=location)
    if min_salary.isdigit():
        jobs = jobs.filter(salary_max__gte=min_salary)
    else:
        min_salary = ''

    return render(request, 'jobportal/job_search.html', {
        'jobs': jobs,
        'query': query,
        'category': category,
        'employment_type': employment_type,
        'location': location,
        'min_salary': min_salary,
        'categories': JobCategory.objects.filter(is_active=True).order_by('name'),
        'type_choices': JobPost.EMPLOYMENT_TYPE_CHOICES,
    })


def jobpost_detail(request, pk):
    job = get_object_or_404(
        JobPost.objects.select_related('employer', 'category'), pk=pk
    )
    return render(request, 'jobportal/jobpost_detail.html', {
        'job': job,
        'requirements': job.requirements.all(),
        'applicant_total': job.applications.count(),
    })