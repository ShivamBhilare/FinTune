from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fixed_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # NEW FIELD: Tracks if they have finished the questionnaire
    is_onboarded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Keep your existing signals below
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()