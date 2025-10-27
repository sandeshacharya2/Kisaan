from django.db import models
from django.contrib.auth.models import User
from accounts.models import FarmerProfile, CustomerProfile
from products.models import Product
from django.core.exceptions import ValidationError


class ChatRoom(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)  # Optional: for context only
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='farmer_chats')
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='customer_chats')
    farmer_accepted = models.BooleanField(default=False)
    farmer_rejected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ✅ Only one chatroom allowed per farmer-customer pair
        unique_together = ('farmer', 'customer')

    def clean(self):
        super().clean()
        if self.farmer_accepted and self.farmer_rejected:
            raise ValidationError("Farmer cannot both accept and reject the chat.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.farmer_accepted:
            self.farmer_rejected = False
        elif self.farmer_rejected:
            self.farmer_accepted = False
        super().save(*args, **kwargs)

    def __str__(self):
        # ✅ No longer depends on product — works even if product is null
        return f"Chat between {self.customer.user.username} and {self.farmer.user.username}"


class Message(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if not hasattr(self.sender, 'farmerprofile') and not hasattr(self.sender, 'customerprofile'):
            raise ValidationError("Only farmers and customers can send messages.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message by {self.sender.username} in {self.chatroom}"