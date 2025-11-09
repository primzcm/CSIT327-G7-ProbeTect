from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import (
    EmailAuthenticationForm,
    InstructorSignUpForm,
    StudentSignUpForm,
    UserProfileForm,
)
from .models import User


class AuthenticatedRedirectMixin:
    redirect_url = reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if request.user.is_authenticated:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)


class StudentSignupView(AuthenticatedRedirectMixin, View):
    template_name = "accounts/signup_student.html"
    form_class = StudentSignUpForm

    def get(self, request):
        return render(request, self.template_name, {"form": self.form_class()})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})


class InstructorSignupView(StudentSignupView):
    template_name = "accounts/signup_instructor.html"
    form_class = InstructorSignUpForm


class AuthLoginView(AuthenticatedRedirectMixin, LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm


def auth_logout(request):
    """Log the user out and always redirect to the landing page."""
    logout(request)
    return redirect("landing")


class DashboardView(View):
    template_name = "accounts/dashboard.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        role = request.user.role if isinstance(request.user, User) else User.Role.STUDENT
        context = {"role": role}
        return render(request, self.template_name, context)


class ProfileView(LoginRequiredMixin, View):
    template_name = "accounts/profile.html"
    form_class = UserProfileForm
    login_url = "login"

    def get(self, request, *args, **kwargs):
        form = self.form_class(instance=request.user)
        context = {
            "form": form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        messages.error(request, "Please fix the errors below.")
        return render(request, self.template_name, {"form": form})
