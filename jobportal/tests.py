from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date

from .models import (
    Applicant, ApplicantProfile, Application, Employer, JobCategory, JobPost,
    Role, Screening, UserProfile,
)
from django.contrib.auth.models import User


class ApplicationWorkflowTests(TestCase):
    def setUp(self):
        admin_role = Role.objects.create(name='Admin')
        admin = User.objects.create_superuser(
            username='testadmin',
            email='admin@example.com',
            password='test-password',
        )
        UserProfile.objects.create(user=admin, role=admin_role)
        self.client.force_login(admin)

        self.employer = Employer.objects.create(
            company_name='Example Ltd',
            company_type='Private',
            contact_person='Hiring Manager',
            contact_number='1234567890',
            email='employer@example.com',
            address='Example address',
        )
        self.category = JobCategory.objects.create(name='Engineering')
        self.job = JobPost.objects.create(
            employer=self.employer,
            category=self.category,
            title='Engineer',
            description='Build software.',
            employment_type='full_time',
            location='Remote',
            application_deadline=date(2099, 12, 31),
            status='published',
        )
        self.applicant = Applicant.objects.create(
            applicant_number='APP-0001',
            first_name='Ada',
            last_name='Lovelace',
            contact_number='1234567890',
            email='ada@example.com',
        )
        self.profile = ApplicantProfile.objects.create(applicant=self.applicant)
        self.application = Application.objects.create(
            application_number='APL-0001',
            applicant=self.applicant,
            job_post=self.job,
            status='submitted',
        )

    def test_application_history_filters_by_status_and_date(self):
        rejected = Application.objects.create(
            application_number='APL-0002',
            applicant=self.applicant,
            job_post=self.job,
            status='rejected',
        )

        response = self.client.get(
            reverse('applicant_applications', args=[self.applicant.pk]),
            {'status': 'submitted'},
        )

        self.assertContains(response, self.application.application_number)
        self.assertNotContains(response, rejected.application_number)

        tomorrow = (timezone.localdate() + timezone.timedelta(days=1)).isoformat()
        response = self.client.get(
            reverse('applicant_applications', args=[self.applicant.pk]),
            {'date_from': tomorrow},
        )
        self.assertContains(response, 'No applications found.')

    def test_application_management_and_shortlist_pages_render(self):
        response = self.client.get(
            reverse('application_list'),
            {
                'q': 'Lovelace',
                'job': str(self.job.pk),
                'status': 'submitted',
            },
        )
        self.assertContains(response, self.application.application_number)
        self.assertContains(response, 'Not scored')

        self.application.status = 'shortlisted'
        self.application.save()
        Screening.objects.create(
            application=self.application,
            total_score=83,
            status='shortlisted',
        )
        response = self.client.get(reverse('shortlist_list'))
        self.assertContains(response, self.application.application_number)
        self.assertContains(response, '83')

    def test_screening_flow_validates_scores_and_shortlist_threshold(self):
        detail_url = reverse('application_detail', args=[self.application.pk])
        review_url = reverse('application_review_start', args=[self.application.pk])
        screening_url = reverse('screening_review', args=[self.application.pk])
        score_url = reverse('screening_score', args=[self.application.pk])
        shortlist_url = reverse('application_shortlist', args=[self.application.pk])

        response = self.client.get(detail_url)
        self.assertContains(response, 'Start review')

        self.client.post(review_url)
        self.assertEqual(
            Application.objects.get(pk=self.application.pk).status, 'under_review'
        )

        self.client.get(screening_url)
        screening = Screening.objects.get(application=self.application)
        self.client.post(screening_url, {'remarks': 'Matches the listed requirements.'})
        screening.refresh_from_db()
        self.assertEqual(screening.remarks, 'Matches the listed requirements.')

        invalid_scores = {
            'education_score': '21',
            'experience_score': '20',
            'skills_score': '25',
            'certifications_score': '8',
            'resume_score': '12',
        }
        response = self.client.post(score_url, invalid_scores)
        self.assertContains(response, 'Enter a score from 0 to 20.')

        passing_scores = {
            'education_score': '18',
            'experience_score': '20',
            'skills_score': '25',
            'certifications_score': '8',
            'resume_score': '12',
        }
        self.client.post(score_url, passing_scores)
        screening.refresh_from_db()
        self.assertEqual(screening.total_score, 83)

        self.client.post(shortlist_url)
        self.assertEqual(
            Application.objects.get(pk=self.application.pk).status, 'shortlisted'
        )
        screening.refresh_from_db()
        self.assertEqual(screening.status, 'shortlisted')

    def test_shortlist_rejects_scores_below_threshold_and_closed_screening(self):
        screening = Screening.objects.create(
            application=self.application,
            total_score=59,
            status='under_review',
        )
        self.application.status = 'under_review'
        self.application.save()

        response = self.client.post(
            reverse('application_shortlist', args=[self.application.pk])
        )
        self.assertEqual(
            Application.objects.get(pk=self.application.pk).status, 'under_review'
        )
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('below the passing score' in str(message) for message in messages))

        self.application.status = 'rejected'
        self.application.save()
        response = self.client.get(
            reverse('screening_score', args=[self.application.pk])
        )
        self.assertRedirects(
            response, reverse('application_detail', args=[self.application.pk])
        )
        screening.refresh_from_db()
        self.assertEqual(screening.total_score, 59)
