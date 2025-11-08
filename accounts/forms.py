from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

INPUT_CLASSES = "block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"


class BaseSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Last name"}),
            "username": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASSES, "placeholder": "Email"}),
        }

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Last name"}),
    )
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Password"}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Confirm password"}))

    role: str = User.Role.STUDENT

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.role = self.role
        if commit:
            user.save()
        return user


class StudentSignUpForm(BaseSignUpForm):
    role = User.Role.STUDENT


class InstructorSignUpForm(BaseSignUpForm):
    role = User.Role.INSTRUCTOR


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Username or email"}),
        max_length=150,
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Password"}),
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        if username and "@" in username:
            try:
                user = User.objects.get(email__iexact=username)
                self.cleaned_data["username"] = user.username
            except User.DoesNotExist:
                pass
        return super().clean()


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information."""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')
        widgets = {
            'first_name': forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "First name"}),
            'last_name': forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Last name"}),
            'email': forms.EmailInput(attrs={"class": INPUT_CLASSES, "placeholder": "Email"}),
            'username': forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Username"}),
        }