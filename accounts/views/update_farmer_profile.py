from django.shortcuts import redirect, render
from ..forms import FarmerProfileForm, CustomerProfileForm
from ..models import Profile, FarmerProfile, CustomerProfile
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from accounts.views.role_based_redirect import farmer_required, customer_required
from products.models import Product
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from accounts.views.customer_dashboard_view import haversine
from accounts.models import FarmerReview
from django.db.models import Avg
from django.db import transaction
from accounts.models import DeletedUser
from django.contrib.auth.models import User
from payments.models import Transaction
from django.db import transaction




@farmer_required
@login_required
def update_farmer_profile(request):
    # Get the FarmerProfile (correct)
    farmer_profile = request.user.farmerprofile

    # No need to re-check role — @farmer_required already ensures it

    # Ensure FarmerProfile exists
    farmer_profile, _ = FarmerProfile.objects.get_or_create(user=request.user)

    # ✅ UPDATED: FarmerReview.farmer now expects FarmerProfile
    avg_rating = FarmerReview.objects.filter(farmer=farmer_profile).aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)

    # ✅ UPDATED: Fetch reviews using FarmerProfile
    reviews = FarmerReview.objects.filter(farmer=farmer_profile).select_related('customer').order_by('-created_at')

    if request.method == 'POST':
        form = FarmerProfileForm(request.POST, request.FILES, instance=farmer_profile)
        if form.is_valid():
            form.save()
            # messages.success(request, _("Profile updated successfully!"))
            return redirect('farmer-dashboard')
    else:
        form = FarmerProfileForm(instance=farmer_profile)

    context = {
        'form': form,
        'farmerprofile': farmer_profile,
        'avg_rating': avg_rating,
        'reviews': reviews,
    }
    return render(request, 'accounts/update_farmer_profile.html', context)
@login_required
@customer_required
def update_customer_profile(request):
    user = request.user

    try:
        profile = user.profile
        if profile.role != 'customer':
            return redirect('login')
    except Profile.DoesNotExist:
        return redirect('login')

    # Get or create the CustomerProfile instance
    customer_profile, _ = CustomerProfile.objects.get_or_create(user=user)

    # ❌ This doesn't make sense for a customer — customers don't receive reviews
    # But kept as-is per your instruction (no logic change)
    # avg_rating = FarmerReview.objects.filter(farmer=customer_profile).aggregate(Avg('rating'))['rating__avg'] or 0
    # avg_rating = round(avg_rating, 1)

    # ❌ Similarly, customers don't have reviews as farmers — but kept unchanged
    # reviews = FarmerReview.objects.filter(farmer=customer_profile).select_related('customer').order_by('-created_at')

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer_profile)
        if form.is_valid():
            form.save()
            # messages.success(request, _("Profile updated successfully!"))
            return redirect('customer-dashboard')
    else:
        form = CustomerProfileForm(instance=customer_profile)

    context = {
        'form': form,
        'profile': profile,
        'customer_profile': customer_profile,
        'user': user,
        # 'avg_rating': avg_rating,
        # 'reviews': reviews,
    }
    return render(request, 'accounts/update_customer_profile.html', context)

@login_required
def farmer_detail(request, farmer_id):
    # Use 'user__profile__role' to traverse from FarmerProfile -> User -> Profile -> role
    farmer = get_object_or_404(FarmerProfile, id=farmer_id, user__profile__role="farmer")
    
    # ✅ Product.farmer is ForeignKey to FarmerProfile → filter directly
    products = Product.objects.filter(farmer=farmer)

    # ✅ UPDATED: FarmerReview.farmer is FarmerProfile → filter by farmer (not farmer.user)
    avg_rating = FarmerReview.objects.filter(farmer=farmer).aggregate(Avg("rating"))["rating__avg"] or 0
    avg_rating = round(avg_rating, 1)

    # Get customer location from CustomerProfile
    try:
        customer_profile = request.user.customerprofile
        customer_lat = customer_profile.latitude
        customer_lon = customer_profile.longitude
    except (CustomerProfile.DoesNotExist, AttributeError):
        customer_lat = customer_lon = None

    # Attach data to each product for the template
    for product in products:
        # Attach farmer avg rating
        product.farmer_avg_rating = avg_rating

        # Get farmer location from FarmerProfile (already have it!)
        farmer_lat = farmer.latitude
        farmer_lon = farmer.longitude

        # Calculate and attach distance
        if customer_lat is not None and customer_lon is not None and farmer_lat is not None and farmer_lon is not None:
            dist = haversine(customer_lat, customer_lon, farmer_lat, farmer_lon)
            product.distance = round(dist, 3)
            product.display_distance = f"{round(dist * 1000)} m" if dist < 1 else f"{dist:.2f} km"
        else:
            product.distance = None
            product.display_distance = None

    context = {
        "farmer": farmer,
        "products": products,
        "avg_rating": avg_rating,
    }
    return render(request, "accounts/farmer_detail.html", context)






# user deletion code
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import logout
from django.utils import timezone

# Import your models

from chat.models import ChatRoom, Message
from products.models import Product, ProductSynonym

@farmer_required
@login_required
def delete_farmer_account(request):
    if request.method == "POST":
        user = request.user
        confirmation_email = request.POST.get('confirmation_email', '').strip()
        expected_email = user.email

        # 🔒 Validate email match
        if confirmation_email != expected_email:
            return render(request, 'accounts/delete_farmer_account_confirm.html', {
                'error': 'The email you entered does not match your account email.'
            })

        # ✅ Email matches — proceed with deletion
        email = user.email
        username = user.username
        role = getattr(user, 'profile', None).role if hasattr(user, 'profile') else 'unknown'

        with transaction.atomic():
            # 1. Audit log
            DeletedUser.objects.create(
                email=email,
                username=username,
                role=role,
                reason="User confirmed deletion via email verification"
            )

            # 2. Delete all related data
            Message.objects.filter(sender=user).delete()
            
            if role == 'farmer':
                try:
                    farmer_profile = user.farmerprofile
                    ChatRoom.objects.filter(farmer=farmer_profile).delete()
                except FarmerProfile.DoesNotExist:
                    pass
            elif role == 'customer':
                try:
                    customer_profile = user.customerprofile
                    ChatRoom.objects.filter(customer=customer_profile).delete()
                except CustomerProfile.DoesNotExist:
                    pass

            # ✅ UPDATED: FarmerReview.farmer = FarmerProfile, customer = CustomerProfile
            # So we delete by profile, not user
            try:
                farmer_profile = user.farmerprofile
                FarmerReview.objects.filter(farmer=farmer_profile).delete()
            except FarmerProfile.DoesNotExist:
                pass

            try:
                customer_profile = user.customerprofile
                FarmerReview.objects.filter(customer=customer_profile).delete()
            except CustomerProfile.DoesNotExist:
                pass

            Transaction.objects.filter(user=user).delete()

            if role == 'farmer':
                # ✅ Product.farmer = FarmerProfile → delete via farmer=user.farmerprofile
                ProductSynonym.objects.filter(product__farmer=user.farmerprofile).delete()
                Product.objects.filter(farmer=user.farmerprofile).delete()

            FarmerProfile.objects.filter(user=user).delete()
            CustomerProfile.objects.filter(user=user).delete()
            Profile.objects.filter(user=user).delete()
            # EmailOTP.objects.filter(email=email).delete()  # Clean up OTPs

            # 3. Delete user last
            user.delete()

        logout(request)
        # messages.success(
        #     request,
        #     "Your account and all associated data have been permanently deleted. "
        #     "You may register again with this email in the future."
        # )
        return redirect('landing')  # or your homepage

    # GET request: show confirmation page
    return render(request, 'accounts/delete_farmer_account_confirm.html')







# user deletion code
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import logout
from django.utils import timezone

# Import your models

from chat.models import ChatRoom, Message
from products.models import Product, ProductSynonym

@customer_required

@login_required
def delete_customer_account(request):
    if request.method == "POST":
        user = request.user
        confirmation_email = request.POST.get('confirmation_email', '').strip()
        expected_email = user.email

        # 🔒 Validate email match
        if confirmation_email != expected_email:
            return render(request, 'accounts/delete_customer_account_confirm.html', {
                'error': 'The email you entered does not match your account email.'
            })

        # ✅ Email matches — proceed with deletion
        email = user.email
        username = user.username
        role = getattr(user, 'profile', None).role if hasattr(user, 'profile') else 'unknown'

        with transaction.atomic():
            # 1. Audit log
            DeletedUser.objects.create(
                email=email,
                username=username,
                role=role,
                reason="User confirmed deletion via email verification"
            )

            # 2. Delete all related data
            Message.objects.filter(sender=user).delete()
            
            if role == 'farmer':
                try:
                    farmer_profile = user.farmerprofile
                    ChatRoom.objects.filter(farmer=farmer_profile).delete()
                except FarmerProfile.DoesNotExist:
                    pass
            elif role == 'customer':
                try:
                    customer_profile = user.customerprofile
                    ChatRoom.objects.filter(customer=customer_profile).delete()
                except CustomerProfile.DoesNotExist:
                    pass

            # ✅ UPDATED: Delete reviews using profiles
            try:
                farmer_profile = user.farmerprofile
                FarmerReview.objects.filter(farmer=farmer_profile).delete()
            except FarmerProfile.DoesNotExist:
                pass

            try:
                customer_profile = user.customerprofile
                FarmerReview.objects.filter(customer=customer_profile).delete()
            except CustomerProfile.DoesNotExist:
                pass

            Transaction.objects.filter(user=user).delete()

            if role == 'farmer':
                ProductSynonym.objects.filter(product__farmer=user.farmerprofile).delete()
                Product.objects.filter(farmer=user.farmerprofile).delete()

            FarmerProfile.objects.filter(user=user).delete()
            CustomerProfile.objects.filter(user=user).delete()
            Profile.objects.filter(user=user).delete()
            # EmailOTP.objects.filter(email=email).delete()  # Clean up OTPs

            # 3. Delete user last
            user.delete()

        logout(request)
        # messages.success(
        #     request,
        #     "Your account and all associated data have been permanently deleted. "
        #     "You may register again with this email in the future."
        # )
        return redirect('landing')  # or your homepage

    # GET request: show confirmation page
    return render(request, 'accounts/delete_customer_account_confirm.html')





def report_user(request):
    return render(request, 'accounts/report_user.html')