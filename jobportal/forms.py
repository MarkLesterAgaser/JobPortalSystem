import os
from datetime import date
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import (
    Applicant, ApplicantProfile, Application, Employer, JobCategory, JobPost,
    JobRequirement, Screening, Interview, Evaluation, Hiring, Role,
)


class EmployerForm(forms.ModelForm):
    class Meta:
        model = Employer
        fields = [
            'company_name', 'company_type', 'contact_person',
            'contact_number', 'email', 'address', 'website',
            'company_description', 'status',
        ]
        widgets = {
            'company_description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_company_name(self):
        name = self.cleaned_data['company_name'].strip()
        duplicates = Employer.objects.filter(company_name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('An employer with this company name already exists.')
        return name

    def clean_contact_number(self):
        number = self.cleaned_data['contact_number'].strip()
        digits = [ch for ch in number if ch.isdigit()]
        if any(ch not in '0123456789 +-()' for ch in number) or not 7 <= len(digits) <= 13:
            raise forms.ValidationError('Enter a valid contact number.')
        return number

class JobCategoryForm(forms.ModelForm):
    class Meta:
        model = JobCategory
        fields = ['name', 'is_active']
        labels = {'name': 'Category name', 'is_active': 'Active'}

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        duplicates = JobCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('A category with this name already exists.')
        return name


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'employer', 'category', 'title', 'description',
            'employment_type', 'location', 'salary_min', 'salary_max',
            'vacancies', 'required_experience', 'education_requirement',
            'application_deadline', 'status',
        ]
        labels = {
            'category': 'Job category',
            'description': 'Description and responsibilities',
            'required_experience': 'Required experience',
            'education_requirement': 'Education requirement',
            'application_deadline': 'Application deadline',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'application_deadline': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'
            ),
        }

    def clean_salary_min(self):
        value = self.cleaned_data['salary_min']
        if value is not None and value < 0:
            raise forms.ValidationError('Salary cannot be negative.')
        return value

    def clean_salary_max(self):
        value = self.cleaned_data['salary_max']
        if value is not None and value < 0:
            raise forms.ValidationError('Salary cannot be negative.')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employer'].queryset = Employer.objects.filter(
            Q(status='active') | Q(pk=self.instance.employer_id)
        ).order_by('company_name')
        self.fields['category'].queryset = JobCategory.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.category_id)
        ).order_by('name')
        self.fields['employer'].empty_label = 'Select an employer'
        self.fields['category'].empty_label = 'Select a category'
        self.fields.pop('status')

    def clean_vacancies(self):
        vacancies = self.cleaned_data['vacancies']
        if vacancies < 1:
            raise forms.ValidationError('Vacancies must be at least 1.')
        return vacancies

    def clean_application_deadline(self):
        deadline = self.cleaned_data['application_deadline']
        if 'application_deadline' in self.changed_data and deadline < date.today():
            raise forms.ValidationError('The deadline cannot be in the past.')
        return deadline

    def clean(self):
        cleaned = super().clean()
        low = cleaned.get('salary_min')
        high = cleaned.get('salary_max')
        if low is not None and high is not None and low > high:
            self.add_error('salary_max', 'Maximum salary cannot be lower than minimum salary.')
        return cleaned


class JobRequirementForm(forms.ModelForm):
    class Meta:
        model = JobRequirement
        fields = [
            'education_qualification', 'skills', 'work_experience',
            'certifications', 'other_qualifications',
        ]
        labels = {'skills': 'Skills and technical skills'}
        widgets = {
            'skills': forms.Textarea(attrs={'rows': 3}),
            'other_qualifications': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        if not any((cleaned.get(name) or '').strip() for name in self.fields):
            raise forms.ValidationError('Fill in at least one requirement.')
        return cleaned


class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = [
            'first_name', 'last_name', 'contact_number', 'email',
            'address', 'date_of_birth', 'career_objective', 'status',
        ]
        labels = {
            'date_of_birth': 'Date of birth',
            'career_objective': 'Career objective',
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'career_objective': forms.Textarea(attrs={'rows': 4}),
        }

    def _clean_person_name(self, field, label):
        value = self.cleaned_data[field].strip()
        if any(ch.isdigit() for ch in value):
            raise forms.ValidationError(f'{label} cannot contain numbers.')
        return value

    def clean_first_name(self):
        return self._clean_person_name('first_name', 'First name')

    def clean_last_name(self):
        return self._clean_person_name('last_name', 'Last name')

    def clean_contact_number(self):
        number = self.cleaned_data['contact_number'].strip()
        digits = [ch for ch in number if ch.isdigit()]
        if any(ch not in '0123456789 +-()' for ch in number) or not 7 <= len(digits) <= 13:
            raise forms.ValidationError('Enter a valid contact number.')
        return number

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        duplicates = Applicant.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('An applicant with this email already exists.')
        return email

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        if dob:
            today = date.today()
            if dob >= today:
                raise forms.ValidationError('Date of birth must be in the past.')
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 16:
                raise forms.ValidationError('The applicant must be at least 16 years old.')
        return dob


class ApplicantProfileInfoForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['training', 'references']
        labels = {
            'training': 'Training and seminars',
            'references': 'References',
        }
        widgets = {
            'training': forms.Textarea(attrs={'rows': 5}),
            'references': forms.Textarea(attrs={'rows': 5}),
        }


class ApplicantEducationForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['education']
        labels = {'education': 'Education history'}
        help_texts = {'education': 'Write the school, course, and year graduated. Use one line for each entry.'}
        widgets = {'education': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['education'].required = True


class ApplicantSkillsExperienceForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['skills', 'work_experience', 'certifications']
        labels = {
            'skills': 'Skills',
            'work_experience': 'Work experience',
            'certifications': 'Certifications',
        }
        help_texts = {
            'skills': 'Write one skill on each line.',
            'work_experience': 'Write the company, position, and years. Use one line for each job.',
        }
        widgets = {
            'skills': forms.Textarea(attrs={'rows': 4}),
            'work_experience': forms.Textarea(attrs={'rows': 5}),
            'certifications': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].required = True


ALLOWED_UPLOADS = ('.pdf', '.doc', '.docx')
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_upload(upload):
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in ALLOWED_UPLOADS:
        raise forms.ValidationError('Upload a PDF, DOC, or DOCX file.')
    if upload.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError('The file must be 5 MB or smaller.')
    return upload


class ResumeUploadForm(forms.Form):
    resume = forms.FileField(
        label='Resume file',
        help_text='PDF, DOC, or DOCX. Maximum 5 MB.',
        widget=forms.FileInput(attrs={'accept': '.pdf,.doc,.docx'}),
    )

    def clean_resume(self):
        return validate_upload(self.cleaned_data['resume'])


class ApplicationForm(forms.ModelForm):
    document = forms.FileField(
        required=False,
        label='Supporting document',
        help_text='Optional. PDF, DOC, or DOCX. Maximum 5 MB.',
        widget=forms.FileInput(attrs={'accept': '.pdf,.doc,.docx'}),
    )

    class Meta:
        model = Application
        fields = ['applicant', 'cover_letter']
        labels = {'cover_letter': 'Cover letter'}
        widgets = {'cover_letter': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, **kwargs):
        self.job = kwargs.pop('job')
        self.only_applicant = kwargs.pop('only_applicant', None)
        super().__init__(*args, **kwargs)
        self.fields['applicant'].queryset = Applicant.objects.order_by('last_name', 'first_name')
        self.fields['applicant'].empty_label = 'Select an applicant'
        if self.only_applicant is not None:
            self.fields['applicant'].queryset = Applicant.objects.filter(pk=self.only_applicant)
            self.fields['applicant'].empty_label = None
        self.fields['applicant'].label_from_instance = (
            lambda a: f'{a.last_name}, {a.first_name} ({a.applicant_number})'
        )

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            validate_upload(document)
        return document

    def clean(self):
        cleaned = super().clean()
        job = self.job
        applicant = cleaned.get('applicant')
        if job.status != 'published':
            raise forms.ValidationError('This job post is not open for applications.')
        if job.application_deadline < date.today():
            raise forms.ValidationError('The application deadline has passed.')
        if applicant:
            if applicant.status != 'active':
                self.add_error('applicant', 'This applicant is inactive.')
            elif Application.objects.filter(applicant=applicant, job_post=job).exists():
                self.add_error('applicant', 'This applicant already applied to this job.')
            else:
                profile = ApplicantProfile.objects.filter(applicant=applicant).first()
                if not profile or not profile.resume:
                    self.add_error('applicant', 'Upload a resume on the applicant profile first.')
                elif not profile.education.strip() or not profile.skills.strip():
                    self.add_error('applicant', 'Complete the education and skills on the applicant profile first.')
        return cleaned


class ScreeningRemarksForm(forms.ModelForm):
    class Meta:
        model = Screening
        fields = ['remarks']
        labels = {'remarks': 'Screening remarks'}
        help_texts = {'remarks': 'Write how the applicant matches the job requirements.'}
        widgets = {'remarks': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['remarks'].required = True


SCORE_LIMITS = {
    'education_score': 20,
    'experience_score': 30,
    'skills_score': 30,
    'certifications_score': 10,
    'resume_score': 10,
}


class ScreeningScoreForm(forms.ModelForm):
    class Meta:
        model = Screening
        fields = list(SCORE_LIMITS)
        labels = {
            'education_score': 'Education score',
            'experience_score': 'Experience score',
            'skills_score': 'Skills score',
            'certifications_score': 'Certifications score',
            'resume_score': 'Resume and profile score',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, limit in SCORE_LIMITS.items():
            self.fields[name].help_text = f'Enter 0 to {limit}.'
            self.fields[name].widget.attrs.update({'min': 0, 'max': limit})

    def clean(self):
        cleaned = super().clean()
        for name, limit in SCORE_LIMITS.items():
            value = cleaned.get(name)
            if value is not None and not 0 <= value <= limit:
                self.add_error(name, f'Enter a score from 0 to {limit}.')
        return cleaned

    def save(self, commit=True):
        screening = super().save(commit=False)
        screening.total_score = sum(getattr(screening, name) for name in SCORE_LIMITS)
        if commit:
            screening.save()
        return screening


ACTIVE_INTERVIEW = ('scheduled', 'confirmed', 'rescheduled')

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['interviewer', 'interview_date', 'interview_time', 'location', 'remarks']
        labels = {
            'interviewer': 'Interviewer name',
            'interview_date': 'Interview date',
            'interview_time': 'Interview time',
            'location': 'Location or meeting link',
        }
        widgets = {
            'interview_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'interview_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].required = True

    def clean_interview_date(self):
        day = self.cleaned_data['interview_date']
        if 'interview_date' in self.changed_data and day < date.today():
            raise forms.ValidationError('The interview date cannot be in the past.')
        return day

    def clean_interview_time(self):
        at = self.cleaned_data['interview_time']
        if not 7 <= at.hour <= 19:
            raise forms.ValidationError('Pick a time between 7 AM and 7:59 PM.')
        return at

    def clean(self):
        cleaned = super().clean()
        interviewer = cleaned.get('interviewer')
        day = cleaned.get('interview_date')
        at = cleaned.get('interview_time')
        if interviewer and day and at:
            clash = Interview.objects.filter(
                interviewer__iexact=interviewer,
                interview_date=day,
                interview_time=at,
                status__in=ACTIVE_INTERVIEW,
            )
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError('This interviewer already has an interview at that date and time.')
        return cleaned


EVALUATION_FIELDS = [
    'communication_score', 'technical_score', 'problem_solving_score',
    'attitude_score', 'experience_score', 'cultural_fit_score',
]
EVALUATION_MAX = 10

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = EVALUATION_FIELDS + ['overall_notes']
        labels = {
            'communication_score': 'Communication',
            'technical_score': 'Technical skills',
            'problem_solving_score': 'Problem solving',
            'attitude_score': 'Attitude',
            'experience_score': 'Relevant experience',
            'cultural_fit_score': 'Cultural fit',
            'overall_notes': 'Overall notes',
        }
        help_texts = {'overall_notes': 'Write your overall impression of the applicant.'}
        widgets = {'overall_notes': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in EVALUATION_FIELDS:
            self.fields[name].help_text = f'Enter 0 to {EVALUATION_MAX}.'
            self.fields[name].widget.attrs.update({'min': 0, 'max': EVALUATION_MAX})
        self.fields['overall_notes'].required = True

    def clean(self):
        cleaned = super().clean()
        for name in EVALUATION_FIELDS:
            value = cleaned.get(name)
            if value is not None and not 0 <= value <= EVALUATION_MAX:
                self.add_error(name, f'Enter a score from 0 to {EVALUATION_MAX}.')
        return cleaned


class HiringForm(forms.ModelForm):
    class Meta:
        model = Hiring
        fields = ['position', 'salary', 'start_date', 'remarks']
        labels = {
            'position': 'Position',
            'salary': 'Monthly salary',
            'start_date': 'Start date',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_salary(self):
        salary = self.cleaned_data['salary']
        if salary <= 0:
            raise forms.ValidationError('Salary must be more than 0.')
        return salary

    def clean_start_date(self):
        start = self.cleaned_data['start_date']
        if 'start_date' in self.changed_data and start < date.today():
            raise forms.ValidationError('The start date cannot be in the past.')
        return start


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(
        required=False,
        help_text='Required for applicant logins. It must match the email of a registered applicant.',
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.order_by('name'), empty_label='Select a role'
    )
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'The passwords do not match.')
        elif password1:
            try:
                validate_password(password1)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        role = cleaned.get('role')
        email = (cleaned.get('email') or '').strip()
        if role and role.name.strip().lower() == 'applicant':
            if not email:
                self.add_error('email', 'Enter the email of the applicant this login belongs to.')
            elif not Applicant.objects.filter(email__iexact=email).exists():
                self.add_error('email', 'No registered applicant has this email. Register the applicant first.')
            elif User.objects.filter(email__iexact=email).exists():
                self.add_error('email', 'Another login already uses this email.')
        return cleaned