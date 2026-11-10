from datetime import date
from django import forms
from django.db.models import Q
from .models import Employer, JobCategory, JobPost, JobRequirement


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