from django.urls import path, reverse_lazy
from django.contrib.auth.views import LogoutView

from . import views  # views

from .views import (
    signup_view,
    verify_otp_view,
    role_based_redirect,
    farmer_dashboard_view,
    customer_dashboard_view,
    FarmerLoginView,
    CustomerLoginView,
    update_farmer_profile,
    update_customer_profile,
    check_availability,
    farmer_detail,
    farmer_reviews_view, 
    customer_farmer_reviews_view,
    customer_detail_view,      # views
)

urlpatterns = [
    
    # Farmer review submission by customer
    path('farmer/<int:farmer_id>/rate/',views.submit_farmer_review, name='submit-farmer-review'),

    # View farmer reviews & average rating
    # path('farmer/<int:farmer_id>/reviews/', views.view_farmer_reviews, name='view-farmer-reviews'),

    path('signup/', signup_view, name='signup'),
    path('verify-otp/', verify_otp_view, name='verify-otp'),
    path('redirect/', role_based_redirect, name='role-redirect'),

    # Login routes
    path('farmer/login/', FarmerLoginView.as_view(), name='farmer-login'),
    path('customer/login/', CustomerLoginView.as_view(), name='customer-login'),

    # Logout
    path('logout/', LogoutView.as_view(next_page=reverse_lazy('farmer-login')), name='logout'),

    # Dashboards
    path('farmer/dashboard/', farmer_dashboard_view, name='farmer-dashboard'),
    path('customer/dashboard/', customer_dashboard_view, name='customer-dashboard'),

    # Profile updates
    path('farmer/profile/update/', update_farmer_profile, name='update-farmer-profile'),
    path('customer/profile/update/', update_customer_profile, name='update-customer-profile'),  # URL path 
    path('farmer-location/<int:farmer_id>/', views.view_farmer_location, name='view_farmer_location'),
    path('ajax/check-availability/', check_availability, name='check_availability'),
    path('farmer/<int:farmer_id>/', farmer_detail, name='farmer_detail'),
    path('farmer/reviews/', farmer_reviews_view, name='farmer-reviews'),
    path('farmer/<int:farmer_id>/reviews/', customer_farmer_reviews_view, name='customer-farmer-reviews'),
    path('farmer/customer/<int:customer_id>/', customer_detail_view, name='customer-detail'),
    path('delete/customer/', views.delete_customer_account, name='delete_customer_account'),
    path('delete/farmer/', views.delete_farmer_account, name='delete_farmer_account'),
    path('report/user', views.report_user, name='report_user'),



]
