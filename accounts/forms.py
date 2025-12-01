from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

INPUT_CLASSES = (
    "block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm "
    "focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 "
    "dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-400"
)


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
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Confirm password"}),
    )

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

    profile_photo = forms.ImageField(
        label="Profile photo",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": (
                    "block w-full cursor-pointer rounded-lg border border-dashed border-slate-300 bg-slate-50 "
                    "px-3 py-2 text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 "
                    "file:bg-indigo-600 file:px-4 file:py-2 file:text-white hover:border-indigo-300 "
                    "dark:border-slate-600 dark:bg-slate-900/40 dark:text-slate-300"
                )
            }
        ),
        help_text="Optional. JPG or PNG, 5 MB max.",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "headline", "bio", "profile_photo")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASSES, "placeholder": "Email"}),
            "username": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "Username"}),
            "headline": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "e.g., Anatomy major"}),
            "bio": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "placeholder": "Tell classmates more about your goals", "rows": 4}
            ),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile photos must be under 5 MB.")
        return photo
