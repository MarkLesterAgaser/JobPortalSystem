from datetime import date

from django.contrib import messages
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import (
    ApplicantEducationForm, ApplicantForm, ApplicantProfileInfoForm,
    ApplicantSkillsExperienceForm, ApplicationForm, EmployerForm,
    JobCategoryForm, JobPostForm, JobRequirementForm, ResumeUploadForm,
    ScreeningRemarksForm, ScreeningScoreForm,
    InterviewForm, ACTIVE_INTERVIEW, EvaluationForm, HiringForm,
)
from .models import (
    Applicant, ApplicantProfile, Application, ApplicationDocument, Employer,
    Hiring, JobCategory, JobPost, JobRequirement, Notification, Screening,
    Interview, Evaluation,
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


def next_application_number():
    last = Application.objects.order_by('-id').first()
    number_id = last.id + 1 if last else 1
    number = f'APL-{number_id:04d}'
    while Application.objects.filter(application_number=number).exists():
        number_id += 1
        number = f'APL-{number_id:04d}'
    return number


def job_apply(request, pk):
    job = get_object_or_404(JobPost.objects.select_related('employer'), pk=pk)
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, job=job)
        if form.is_valid():
            application = form.save(commit=False)
            application.job_post = job
            application.application_number = next_application_number()
            application.save()
            document = request.FILES.get('document')
            if document:
                ApplicationDocument.objects.create(application=application, document=document)
            Notification.objects.create(
                applicant=application.applicant,
                message=f'Your application {application.application_number} for {job.title} was received.'[:255],
            )
            return redirect('application_confirmation', pk=application.pk)
    else:
        form = ApplicationForm(job=job)
    return render(request, 'jobportal/job_application.html', {
        'job': job,
        'form': form,
    })


def application_confirmation(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post__employer'), pk=pk
    )
    return render(request, 'jobportal/application_confirmation.html', {
        'application': application,
        'documents': application.documents.all(),
    })


def applicant_resume(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    profile = get_profile(applicant)
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            old_name = profile.resume.name if profile.resume else ''
            profile.resume = form.cleaned_data['resume']
            profile.save()
            if old_name and old_name != profile.resume.name:
                profile.resume.storage.delete(old_name)
            messages.success(request, 'Resume was saved.')
            return redirect('applicant_profile', pk=applicant.pk)
    else:
        form = ResumeUploadForm()
    return render(request, 'jobportal/applicant_resume.html', {
        'form': form, 'applicant': applicant, 'profile': profile,
    })


@require_POST
def applicant_resume_delete(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    profile = get_profile(applicant)
    if profile.resume:
        profile.resume.delete(save=True)
        messages.success(request, 'Resume was deleted.')
    else:
        messages.error(request, 'There is no resume to delete.')
    return redirect('applicant_profile', pk=applicant.pk)


def applicant_applications(request, pk):
    applicant = get_object_or_404(Applicant, pk=pk)
    applications = applicant.applications.select_related(
        'job_post__employer'
    ).order_by('-application_date')

    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status in dict(Application.STATUS_CHOICES):
        applications = applications.filter(status=status)
    else:
        status = ''

    try:
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
    except ValueError:
        start = end = None
    if start:
        applications = applications.filter(application_date__date__gte=start)
    if end:
        applications = applications.filter(application_date__date__lte=end)

    return render(request, 'jobportal/applicant_applications.html', {
        'applicant': applicant,
        'applications': applications,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Application.STATUS_CHOICES,
    })


def application_list(request):
    applications = Application.objects.select_related(
        'applicant', 'job_post__employer', 'screening'
    ).order_by('-application_date')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    job = request.GET.get('job', '')

    if query:
        applications = applications.filter(
            Q(application_number__icontains=query)
            | Q(applicant__first_name__icontains=query)
            | Q(applicant__last_name__icontains=query)
            | Q(job_post__title__icontains=query)
        )
    if status in dict(Application.STATUS_CHOICES):
        applications = applications.filter(status=status)
    else:
        status = ''
    if job.isdigit():
        applications = applications.filter(job_post_id=job)
    else:
        job = ''

    return render(request, 'jobportal/application_list.html', {
        'applications': applications,
        'query': query,
        'status': status,
        'job': job,
        'status_choices': Application.STATUS_CHOICES,
        'jobs': JobPost.objects.order_by('title'),
    })


def application_detail(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post__employer'), pk=pk
    )
    return render(request, 'jobportal/application_detail.html', {
        'application': application,
        'applicant': application.applicant,
        'profile': get_profile(application.applicant),
        'documents': application.documents.all(),
        'screening': Screening.objects.filter(application=application).first(),
        'interviews': application.interviews.select_related('evaluation').order_by('-interview_date', '-interview_time'),
        'can_schedule': application.status in ('shortlisted', 'interview') and not application.interviews.filter(status__in=ACTIVE_INTERVIEW).exists(),
        'hiring': Hiring.objects.filter(application=application).first(),
    })


@require_POST
def application_review_start(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if application.status != 'submitted':
        messages.error(request, 'Only a submitted application can start review.')
    else:
        application.status = 'under_review'
        application.save()
        messages.success(request, f'{application.application_number} is now under review.')
    return redirect('application_detail', pk=application.pk)


def get_screening(application):
    screening, created = Screening.objects.get_or_create(
        application=application, defaults={'status': 'under_review'}
    )
    return screening


def get_open_screening(request, application):
    if application.status != 'under_review':
        messages.error(request, 'Screening is only open while an application is under review.')
        return None
    return get_screening(application)


def screening_review(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post__employer'), pk=pk
    )
    screening = get_open_screening(request, application)
    if screening is None:
        return redirect('application_detail', pk=application.pk)
    if request.method == 'POST':
        form = ScreeningRemarksForm(request.POST, instance=screening)
        if form.is_valid():
            form.save()
            messages.success(request, 'Screening remarks were saved.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ScreeningRemarksForm(instance=screening)
    return render(request, 'jobportal/screening_review.html', {
        'application': application,
        'job': application.job_post,
        'requirements': application.job_post.requirements.all(),
        'applicant': application.applicant,
        'profile': get_profile(application.applicant),
        'form': form,
    })


PASSING_SCORE = 60


def screening_score(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post'), pk=pk
    )
    screening = get_open_screening(request, application)
    if screening is None:
        return redirect('application_detail', pk=application.pk)
    if request.method == 'POST':
        form = ScreeningScoreForm(request.POST, instance=screening)
        if form.is_valid():
            screening = form.save()
            messages.success(request, f'Scores were saved. The total is {screening.total_score} out of 100.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ScreeningScoreForm(instance=screening)
    return render(request, 'jobportal/screening_score.html', {
        'form': form,
        'application': application,
        'passing_score': PASSING_SCORE,
    })


DECISIONS = {
    'shortlist': 'shortlisted',
    'reject': 'rejected',
}


@require_POST
def application_decide(request, pk, decision):
    application = get_object_or_404(Application, pk=pk)
    new_status = DECISIONS[decision]
    screening = Screening.objects.filter(application=application).first()
    if application.status != 'under_review':
        messages.error(request, 'Only an application under review can be shortlisted or rejected.')
    elif screening is None or screening.total_score <= 0:
        messages.error(request, 'Enter the screening scores first.')
    elif decision == 'shortlist' and screening.total_score < PASSING_SCORE:
        messages.error(request, f'The total score is below the passing score of {PASSING_SCORE}.')
    else:
        application.status = new_status
        application.save()
        screening.status = new_status
        screening.save()
        messages.success(request, f'{application.application_number} is now {application.get_status_display().lower()}.')
    return redirect('application_detail', pk=application.pk)


def shortlist_list(request):
    applications = Application.objects.filter(status='shortlisted').select_related(
        'applicant', 'job_post__employer', 'screening'
    ).order_by('-screening__total_score', 'application_date')
    job = request.GET.get('job', '')
    if job.isdigit():
        applications = applications.filter(job_post_id=job)
    else:
        job = ''
    return render(request, 'jobportal/shortlist_list.html', {
        'applications': applications,
        'job': job,
        'jobs': JobPost.objects.filter(applications__status='shortlisted').distinct().order_by('title'),
    })


def notify_applicant(application, text):
    Notification.objects.create(applicant=application.applicant, message=text[:255])

def interview_schedule(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post__employer'), pk=pk
    )
    if application.status not in ('shortlisted', 'interview'):
        messages.error(request, 'Only a shortlisted application can be scheduled for an interview.')
        return redirect('application_detail', pk=application.pk)
    if application.interviews.filter(status__in=ACTIVE_INTERVIEW).exists():
        messages.error(request, 'This application already has an active interview.')
        return redirect('application_detail', pk=application.pk)
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = 'scheduled'
            interview.save()
            application.status = 'interview'
            application.save()
            notify_applicant(
                application,
                f'An interview for {application.job_post.title} was scheduled on '
                f'{interview.interview_date:%B %d, %Y} at {interview.interview_time:%I:%M %p}.',
            )
            messages.success(request, 'The interview was scheduled.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = InterviewForm()
    return render(request, 'jobportal/interview_form.html', {
        'form': form, 'application': application, 'title': 'Schedule interview',
    })


INTERVIEW_ACTIONS = {
    'confirm': ('confirmed', ('scheduled', 'rescheduled')),
    'complete': ('completed', ACTIVE_INTERVIEW),
    'no_show': ('no_show', ACTIVE_INTERVIEW),
    'cancel': ('cancelled', ACTIVE_INTERVIEW),
}

def reset_application_after_interview(application):
    still_open = application.interviews.filter(status__in=ACTIVE_INTERVIEW + ('completed',)).exists()
    if application.status == 'interview' and not still_open:
        application.status = 'shortlisted'
        application.save()

def interview_list(request):
    interviews = Interview.objects.select_related(
        'application__applicant', 'application__job_post', 'evaluation'
    ).order_by('-interview_date', '-interview_time')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if query:
        interviews = interviews.filter(
            Q(application__application_number__icontains=query)
            | Q(application__applicant__first_name__icontains=query)
            | Q(application__applicant__last_name__icontains=query)
            | Q(interviewer__icontains=query)
        )
    if status in dict(Interview.STATUS_CHOICES):
        interviews = interviews.filter(status=status)
    else:
        status = ''

    try:
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
    except ValueError:
        start = end = None
    if start:
        interviews = interviews.filter(interview_date__gte=start)
    if end:
        interviews = interviews.filter(interview_date__lte=end)

    return render(request, 'jobportal/interview_list.html', {
        'interviews': interviews,
        'query': query,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Interview.STATUS_CHOICES,
    })

def interview_reschedule(request, pk):
    interview = get_object_or_404(
        Interview.objects.select_related('application__applicant', 'application__job_post'), pk=pk
    )
    application = interview.application
    if interview.status not in ACTIVE_INTERVIEW:
        messages.error(request, 'Only a scheduled, confirmed, or rescheduled interview can be changed.')
        return redirect('interview_list')
    if request.method == 'POST':
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.status = 'rescheduled'
            interview.save()
            notify_applicant(
                application,
                f'Your interview for {application.job_post.title} was moved to '
                f'{interview.interview_date:%B %d, %Y} at {interview.interview_time:%I:%M %p}.',
            )
            messages.success(request, 'The interview was rescheduled.')
            return redirect('interview_list')
    else:
        form = InterviewForm(instance=interview)
    return render(request, 'jobportal/interview_form.html', {
        'form': form, 'application': application, 'title': 'Reschedule interview',
    })

@require_POST
def interview_set_status(request, pk, action):
    interview = get_object_or_404(
        Interview.objects.select_related('application__applicant', 'application__job_post'), pk=pk
    )
    application = interview.application
    new_status, allowed = INTERVIEW_ACTIONS[action]
    if interview.status not in allowed:
        messages.error(request, f'An interview that is {interview.get_status_display().lower()} cannot use this action.')
    elif action in ('complete', 'no_show') and interview.interview_date > date.today():
        messages.error(request, 'This interview is in the future. You cannot mark it yet.')
    else:
        interview.status = new_status
        interview.save()
        if action == 'confirm':
            notify_applicant(
                application,
                f'Your interview for {application.job_post.title} on {interview.interview_date:%B %d, %Y} was confirmed.',
            )
        if action == 'cancel':
            notify_applicant(
                application,
                f'Your interview for {application.job_post.title} was cancelled.',
            )
        if action in ('cancel', 'no_show'):
            reset_application_after_interview(application)
        messages.success(request, f'The interview is now {interview.get_status_display().lower()}.')
    return redirect('interview_list')


def interview_evaluate(request, pk):
    interview = get_object_or_404(
        Interview.objects.select_related('application__applicant', 'application__job_post'), pk=pk
    )
    if interview.status != 'completed':
        messages.error(request, 'Only a completed interview can be evaluated.')
        return redirect('interview_list')
    evaluation = Evaluation.objects.filter(interview=interview).first()
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.interview = interview
            evaluation.save()
            messages.success(request, f'The evaluation was saved. The total is {evaluation.total_score} out of 60.')
            return redirect('interview_list')
    else:
        form = EvaluationForm(instance=evaluation)
    return render(request, 'jobportal/evaluation_form.html', {
        'form': form, 'interview': interview, 'application': interview.application,
    })

def candidate_selection(request, pk):
    job = get_object_or_404(JobPost.objects.select_related('employer'), pk=pk)
    applications = job.applications.filter(status='interview').select_related(
        'applicant', 'screening'
    ).prefetch_related('interviews__evaluation')
    candidates = []
    for application in applications:
        evaluations = [
            i.evaluation for i in application.interviews.all()
            if i.status == 'completed' and hasattr(i, 'evaluation')
        ]
        screening_total = float(application.screening.total_score) if hasattr(application, 'screening') else 0.0
        interview_percent = None
        combined = None
        if evaluations:
            average = sum(float(e.total_score) for e in evaluations) / len(evaluations)
            interview_percent = round(average * 100 / 60, 1)
            combined = round(screening_total * 0.4 + interview_percent * 0.6, 1)
        candidates.append({
            'application': application,
            'screening_total': screening_total,
            'interview_percent': interview_percent,
            'combined': combined,
            'evaluated': bool(evaluations),
        })
    candidates.sort(key=lambda c: (not c['evaluated'], -(c['combined'] or 0)))
    hires = Hiring.objects.filter(
        application__job_post=job, status='hired'
    ).select_related('application__applicant')
    open_slots = job.vacancies - hires.count()
    return render(request, 'jobportal/candidate_selection.html', {
        'job': job,
        'candidates': candidates,
        'hires': hires,
        'open_slots': max(open_slots, 0),
        'can_select': job.status == 'published' and open_slots > 0,
    })

def hiring_add(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('applicant', 'job_post__employer'), pk=pk
    )
    job = application.job_post
    if Hiring.objects.filter(application=application).exists():
        messages.error(request, 'This application already has a hiring record.')
        return redirect('hiring_list')
    if application.status != 'interview':
        messages.error(request, 'Only an applicant in the interview stage can be hired.')
        return redirect('application_detail', pk=application.pk)
    if job.status != 'published':
        messages.error(request, 'This job post is not open.')
        return redirect('candidate_selection', pk=job.pk)
    if not Evaluation.objects.filter(
        interview__application=application, interview__status='completed'
    ).exists():
        messages.error(request, 'Complete and evaluate an interview first.')
        return redirect('candidate_selection', pk=job.pk)
    hired_total = Hiring.objects.filter(application__job_post=job, status='hired').count()
    if hired_total >= job.vacancies:
        messages.error(request, 'All vacancies for this job are already filled.')
        return redirect('candidate_selection', pk=job.pk)
    if request.method == 'POST':
        form = HiringForm(request.POST)
        if form.is_valid():
            hiring = form.save(commit=False)
            hiring.application = application
            hiring.status = 'hired'
            hiring.save()
            filled = finish_hiring(hiring)
            note = ' The job post is now filled and the other applicants were marked not selected.' if filled else ''
            messages.success(request, f'{application.applicant} was hired as {hiring.position}.{note}')
            return redirect('hiring_list')
    else:
        form = HiringForm(initial={'position': job.title})
    return render(request, 'jobportal/hiring_form.html', {
        'form': form, 'application': application, 'title': 'Hire applicant',
    })

def hiring_list(request):
    hirings = Hiring.objects.select_related(
        'application__applicant', 'application__job_post__employer'
    ).order_by('-hiring_date', '-id')
    query = request.GET.get('q', '').strip()
    if query:
        hirings = hirings.filter(
            Q(position__icontains=query)
            | Q(application__application_number__icontains=query)
            | Q(application__applicant__first_name__icontains=query)
            | Q(application__applicant__last_name__icontains=query)
        )
    return render(request, 'jobportal/hiring_list.html', {
        'hirings': hirings,
        'query': query,
    })

def hiring_edit(request, pk):
    hiring = get_object_or_404(
        Hiring.objects.select_related('application__applicant', 'application__job_post'), pk=pk
    )
    if request.method == 'POST':
        form = HiringForm(request.POST, instance=hiring)
        if form.is_valid():
            form.save()
            messages.success(request, 'The hiring record was updated.')
            return redirect('hiring_list')
    else:
        form = HiringForm(instance=hiring)
    return render(request, 'jobportal/hiring_form.html', {
        'form': form, 'application': hiring.application, 'title': 'Edit hiring record',
    })

OPEN_APPLICATION_STATUSES = ('submitted', 'under_review', 'shortlisted', 'interview')

def finish_hiring(hiring):
    application = hiring.application
    job = application.job_post
    application.status = 'hired'
    application.save()
    notify_applicant(
        application,
        f'You were hired as {hiring.position} at {job.employer.company_name}. '
        f'Your start date is {hiring.start_date:%B %d, %Y}.',
    )
    hired_total = Hiring.objects.filter(application__job_post=job, status='hired').count()
    if hired_total < job.vacancies:
        return False
    job.status = 'filled'
    job.save()
    for other in job.applications.filter(status__in=OPEN_APPLICATION_STATUSES):
        other.interviews.filter(status__in=ACTIVE_INTERVIEW).update(status='cancelled')
        other.status = 'not_selected'
        other.save()
        notify_applicant(
            other,
            f'The position {job.title} was filled. Your application {other.application_number} was not selected.',
        )
    return True