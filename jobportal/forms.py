from datetime import date
from django import forms
from django.db.models import Q
from .models import (
    Applicant, ApplicantProfile, Employer, JobCategory, JobPost, JobRequirement,
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