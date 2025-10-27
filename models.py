from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from django.db.models.signals import post_save
from django.utils.translation import gettext as _
from django.dispatch import receiver


class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.save()

    def is_valid(self):
        return self.otp and (timezone.now() - self.created_at) <= timedelta(minutes=3)

    def __str__(self):
        return f"{self.email} - {self.otp}"

    @staticmethod
    def cleanup_expired():
        expiry_time = timezone.now() - timedelta(minutes=3)
        EmailOTP.objects.filter(created_at__lt=expiry_time).delete()


class Profile(models.Model):
    ROLE_CHOICES = (
        ('farmer', 'Farmer'),
        ('customer', 'Customer'),
        ('admin', 'Admin')
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='admin')
    is_blocked= models.BooleanField(default=False)
    
    


    def __str__(self):
        return f"{self.user.username} Profile"
class BlockedProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = "Blocked User"
        verbose_name_plural = "Blocked Users"

# Farmer specific profile
class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='farmer_profiles/', blank=True, null=True)
    address = models.CharField(max_length=255, default="Beni Municipality", editable=False)
    phonenumber = models.CharField(max_length=20)
    ward = models.CharField(max_length=100, blank=True, null=True)
    tole = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name or ''} {self.user.last_name or ''}".strip() or self.user.username


# Customer specific profile 
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='customer_profiles/', blank=True, null=True)
    address = models.CharField(max_length=255, default="Beni Municipality", editable=False)
    phonenumber = models.CharField(max_length=20)
    ward = models.CharField(max_length=100, blank=True, null=True)
    tole = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    

    def __str__(self):
        return f"{self.user.first_name or ''} {self.user.last_name or ''}".strip() or self.user.username


# Signal to create or update profiles automatically
@receiver(post_save, sender=User)
def create_or_update_user_profiles(sender, instance, created, **kwargs):
    if created:
        # General Profile 
        Profile.objects.create(user=instance)

        # FarmerProfile or CustomerProfile creation based on role
        if hasattr(instance, 'profile') and instance.profile.role == 'farmer':      #hasattr Safely checks if the Profile exists
            FarmerProfile.objects.create(user=instance)    # Creates a farmer-specific profile linked to that user and user= instance means link the profile to the newly created user
        elif hasattr(instance, 'profile') and instance.profile.role == 'customer':
            CustomerProfile.objects.create(user=instance)

    else:
        # General Profile update
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)

        # FarmerProfile update
        if instance.profile.role == 'farmer':
            try:
                instance.farmerprofile.save()
            except FarmerProfile.DoesNotExist:
                FarmerProfile.objects.create(user=instance)

        # CustomerProfile update/
        elif instance.profile.role == 'customer':
            try:
                instance.customerprofile.save()
            except CustomerProfile.DoesNotExist:
                CustomerProfile.objects.create(user=instance)


class FarmerReview(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)  # 1-5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('farmer', 'customer')  # One review per customer per farmer

    def __str__(self):
        return f"{self.customer.username} → {self.farmer.username}: {self.rating}⭐"
    

class DeletedUser(models.Model):
    email=models.EmailField()
    username=models.CharField(max_length=150)
    role=models.CharField(max_length=50, blank=True)
    deleted_at=models.DateTimeField(default=timezone.now)
    reason=models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Deleted: {self.email} on {self.deleted_at.strftime('%Y-%m-%d')}"
