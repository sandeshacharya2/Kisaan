from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from datetime import timedelta
from django.utils.translation import gettext as _
from accounts.views.role_based_redirect import farmer_required, customer_required

from ..models import EmailOTP, Profile, FarmerProfile, CustomerProfile  
from ..forms import SignUpForm, FarmerProfileForm
from products.models import Product
from chat.models import ChatRoom
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from accounts.forms import FarmerReviewForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from accounts.models import FarmerReview

# views.py
from django.contrib.auth.views import PasswordResetView
from accounts.forms import CustomPasswordResetForm

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'

    
@require_GET
def check_availability(request):
    field = request.GET.get('field')
    value = request.GET.get('value', '').strip()

    if not field or not value:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    if field == 'username':
        exists = User.objects.filter(username=value).exists()
    elif field == 'email':
        exists = User.objects.filter(email=value).exists()
    elif field == 'phonenumber':
        # Check both FarmerProfile and CustomerProfile for phone number
        exists = FarmerProfile.objects.filter(phonenumber=value).exists() or \
                 CustomerProfile.objects.filter(phonenumber=value).exists()
    else:
        return JsonResponse({'error': 'Invalid field'}, status=400)

    return JsonResponse({'exists': exists})


def landing_page(request):
    return render(request, 'landingpage/index.html')


def about(request):
    return render(request, 'landingpage/about.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        full_message = f"नाम: {name}\nइमेल: {email}\n\nसन्देश:\n{message}"

        send_mail(
            subject=subject,
            message=full_message,
            from_email='kisaan.helps@gmail.com',
            recipient_list=['kisaan.helps@gmail.com'],
            fail_silently=False,
        )

        messages.success(request, _('Your message has been sent successfully!'))

    return render(request, 'landingpage/contact.html')


def switch_to_farmer(request):
    logout(request)
    return redirect('farmer-login')


def switch_to_customer(request):
    logout(request)
    return redirect('customer-login')


# ✅ Send OTP Email
def send_otp(email, otp):
    subject = _("Your OTP for Kisaan app")
    message = _(f" your OTP {otp}. This OTP is valid for 3 minutes. If you did not request this, please ignore this email.")
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


# ✅ SignUp View (cleaned, kept full version)
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            allowed_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com', 'mail.com', 'zoho.com']
            domain = email.split('@')[-1].lower()

            if domain not in allowed_domains:
                messages.error(request, _("this email domain is not allowed. Please use a common email provider like Gmail, Yahoo, Outlook, etc."))
                return render(request, 'accounts/signup.html', {'form': form})

            signup_data = form.cleaned_data.copy()      #retrieve form data in dictionary
            signup_data.pop('password2', None)

            signup_data['latitude'] = request.POST.get('latitude')      #the first part is the key, the second part is the value in dictionary signup_data
            signup_data['longitude'] = request.POST.get('longitude')    

            request.session['signup_data'] = signup_data

            """signup_data = form.cleaned_data.copy()	Get form data temporarily (this view only)
                request.session['signup_data'] = signup_data	Store data across views (OTP, login, etc.)"""
            # Cleanup expired OTPs
            EmailOTP.cleanup_expired()      #calls the cleanup_expired method from model to delete expired OTPs

            # Delete any existing OTP for this email before creating a new one
            EmailOTP.objects.filter(email=email).delete()

            otp_obj = EmailOTP.objects.create(email=email)      #creates a new OTP object with the email
            otp_obj.generate_otp()     #generate a new OTP through the generate_otp method in model
            send_otp(email, otp_obj.otp)        #sending the otp through send_otp function

            print(f"OTP sent to {email}: {otp_obj.otp}")
            return redirect('verify-otp')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


# ✅ OTP Verification View
def verify_otp_view(request):
    EmailOTP.cleanup_expired()  #delete expired OTPs before processing

    signup_data = request.session.get('signup_data') #retrieves the signup data from session
    if not signup_data:
        return redirect('signup')

    email = signup_data.get('email') #gets the email from signup data
    try:
        otp_obj = EmailOTP.objects.get(email=email)
    except EmailOTP.DoesNotExist:
        return redirect('signup')

    now = timezone.now()        #This gets the current date and time
    expiry_time = otp_obj.created_at + timedelta(minutes=3) # This calculates the expiry time of the OTP
    seconds_left = max(0, (expiry_time - now).total_seconds())
    can_resend = seconds_left == 0

    # Resend OTP
    if request.method == 'POST' and 'resend_otp' in request.POST:   #post method and user clicks resend OTP button
        if not can_resend:
            messages.warning(request, f"wait, to resend otp {int(seconds_left)} is left")
        else:
            otp_obj.generate_otp()
            otp_obj.save()
            send_otp(email, otp_obj.otp)
            messages.success(request, "the new otp has been sent to your email. ")
            seconds_left = 180
            can_resend = False

        return render(request, 'accounts/verify_otp.html', {
            'email': email,
            'seconds_left': int(seconds_left),
            'can_resend': can_resend,
        })

    # Submit OTP
    if request.method == 'POST' and 'otp' in request.POST:
        entered_otp = request.POST.get('otp', '').strip()       #Gets the OTP the user entered from the form data.

        if otp_obj.is_valid() and otp_obj.otp == entered_otp:
            if User.objects.filter(email=email).exists():
                del request.session['signup_data']
                EmailOTP.objects.filter(email=email).delete()
                messages.success(request, "you are already registered. Please log in.")
                return redirect('login')

            user = User.objects.create_user(
                first_name=signup_data.get('first_name', ''),
                last_name=signup_data.get('last_name', ''),
                username=signup_data['username'],
                email=email,
                password=signup_data['password1']
            )

            # ✅ Get or create Profile (role only)
            profile = user.profile
            profile.role = signup_data.get('role')
            profile.save()

            # ✅ Assign profile fields to FarmerProfile or CustomerProfile based on role
            role = signup_data.get('role')

            if role == 'farmer':
                farmer_profile, created = FarmerProfile.objects.get_or_create(user=user)
                farmer_profile.phonenumber = signup_data.get('phonenumber')
                farmer_profile.ward = signup_data.get('ward')
                farmer_profile.tole = signup_data.get('tole')
                farmer_profile.latitude = float(signup_data.get('latitude') or 0)
                farmer_profile.longitude = float(signup_data.get('longitude') or 0)
                farmer_profile.save()

            elif role == 'customer':
                customer_profile, created = CustomerProfile.objects.get_or_create(user=user)
                customer_profile.phonenumber = signup_data.get('phonenumber')
                customer_profile.ward = signup_data.get('ward')
                customer_profile.tole = signup_data.get('tole')
                customer_profile.latitude = float(signup_data.get('latitude') or 0)
                customer_profile.longitude = float(signup_data.get('longitude') or 0)
                customer_profile.save()

            del request.session['signup_data']
            EmailOTP.objects.filter(email=email).delete()
            messages.success(request, "regestration successful. You can now log in.")

            if role == 'farmer':
                return redirect('farmer-login')
            elif role == 'customer':
                return redirect('customer-login')
            return redirect('login')
        else:
            return render(request, 'accounts/verify_otp.html', {
                'email': email,
                'error': 'invalid or expired OTP. Please try again.',
                'seconds_left': int(seconds_left),
                'can_resend': can_resend,
            })

    return render(request, 'accounts/verify_otp.html', {
        'email': email,
        'seconds_left': int(seconds_left),
        'can_resend': can_resend,
    })


from django.db.models import Avg
from accounts.models import FarmerReview

@login_required
@farmer_required
def farmer_dashboard_view(request):
    user = request.user

    # ✅ Correct: Product.farmer expects FarmerProfile
    products = Product.objects.filter(farmer=user.farmerprofile)

    try:
        farmer_profile = user.farmerprofile
    except FarmerProfile.DoesNotExist:
        farmer_profile = None

    # ✅ FIXED: Get Profile (for role), not FarmerProfile
    try:
        accounts_profile = user.profile
    except Profile.DoesNotExist:
        accounts_profile = None

    # ✅ FIXED: ChatRoom.farmer expects FarmerProfile
    pending_chats = ChatRoom.objects.filter(
        farmer=user.farmerprofile,  # ← CHANGED HERE
        farmer_accepted=False,
        farmer_rejected=False
    )

    form = FarmerProfileForm(instance=farmer_profile)

    # ✅ UPDATED: FarmerReview.farmer now expects FarmerProfile → use user.farmerprofile
    avg_rating = FarmerReview.objects.filter(farmer=user.farmerprofile).aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)

    # ✅ UPDATED: Fetch reviews using FarmerProfile
    reviews = FarmerReview.objects.filter(farmer=user.farmerprofile).select_related('customer').order_by('-created_at')

    context = {
        'products': products,
        'form': form,
        'farmerprofile': farmer_profile,
        'accounts_profile': accounts_profile,
        'pending_chats': pending_chats,
        'avg_rating': avg_rating,
        'reviews': reviews,
    }

    return render(request, 'accounts/farmer_dashboard.html', context)

# @login_required
# def customer_dashboard_view(request):
#     products = Product.objects.all().order_by('-date_posted')

#     try:
#         customer_profile = request.user.customerprofile
#     except:
#         customer_profile = None

#     return render(request, 'accounts/customer_dashboard.html', {
#         'products': products,
#         'customer_profile': customer_profile,
#     })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Avg
# from .models import FarmerProfile, CustomerProfile, FarmerReview, User  # Import User explicitly
# from .forms import FarmerReviewForm

# @login_required
# @customer_required
# def submit_farmer_review(request, farmer_id):
#     # Get the FarmerProfile to display info, but review uses User
#     farmer_profile = get_object_or_404(FarmerProfile, id=farmer_id)
#     farmer_user = farmer_profile.user  # Extract the User object
#     
#     # Use User objects for review
#     review, created = FarmerReview.objects.get_or_create(
#         farmer=farmer_user,           # ← Farmer is a User
#         customer=request.user,        # ← Customer is a User (logged-in user)
#         defaults={'rating': 5}
#     )

#     if request.method == 'POST':
#         form = FarmerReviewForm(request.POST, instance=review)
#         if form.is_valid():
#             form.save()
#             return redirect('customer-dashboard')
#     else:
#         form = FarmerReviewForm(instance=review)

#     return render(request, 'accounts/submit_farmer_review.html', {
#         'form': form,
#         'farmer': farmer_user,  # Pass User object for display
#     })


@login_required
def farmer_reviews_view(request):
    """Farmer sees all reviews about themselves"""
    # Ensure user has FarmerProfile (role check)
    try:
        farmer_profile = request.user.farmerprofile  # ← Note: auto-generated name 'farmerprofile'
    except FarmerProfile.DoesNotExist:
        return HttpResponseForbidden("You are not a farmer.")

    # ✅ UPDATED: Filter reviews by FarmerProfile, not User
    reviews = FarmerReview.objects.filter(farmer=farmer_profile).select_related('customer').order_by('-created_at')

    return render(request, 'accounts/farmer_reviews.html', {
        'reviews': reviews,
        'farmer': request.user,
    })


@login_required
def customer_farmer_reviews_view(request, farmer_id):
    """Customer sees reviews of a specific farmer"""
    farmer_profile = get_object_or_404(FarmerProfile, id=farmer_id)
    # farmer_user = farmer_profile.user  # Not needed for query anymore
    
    # ✅ UPDATED: Filter by FarmerProfile
    reviews = FarmerReview.objects.filter(farmer=farmer_profile).select_related('customer').order_by('-created_at')

    return render(request, 'accounts/farmer_reviews_customer.html', {
        'reviews': reviews,
        'farmer': farmer_profile,  # Still pass User for display in template
    })


@login_required
# @farmer_required
def customer_detail_view(request, customer_id):
    customer_profile = get_object_or_404(CustomerProfile, id=customer_id)
    # customer_user = customer_profile.user  # Not needed for query
    
    # ✅ UPDATED: Reviews use FarmerProfile (request.user.farmerprofile) and CustomerProfile
    try:
        farmer_profile = request.user.farmerprofile
    except FarmerProfile.DoesNotExist:
        return HttpResponseForbidden("You are not a farmer.")

    reviews = FarmerReview.objects.filter(
        farmer=farmer_profile,      # ← Farmer is FarmerProfile
        customer=customer_profile   # ← Customer is CustomerProfile
    )

    return render(request, 'accounts/customer_detail.html', {
        'customer': customer_profile,  # Still pass profile for display details
        'reviews': reviews,
    })








@login_required
@customer_required
@login_required
@customer_required
def submit_farmer_review(request, farmer_id):
    farmer_profile = get_object_or_404(FarmerProfile, id=farmer_id)
    customer_profile = request.user.customerprofile

    # ✅ Only fetch existing review (don't create one yet)
    try:
        review = FarmerReview.objects.get(farmer=farmer_profile, customer=customer_profile)
        form = FarmerReviewForm(instance=review)
    except FarmerReview.DoesNotExist:
        review = None
        form = FarmerReviewForm()  # Empty form — no default rating

    if request.method == 'POST':
        form = FarmerReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.farmer = farmer_profile
            review.customer = customer_profile
            review.save()
            return redirect('customer-dashboard')

    return render(request, 'accounts/submit_farmer_review.html', {
        'form': form,
        'farmer': farmer_profile,
    })

# @login_required
# # @farmer_required
# def farmer_reviews_view(request):
#     """Farmer sees all reviews about themselves"""
#     reviews = FarmerReview.objects.filter(farmer=request.user) \
#                                   .select_related('customer') \
#                                   .order_by('-created_at')
#     return render(request, 'accounts/farmer_reviews.html', {
#         'reviews': reviews,
#         'farmer': request.user,
#     })


@login_required
def customer_farmer_reviews_view(request, farmer_id):
    """Customer sees reviews of a specific farmer"""
    # ✅ UPDATED: farmer_id is FarmerProfile.id
    farmer_profile = get_object_or_404(FarmerProfile, id=farmer_id)
    reviews = FarmerReview.objects.filter(farmer=farmer_profile) \
                                  .select_related('customer') \
                                  .order_by('-created_at')
    return render(request, 'accounts/farmer_reviews_customer.html', {
        'reviews': reviews,
        'farmer': farmer_profile,  # Pass User for display
    })


# @login_required
# @farmer_required
# def customer_detail_view(request, customer_id):
#     """Farmer sees customer details along with reviews given to this farmer"""
#     customer = get_object_or_404(User, id=customer_id)
#     
#     # Fetch review(s) this customer gave to the logged-in farmer
#     reviews = FarmerReview.objects.filter(farmer=request.user, customer=customer)

#     return render(request, 'accounts/customer_detail.html', {
#         'customer': customer,
#         'reviews': reviews,
#     })