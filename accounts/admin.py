from django.contrib import admin
from .models import Profile, BlockedProfile, FarmerProfile, CustomerProfile, FarmerReview

# Regular Profile admin (shows all users)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_blocked')
    list_filter = ('role', 'is_blocked')
    search_fields = ('user__username', 'user__email')

# BlockedProfile admin (shows only blocked users)
@admin.register(BlockedProfile)
class BlockedProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_blocked')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_blocked=True)

    # Optional: Prevent editing is_blocked from this view (since it's always True here)
    def has_add_permission(self, request):
        return False  # Can't add from blocked list — must block via main Profile

# Register other models
admin.site.register(FarmerProfile)
admin.site.register(CustomerProfile)
admin.site.register(FarmerReview)