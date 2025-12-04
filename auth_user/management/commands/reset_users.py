from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from allauth.account.models import EmailAddress

class Command(BaseCommand):
    help = 'Resets all user data but keeps necessary tables.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Deleting all users...')
        # This will cascade delete UserProfile, EmailAddress, SocialAccount, etc.
        count, _ = User.objects.all().delete()
        self.stdout.write(f'Deleted {count} objects related to Users.')
        
        self.stdout.write('Deleting all sessions...')
        Session.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('Successfully reset user data.'))
