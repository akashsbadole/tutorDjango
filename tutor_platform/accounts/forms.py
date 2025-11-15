from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, TutorProfile, UserPreferences


class CustomSignupForm(UserCreationForm):
    """Custom form for user registration"""
    
    email = forms.EmailField(
        label=_('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email')})
    )
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First Name')})
    )
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last Name')})
    )
    user_type = forms.ChoiceField(
        label=_('I am a'),
        choices=User.UserType.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label=_('Phone Number'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone Number (optional)')})
    )
    timezone = forms.CharField(
        label=_('Timezone'),
        initial='UTC',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'phone_number', 'timezone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Username')}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Confirm Password')}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = self.cleaned_data['user_type']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.timezone = self.cleaned_data['timezone']
        
        if commit:
            user.save()
            # Create user preferences
            UserPreferences.objects.create(
                user=user,
                timezone=user.timezone
            )
            
            # Create profile based on user type
            if user.is_student():
                StudentProfile.objects.create(user=user)
            elif user.is_tutor():
                TutorProfile.objects.create(user=user)
        
        return user


class CustomLoginForm(forms.Form):
    """Custom form for user login"""
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email'), 'autofocus': True})
    )
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')})
    )
    remember_me = forms.BooleanField(
        label=_('Remember me'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            self.user_cache = authenticate(
                self.request,
                username=email,
                password=password
            )
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    _('Please enter a correct email and password.'),
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data
    
    def confirm_login_allowed(self, user):
        """Check if user is allowed to login"""
        if not user.is_active:
            raise forms.ValidationError(
                _('This account is inactive.'),
                code='inactive'
            )
    
    def get_user(self):
        return self.user_cache


class StudentProfileForm(forms.ModelForm):
    """Form for student profile"""
    
    class Meta:
        model = StudentProfile
        fields = [
            'educational_status', 'institution', 'grade_level', 
            'major_field', 'learning_goals', 'preferred_learning_style', 'bio'
        ]
        widgets = {
            'educational_status': forms.Select(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Institution')}),
            'grade_level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Grade Level')}),
            'major_field': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Major Field')}),
            'learning_goals': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('What are your learning goals?')}),
            'preferred_learning_style': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Tell us about yourself')}),
        }


class TutorProfileForm(forms.ModelForm):
    """Form for tutor profile"""
    
    class Meta:
        model = TutorProfile
        fields = [
            'professional_title', 'experience_years', 'education', 'bio',
            'hourly_rate_min', 'hourly_rate_max', 'languages', 'teaching_experience'
        ]
        widgets = {
            'professional_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Professional Title')}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Your education background')}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Tell us about your teaching experience')}),
            'hourly_rate_min': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01, 'min': 0}),
            'hourly_rate_max': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01, 'min': 0}),
            'languages': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('English, Spanish, French (comma-separated)')}),
            'teaching_experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Describe your teaching experience')}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        hourly_rate_min = cleaned_data.get('hourly_rate_min')
        hourly_rate_max = cleaned_data.get('hourly_rate_max')
        
        if hourly_rate_min and hourly_rate_max:
            if hourly_rate_min > hourly_rate_max:
                raise forms.ValidationError(_('Minimum hourly rate cannot be greater than maximum hourly rate'))
        
        return cleaned_data


class UserPreferencesForm(forms.ModelForm):
    """Form for user preferences"""
    
    class Meta:
        model = UserPreferences
        fields = [
            'email_notifications', 'sms_notifications', 'push_notifications',
            'marketing_emails', 'language', 'timezone', 'currency'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'marketing_emails': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
        }


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'timezone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProfilePictureForm(forms.ModelForm):
    """Form for updating profile picture"""
    
    class Meta:
        model = User
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }