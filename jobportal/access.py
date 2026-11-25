from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect

OPEN_NAMES = {'login', 'logout', 'landing', 'home'}

ADMIN_ONLY = {
    'employer_list', 'employer_add', 'employer_toggle',
    'category_add', 'category_edit', 'category_toggle',
    'applicant_list', 'applicant_add', 'applicant_toggle',
    'report_applicants',
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


def get_role(user):
    if not user.is_authenticated:
        return ''
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role.name.strip().lower()
    except (ObjectDoesNotExist, AttributeError):
        return ''


def role_context(request):
    user = getattr(request, 'user', None)
    role = get_role(user) if user is not None else ''
    context = {'user_role': role, 'my_applicant_id': None}
    if role == 'applicant' and user.email:
        from .models import Applicant
        context['my_applicant_id'] = (
            Applicant.objects.filter(email__iexact=user.email)
            .values_list('pk', flat=True).first()
        )
    return context


def can_access(role, name):
    if role == 'admin':
        return True
    if role == 'employer':
        return name not in EMPLOYER_BLOCKED
    if role == 'applicant':
        return name in APPLICANT_ALLOWED
    return False


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
        if name in OPEN_NAMES or can_access(get_role(request.user), name):
            return None
        messages.error(request, 'Your account cannot open that page.')
        return redirect('landing')
