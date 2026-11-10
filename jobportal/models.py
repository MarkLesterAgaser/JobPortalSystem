from django.db import models
from django.contrib.auth.models import User


# ---------- EMPLOYER MODULE ----------
class Employer(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    company_name = models.CharField(max_length=200)
    company_type = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    company_description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


# ---------- JOB POST MODULE ----------
class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class JobPost(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('filled', 'Filled'),
    ]

    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name='job_posts')
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    location = models.CharField(max_length=150)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vacancies = models.PositiveIntegerField(default=1)
    required_experience = models.CharField(max_length=100, blank=True)
    education_requirement = models.CharField(max_length=150, blank=True)
    application_deadline = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class JobRequirement(models.Model):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='requirements')
    education_qualification = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)
    work_experience = models.CharField(max_length=200, blank=True)
    certifications = models.CharField(max_length=200, blank=True)
    other_qualifications = models.TextField(blank=True)

    def __str__(self):
        return f"Requirements for {self.job_post.title}"


# ---------- APPLICANT MODULE ----------
class Applicant(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    applicant_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    career_objective = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ApplicantProfile(models.Model):
    applicant = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name='profile')
    education = models.TextField(blank=True)
    work_experience = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    training = models.TextField(blank=True)
    references = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.applicant}"


# ---------- APPLICATION MODULE ----------
class Application(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('interview', 'Interview'),
        ('hired', 'Hired'),
        ('not_selected', 'Not Selected'),
    ]

    application_number = models.CharField(max_length=20, unique=True)
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='applications')
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField(blank=True)
    application_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='submitted')

    def __str__(self):
        return self.application_number


class ApplicationDocument(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='application_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.application.application_number}"


# ---------- SCREENING MODULE ----------
class Screening(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='screening')
    education_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    experience_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    skills_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    certifications_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    resume_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='submitted')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Screening for {self.application.application_number}"


# ---------- INTERVIEW MODULE ----------
class Interview(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interviewer = models.CharField(max_length=150)
    interview_date = models.DateField()
    interview_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='scheduled')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Interview for {self.application.application_number}"


class Evaluation(models.Model):
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='evaluation')
    communication_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    technical_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    problem_solving_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    attitude_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    experience_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cultural_fit_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Evaluation for {self.interview}"


# ---------- HIRING MODULE ----------
class Hiring(models.Model):
    STATUS_CHOICES = [('hired', 'Hired'), ('withdrawn', 'Withdrawn')]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='hiring')
    position = models.CharField(max_length=150)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hiring_date = models.DateField(auto_now_add=True)
    start_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='hired')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Hiring record for {self.application.application_number}"


# ---------- NOTIFICATION MODULE ----------
class Notification(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message


# ---------- USERS AND ROLES ----------
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"