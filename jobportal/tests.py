from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date

from .models import (
    Applicant, ApplicantProfile, Application, Employer, JobCategory, JobPost,
    Notification, Role, Screening, UserProfile,
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
            'certifications_score': '10',
            'resume_score': '10',
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


class UserManagementTests(TestCase):
    def setUp(self):
        admin_role = Role.objects.create(name='Admin')
        self.admin = User.objects.create_superuser(
            username='useradmin',
            email='useradmin@example.com',
            password='test-password',
        )
        UserProfile.objects.create(user=self.admin, role=admin_role)
        self.client.force_login(self.admin)
        self.applicant_role = Role.objects.create(name='Applicant')
        self.applicant = Applicant.objects.create(
            applicant_number='APP-1000',
            first_name='Grace',
            last_name='Hopper',
            contact_number='1234567890',
            email='grace@example.com',
        )

    def test_user_creation_and_account_toggle(self):
        response = self.client.post(reverse('user_add'), {
            'username': 'grace.hopper',
            'email': self.applicant.email,
            'role': self.applicant_role.pk,
            'password1': 'Strong-P@ssw0rd-9',
            'password2': 'Strong-P@ssw0rd-9',
        })
        self.assertRedirects(response, reverse('user_list'))
        user = User.objects.get(username='grace.hopper')
        self.assertEqual(user.email, self.applicant.email)
        self.assertEqual(user.profile.role, self.applicant_role)

        response = self.client.get(reverse('user_list'))
        self.assertContains(response, 'grace.hopper')
        self.client.post(reverse('user_toggle', args=[user.pk]))
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_dashboard_and_report_pages_render(self):
        for name in (
            'dashboard', 'report_index', 'report_jobs', 'report_applicants',
            'report_applications', 'report_interviews', 'report_hiring',
            'report_screening', 'report_employers',
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_recruiter_and_manager_landing_pages_are_allowed(self):
        for role_name, destination in (
            ('Recruiter', 'application_list'),
            ('Manager', 'report_index'),
        ):
            with self.subTest(role=role_name):
                role = Role.objects.create(name=role_name)
                user = User.objects.create_user(
                    username=role_name.lower(),
                    password='test-password',
                )
                UserProfile.objects.create(user=user, role=role)
                self.client.force_login(user)
                response = self.client.get(reverse('landing'))
                self.assertRedirects(response, reverse(destination))


class ApplicantOwnershipTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name='Applicant')
        self.owner = Applicant.objects.create(
            applicant_number='APP-0101',
            first_name='Owner',
            last_name='Applicant',
            contact_number='1234567890',
            email='owner@example.com',
        )
        self.other = Applicant.objects.create(
            applicant_number='APP-0102',
            first_name='Other',
            last_name='Applicant',
            contact_number='1234567891',
            email='other@example.com',
        )
        ApplicantProfile.objects.create(applicant=self.owner)
        ApplicantProfile.objects.create(applicant=self.other)
        user = User.objects.create_user(
            username='applicant-owner',
            email=self.owner.email,
            password='test-password',
        )
        UserProfile.objects.create(user=user, role=role)
        self.client.force_login(user)

        employer = Employer.objects.create(
            company_name='Ownership Ltd',
            company_type='Private',
            contact_person='Contact',
            contact_number='1234567890',
            email='contact@example.com',
            address='Example address',
        )
        category = JobCategory.objects.create(name='Ownership')
        self.job = JobPost.objects.create(
            employer=employer,
            category=category,
            title='Ownership role',
            description='A test position.',
            employment_type='full_time',
            location='Remote',
            application_deadline=date(2099, 12, 31),
            status='published',
        )
        self.owner_application = Application.objects.create(
            application_number='APL-0101',
            applicant=self.owner,
            job_post=self.job,
        )
        self.other_application = Application.objects.create(
            application_number='APL-0102',
            applicant=self.other,
            job_post=self.job,
        )
        self.owner_notification = Notification.objects.create(
            applicant=self.owner,
            message='Owner notification',
        )
        self.other_notification = Notification.objects.create(
            applicant=self.other,
            message='Other notification',
        )

    def test_applicant_cannot_open_another_applicants_records(self):
        response = self.client.get(
            reverse('applicant_profile', args=[self.other.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('landing'))

        response = self.client.get(
            reverse('application_confirmation', args=[self.other_application.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('landing'))

        response = self.client.get(
            reverse('application_confirmation', args=[self.owner_application.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_applicant_notifications_are_limited_to_their_records(self):
        response = self.client.get(
            reverse('notification_list'), {'applicant': self.other.pk}
        )
        self.assertContains(response, 'Owner notification')
        self.assertNotContains(response, 'Other notification')
        self.assertNotContains(response, 'All applicants')

        self.client.post(
            reverse('notification_mark_all_read'),
            {'applicant': self.other.pk},
        )
        self.owner_notification.refresh_from_db()
        self.other_notification.refresh_from_db()
        self.assertTrue(self.owner_notification.is_read)
        self.assertFalse(self.other_notification.is_read)

    def test_applicant_application_form_only_offers_their_record(self):
        response = self.client.get(reverse('job_apply', args=[self.job.pk]))
        form = response.context['form']
        self.assertEqual(
            list(form.fields['applicant'].queryset),
            [self.owner],
        )
