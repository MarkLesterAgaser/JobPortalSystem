from django.core.management.base import BaseCommand

from jobportal.models import Role


class Command(BaseCommand):
    help = 'Create the Admin, Employer, Applicant, Recruiter, and Manager roles.'

    def handle(self, *args, **options):
        for name in ('Admin', 'Employer', 'Applicant', 'Recruiter', 'Manager'):
            role, created = Role.objects.get_or_create(name=name)
            self.stdout.write(f'{name} {"created" if created else "already exists"}')
