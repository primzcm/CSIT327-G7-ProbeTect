import os
from io import BytesIO

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from django.conf import settings

from .models import User
from materials import supabase
from materials.supabase import SupabaseStorageError

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
        help_text="",
    )
    remove_profile_photo = forms.BooleanField(
        required=False,
        label="Remove current photo",
        help_text="Check to remove your current profile photo.",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "headline", "bio")
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

    def _normalize_photo(self, upload):
        """
        Convert JPEG uploads to PNG to avoid Supabase buckets that disallow image/jpeg.
        Returns a new UploadedFile if conversion occurs; otherwise returns the original.
        """
        if not upload:
            return upload

        content_type = getattr(upload, "content_type", None) or ""
        if content_type.lower() in {"image/jpeg", "image/jpg"}:
            image = Image.open(upload)
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="PNG")
            buffer.seek(0)
            return SimpleUploadedFile(
                name=f"{upload.name.rsplit('.', 1)[0]}.png",
                content=buffer.getvalue(),
                content_type="image/png",
            )
        return upload

    def save(self, commit: bool = True) -> User:
        """
        Save profile fields and, if provided, upload the photo to Supabase storage.
        Old Supabase and local avatar assets are cleaned up after a successful upload.
        """
        user = super().save(commit=False)
        upload = self.cleaned_data.get("profile_photo")
        remove_photo = self.cleaned_data.get("remove_profile_photo")

        previous_storage_path = user.profile_photo_storage_path
        previous_bucket = user.profile_photo_bucket
        previous_local_photo = user.profile_photo if user.profile_photo else None
        removed = False

        if upload:
            upload = self._normalize_photo(upload)
            if not user.pk:
                raise SupabaseStorageError("Cannot upload a profile photo before the user record exists.")

            avatar_bucket = (
                getattr(settings, "SUPABASE_AVATAR_BUCKET", None)
                or os.getenv("SUPABASE_AVATAR_BUCKET")
                or "avatars"
            )
            new_path, public_url = supabase.upload_file(
                upload,
                owner_id=user.pk,
                folder="avatars",
                bucket_override=avatar_bucket,
                content_type_override="image/png",  # we normalize JPEG -> PNG; keep explicit header
            )
            user.profile_photo_storage_path = new_path
            user.profile_photo_public_url = public_url
            user.profile_photo_bucket = avatar_bucket
            user.profile_photo = None
        elif remove_photo:
            removed = True
            user.profile_photo_storage_path = None
            user.profile_photo_public_url = None
            user.profile_photo_bucket = None
            user.profile_photo = None

        if commit:
            user.save()

        if upload:
            if previous_storage_path:
                supabase.delete_file(previous_storage_path, bucket_override=previous_bucket)
            if previous_local_photo:
                previous_local_photo.delete(save=False)
        elif removed:
            if previous_storage_path:
                supabase.delete_file(previous_storage_path, bucket_override=previous_bucket)
            if previous_local_photo:
                previous_local_photo.delete(save=False)

        return user
