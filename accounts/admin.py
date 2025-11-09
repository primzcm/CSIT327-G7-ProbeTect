from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
        ("Profile", {"fields": ("headline", "bio", "profile_photo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "role")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "headline", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
