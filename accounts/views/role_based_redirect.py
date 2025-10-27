from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.utils.translation import gettext_lazy as _

# Relative imports (since this file is in accounts/views/)
from ..models import CustomerProfile, FarmerProfile, Profile
from accounts.models import Profile
from accounts.models import FarmerProfile, CustomerProfile
from ..forms import FarmerProfileForm, CustomerProfileForm

# redirects users to their specific dashboards based on their roles after login
@login_required
def role_based_redirect(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        messages.error(request, _("Profile not found. Please log in again."))
        return redirect('login')

    if profile.is_blocked:
        messages.error(request, _("You are blocked by the system."))
        logout(request)
        return redirect('login')

    if profile.role == 'farmer':
        try:
            farmer_profile = request.user.farmerprofile
        except FarmerProfile.DoesNotExist:
            farmer_profile = FarmerProfile.objects.create(user=request.user)

        # Redirect to profile update if required fields are missing mainly for profile picture
        if not farmer_profile.profile_picture:
            return redirect('update-farmer-profile')

        return redirect('farmer-dashboard')

    elif profile.role == 'customer':
        try:
            customer_profile = request.user.customerprofile
        except CustomerProfile.DoesNotExist:
            customer_profile = CustomerProfile.objects.create(user=request.user)

        # Redirect to profile update if required fields are missing like profile picture
        if not customer_profile.profile_picture:
            return redirect('update-customer-profile')

        return redirect('customer-dashboard')

    else:
        messages.error(request, _("illegal access"))
        logout(request)
        return redirect('login')

# login page for famers only 
class FarmerLoginView(LoginView):
    template_name = 'accounts/farmer_login.html'      #use farmer specific login template  
    redirect_authenticated_user = True

#check if the logged in user is a farmer, if not logout and redirect to farmer login page
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and request.user.profile.role == 'farmer':
                return redirect('role-redirect')
            
         # If logged in but not a farmer, log them out and show error

            else:
                logout(request)
                messages.error(request, _("You must be logged in as a farmer to access this page."))
                return redirect('farmer-login')
        return super().dispatch(request, *args, **kwargs)

    # After successfully form submission (login)
    def form_valid(self, form):
        user = form.get_user()
        # Checking the user is actually a farmer or not
        if hasattr(user, 'profile') and user.profile.role == 'farmer':
            if user.profile.is_blocked:
                messages.error(self.request, _("You are blocked by the system."))
                return redirect('farmer-login')
            login(self.request, user)  
            return redirect('role-redirect') 
        else:
            # Not a farmer log out and show error
            logout(self.request)
            messages.error(self.request, _("You are not a farmer. Please use the correct login page."))
            return redirect('farmer-login')


# Custom login page for customers only
class CustomerLoginView(LoginView):
    template_name = 'accounts/customer_login.html'  # Use customer-specific login template
    redirect_authenticated_user = True

    # Check before showing the login page
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # If already logged in as a customer, go to dashboard
            if hasattr(request.user, 'profile') and request.user.profile.role == 'customer':
                return redirect('role-redirect')
            else:
                # If logged in but not a customer, log them out and show error
                logout(request)
                messages.error(request, _("You must be logged in as a customer to access this page."))
                return redirect('customer-login')
        return super().dispatch(request, *args, **kwargs)
    

 # After successful login
    def form_valid(self, form):
        user = form.get_user()
        # Check if the user is actually a customer
        if hasattr(user, 'profile') and user.profile.role == 'customer':
            if user.profile.is_blocked:
                messages.error(self.request, _("You are blocked by the system."))
                return redirect('customer-login')
            login(self.request, user)
            return redirect('role-redirect')
        else:
            # Not a customer – log out and show error
            logout(self.request)
            messages.error(self.request, _("You are not a customer. Please use the correct login page."))
            return redirect('customer-login')


# ------------------- Decorators -------------------

# A decorator to protect views that only farmers should access
def farmer_required(view_func):
    @login_required  # First ensure user is logged in
    def wrapper(request, *args, **kwargs):
        # Check if user has a profile and is a farmer
        if hasattr(request.user, 'profile') and request.user.profile.role == 'farmer':
            if request.user.profile.is_blocked:
                messages.error(request, _("You are blocked by the system."))
                logout(request)
                return redirect('farmer-login')
            return view_func(request, *args, **kwargs)  # Allow access
        else:
            # Show error and redirect to farmer login
            messages.error(request, _("Only farmers can access this page."))
            return redirect('farmer-login')
    return wrapper


# A decorator to protect views that only customers should access
def customer_required(view_func):
    @login_required  # First ensure user is logged in
    def wrapper(request, *args, **kwargs):
        # Check if user has a profile and is a customer
        if hasattr(request.user, 'profile') and request.user.profile.role == 'customer':
            if request.user.profile.is_blocked:
                messages.error(request, _("You are blocked by the system."))
                logout(request)
                return redirect('customer-login')
            return view_func(request, *args, **kwargs)  # Allow access
        else:
            # Show error and redirect to customer login
            messages.error(request, _("Only customers can access this page."))
            return redirect('customer-login')
    return wrapper