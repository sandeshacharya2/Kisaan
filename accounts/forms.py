from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, FarmerProfile, CustomerProfile
from django.utils.translation import gettext_lazy as _
from accounts.models import FarmerReview


# forms.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is not registered.")
        return email
WARD_CHOICES = [
    ('Ward 1 – Ratnechaur', 'वडा १ – रातनेचौर'),
    ('Ward 2 – Jyamrukot', 'वडा २ – ज्यामरुकोट'),
    ('Ward 3 – Bhakimli', 'वडा ३ – भाकिम्ली'),
    ('Ward 4 – Singa', 'वडा ४ – सिङ्गा'),
    ('Ward 5 – Pulachaur', 'वडा ५ – पुलाचौर'),
    ('Ward 6 – Arthunge', 'वडा ६ – अर्थुङ्गे'),
    ('Ward 7 – Beni', 'वडा ७ – बेनी'),
    ('Ward 8 – Beni', 'वडा ८ – बेनी'),
    ('Ward 9 – Ghatan', 'वडा ९ – घतान'),
    ('Ward 10 – Patlekhet', 'वडा १० – पात्लेखेत'),
]


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        error_messages={'required': _('please enter your email address.')}
    )
    phonenumber = forms.CharField(
        required=True,
        max_length=20,
        error_messages={'required': _('please enter your phone number.')}
    )
    ward = forms.ChoiceField(
        choices=WARD_CHOICES,
        required=True,
        error_messages={'required': _('please select your ward.')}
    )
    first_name = forms.CharField(
        required=True,
        max_length=30,
        label=_("First Name"),
        widget=forms.TextInput(attrs={'autofocus': True}),
        error_messages={'required': _('please enter your first name.')}
    )

    last_name = forms.CharField(
        required=True,
        max_length=30,
        label=_("Last Name"),
        error_messages={'required': _('please enter your last name.')}
    )   

    tole = forms.CharField(
        required=True,
        max_length=100,
        label=_("Tole (Neighborhood)"),
        error_messages={'required': _('please enter your tole')}
    )
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        required=True,
        error_messages={'required': _('please select your role.')}
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        error_messages={'required': _('password is required.')}
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput,
        error_messages={'required': _('please confirm your password.')}
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'phonenumber', 'ward', 'tole', 'role', 'password1', 'password2')
        error_messages = {
            'username': {
                'required': _('please enter a username.'),
            },
            'password1': {
                'required': _('please enter a password.')
            },
            'password2': {
                'required': _('please confirm your password.')
            },
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('the email is already in use. Please use a different email.'))
        return email

    def clean_phonenumber(self):
        phonenumber = self.cleaned_data.get('phonenumber')
        if not phonenumber.isdigit():
            raise forms.ValidationError(_('please enter a valid phone number containing only digits.'))
        if len(phonenumber) < 8:
            raise forms.ValidationError(_('the phone number is too short. It should be at least 8 digits.'))

        # ✅ Validate against FarmerProfile and CustomerProfile — NOT Profile
        if FarmerProfile.objects.filter(phonenumber=phonenumber).exists() or \
           CustomerProfile.objects.filter(phonenumber=phonenumber).exists():
            raise forms.ValidationError(_('the phone number is already in use. Please use a different phone number.'))

        return phonenumber

    # ✅ DO NOT OVERRIDE save() — let signup_view handle saving based on role + geolocation


class FarmerProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FarmerProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FarmerProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CustomerProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CustomerProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CustomerProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class FarmerReviewForm(forms.ModelForm):
    class Meta:
        model = FarmerReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Write your review...'),
                'class': 'form-control'
            }),
        }