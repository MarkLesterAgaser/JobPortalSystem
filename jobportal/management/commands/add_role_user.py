from getpass import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from jobportal.models import Role, UserProfile


class Command(BaseCommand):
    help = 'Create a user with a role. Use add_role_user NAME ROLE.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('role')
        parser.add_argument('--email', default='')

    def handle(self, *args, **options):
        role = Role.objects.filter(name__iexact=options['role']).first()
        if role is None:
            raise CommandError('Role not found. Run setup_roles first.')
        user = User.objects.filter(username=options['username']).first()
        if user is None:
            password = getpass('Password ')
            if len(password) < 8:
                raise CommandError('Use at least 8 characters.')
            if password != getpass('Type it again '):
                raise CommandError('The passwords do not match.')
            user = User.objects.create_user(
                username=options['username'], password=password, email=options['email']
            )
        elif options['email']:
            user.email = options['email']
            user.save()
        profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
        if not created:
            profile.role = role
            profile.save()
        self.stdout.write(f'{user.username} is now {role.name}.')
