import os
from datetime import date
from django import forms
from django.db.models import Q
from .models import (
    Applicant, ApplicantProfile, Application, Employer, JobCategory, JobPost, JobRequirement,
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
        super().__init__(*args, **kwargs)
        self.fields['applicant'].queryset = Applicant.objects.order_by('last_name', 'first_name')
        self.fields['applicant'].empty_label = 'Select an applicant'
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
        return cleaned