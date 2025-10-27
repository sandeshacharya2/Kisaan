from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from accounts.models import Profile  # Explicit import for clarity


class EmailBackend(ModelBackend):
    """
    Authenticate using email (case-insensitive) and password.
    Optional role check included for role-based login (e.g., farmer/customer).
    """
    def authenticate(self, request, username=None, password=None, role=None, **kwargs):
        if not username or not password:
            return None

        try:
            # Case-insensitive email lookup
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            return None

        # Optional: Enforce case-sensitive email (uncomment if needed)
        # if user.email != username:
        #     return None

        # Optional role check
        if role:
            try:
                profile = user.profile
                if profile.role != role:
                    return None
            except Profile.DoesNotExist:
                return None  # User has no profile → deny access if role is required

        # Verify password
        if user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None