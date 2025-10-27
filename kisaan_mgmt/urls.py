from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language  # <-- Add this import

from accounts import views  # views import गरियो
from accounts.views import signup_view, landing_page, about, contact, CustomPasswordResetView  # Import your views
from products import views
from django.views.i18n import set_language  # <-- Add this import

from accounts import views  # views import गरियो
from products.views import vegetables, fruits, grains, category_list_view, krishi_news, farming_tips, tech_updates,weather_view
from accounts.views import signup_view, landing_page, about, contact  # Import your views
# from views import landing_view

urlpatterns = [

    path("__reload__/", include("django_browser_reload.urls")),

    path('', landing_page, name='landing'),   # Main landing page at "/"
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('vegetables/', vegetables, name= 'vegetables'),
    path('ourproducts/', category_list_view, name='products'),
    path('fruits/', fruits, name= 'fruits'),
    path('grains/', grains, name= 'grains'),
    path('krishi-news/', krishi_news, name='krishi_news'),
    path('farming-tips/', farming_tips, name='farming_tips'),
    path('tech-updates/', tech_updates, name='tech_updates'),
    path('weather/', weather_view, name='weather'),

    path('login/', auth_views.LoginView.as_view(template_name='accounts/farmer_login.html'), name='login'),

    # Login paths
    path('farmer/login/', auth_views.LoginView.as_view(template_name='accounts/farmer_login.html'), name='farmer-login'),
    path('customer/login/', auth_views.LoginView.as_view(template_name='accounts/customer_login.html'), name='customer-login'),

    path('switch-to-farmer/', views.switch_to_farmer, name='switch_to_farmer'),
    path('switch-to-customer/', views.switch_to_customer, name='switch_to_customer'),

    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('signup/', signup_view, name='signup'),

    # Password reset paths
    path('password_reset/', CustomPasswordResetView.as_view(
        template_name='accounts/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('payments/', include('payments.urls')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('set_language/', set_language, name='set_language'),  # <-- Add this line at the end
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
