from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect

OPEN_NAMES = {'login', 'logout', 'landing', 'home', 'password_change'}

ADMIN_ONLY = {
    'employer_list', 'employer_add', 'employer_toggle',
    'employer_edit',
    'category_add', 'category_edit', 'category_toggle',
    'applicant_list', 'applicant_add', 'applicant_toggle',
    'report_applicants', 'user_list', 'user_add', 'user_toggle',
    'report_employers',
}

EMPLOYER_BLOCKED = ADMIN_ONLY | {
    'applicant_edit', 'applicant_profile_edit', 'applicant_education',
    'applicant_skills', 'applicant_resume', 'applicant_resume_delete',
    'job_apply', 'notification_list', 'notification_mark_read',
    'notification_mark_all_read',
}

APPLICANT_ALLOWED = {
    'job_search', 'jobpost_detail', 'job_apply', 'application_confirmation',
    'applicant_profile', 'applicant_profile_edit', 'applicant_education',
    'applicant_skills', 'applicant_resume', 'applicant_resume_delete',
    'applicant_edit', 'applicant_applications', 'notification_list',
    'notification_mark_read', 'notification_mark_all_read',
}

RECRUITER_ALLOWED = {
    'dashboard', 'job_search', 'jobpost_detail', 'applicant_profile',
    'application_list', 'application_detail', 'application_review_start',
    'application_confirmation', 'screening_review', 'screening_score',
    'application_shortlist', 'application_reject', 'shortlist_list',
    'interview_schedule', 'interview_list', 'interview_reschedule',
    'interview_confirm', 'interview_complete', 'interview_no_show',
    'interview_cancel', 'interview_evaluate', 'candidate_selection',
    'hiring_add', 'hiring_list', 'hiring_edit', 'report_screening',
}

MANAGER_ALLOWED = {
    'dashboard', 'job_search', 'jobpost_detail', 'report_index',
    'report_jobs', 'report_applications', 'report_screening',
    'report_interviews', 'report_hiring', 'report_employers',
    'report_applicants',
}


def get_role(user):
    if not user.is_authenticated:
        return ''
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role.name.strip().lower()
    except (ObjectDoesNotExist, AttributeError):
        return ''


def can_access(role, name):
    if role == 'admin':
        return True
    if role == 'employer':
        return name not in EMPLOYER_BLOCKED
    if role == 'applicant':
        return name in APPLICANT_ALLOWED
    if role == 'recruiter':
        return name in RECRUITER_ALLOWED
    if role == 'manager':
        return name in MANAGER_ALLOWED
    return False


class Allowed:
    def __init__(self, role):
        self.role = role

    def __contains__(self, name):
        return can_access(self.role, name)


def role_context(request):
    user = getattr(request, 'user', None)
    role = get_role(user) if user is not None else ''
    context = {'user_role': role, 'my_applicant_id': None, 'can_open': Allowed(role)}
    if role == 'applicant' and user.email:
        from .models import Applicant
        context['my_applicant_id'] = (
            Applicant.objects.filter(email__iexact=user.email)
            .values_list('pk', flat=True).first()
        )
    return context


APPLICANT_PK_NAMES = {
    'applicant_profile', 'applicant_profile_edit', 'applicant_education',
    'applicant_skills', 'applicant_resume', 'applicant_resume_delete',
    'applicant_edit', 'applicant_applications',
}


def applicant_id_for(user):
    if not user.is_authenticated or not user.email:
        return None
    from .models import Applicant
    return (
        Applicant.objects.filter(email__iexact=user.email)
        .values_list('pk', flat=True).first()
    )


def owns_page(user, name, kwargs):
    from .models import Application, Notification
    mine = applicant_id_for(user)
    if mine is None:
        return name not in APPLICANT_PK_NAMES and name not in (
            'application_confirmation', 'notification_mark_read'
        )
    pk = kwargs.get('pk')
    if name in APPLICANT_PK_NAMES:
        return pk == mine
    if name == 'application_confirmation':
        return Application.objects.filter(pk=pk, applicant_id=mine).exists()
    if name == 'notification_mark_read':
        return Notification.objects.filter(pk=pk, applicant_id=mine).exists()
    return True


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith(('/admin/', '/static/', '/media/')):
            return None
        match = request.resolver_match
        if match is None:
            return None
        name = match.url_name
        if not request.user.is_authenticated:
            if name == 'login':
                return None
            return redirect_to_login(request.get_full_path())
        role = get_role(request.user)
        if name in OPEN_NAMES:
            return None
        if not can_access(role, name):
            messages.error(request, 'Your account cannot open that page.')
            return redirect('landing')
        if role == 'applicant' and not owns_page(request.user, name, view_kwargs):
            messages.error(request, 'You can only open your own records.')
            return redirect('landing')
        return None
