from django import forms
from .models import Course, Employer, Enrollment, JobCategory


class EmployerForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label='Select a course',
        error_messages={'required': 'Please select a course.'},
    )

    class Meta:
        model = Employer
        fields = [
            'company_name', 'company_type', 'contact_person',
            'contact_number', 'email', 'address', 'website',
            'company_description', 'course', 'status',
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

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name']
        labels = {'course_name': 'Course name'}
        error_messages = {
            'course_name': {'required': 'Course name cannot be empty.'},
        }

    def clean_course_name(self):
        name = self.cleaned_data['course_name'].strip()
        duplicates = Course.objects.filter(course_name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('This course already exists.')
        return name

class EnrollmentForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label='Select a course',
        error_messages={'required': 'Please select a course.'},
    )

    class Meta:
        model = Enrollment
        fields = ['student_name', 'college_id', 'course', 'enrollment_date']
        widgets = {
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }