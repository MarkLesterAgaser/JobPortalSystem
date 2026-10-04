from django.contrib import admin
from .models import (
    Employer, JobCategory, JobPost, JobRequirement,
    Applicant, ApplicantProfile, Application, ApplicationDocument,
    Screening, Interview, Evaluation, Hiring, Notification,
    Role, UserProfile
)

admin.site.register(Employer)
admin.site.register(JobCategory)
admin.site.register(JobPost)
admin.site.register(JobRequirement)
admin.site.register(Applicant)
admin.site.register(ApplicantProfile)
admin.site.register(Application)
admin.site.register(ApplicationDocument)
admin.site.register(Screening)
admin.site.register(Interview)
admin.site.register(Evaluation)
admin.site.register(Hiring)
admin.site.register(Notification)
admin.site.register(Role)
admin.site.register(UserProfile)