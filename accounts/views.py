from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import EmailAuthenticationForm, InstructorSignUpForm, StudentSignUpForm, UserProfileForm
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
        
        from materials.models import Material
        from quizzes.models import Quiz
        from lessons.models import Lesson
        
        # Get active tab from query parameter
        active_tab = request.GET.get('tab', 'files')
        
        # Get user's materials, quizzes, and lessons
        materials = Material.objects.filter(owner=request.user).order_by('-created_at')[:10]
        quizzes = Quiz.objects.filter(owner=request.user).select_related('material').order_by('-created_at')[:10]
        lessons = Lesson.objects.filter(owner=request.user).select_related('material').order_by('-created_at')[:10]
        
        # Counts for tabs
        materials_count = Material.objects.filter(owner=request.user).count()
        quizzes_count = Quiz.objects.filter(owner=request.user).count()
        lessons_count = Lesson.objects.filter(owner=request.user).count()
        
        # Lessons no longer have a scheduled date; show most recent as "upcoming"
        upcoming_lessons = Lesson.objects.filter(owner=request.user).order_by('-created_at')[:5]
        
        # Get role as string value - request.user.role is already a string from CharField
        # It should be "instructor" or "student"
        role = getattr(request.user, 'role', 'student')
        
        context = {
            "role": role,
            "materials": materials,
            "quizzes": quizzes,
            "lessons": lessons,
            "materials_count": materials_count,
            "quizzes_count": quizzes_count,
            "lessons_count": lessons_count,
            "active_tab": active_tab,
            "upcoming_lessons": upcoming_lessons,
        }
        return render(request, self.template_name, context)


class ProfileView(LoginRequiredMixin, View):
    """View for viewing and updating user profile."""
    template_name = "accounts/profile.html"

    def _get_related_counts(self, request):
        from materials.models import Material
        from quizzes.models import Quiz
        from lessons.models import Lesson

        return {
            "materials_count": Material.objects.filter(owner=request.user).count(),
            "quizzes_count": Quiz.objects.filter(owner=request.user).count(),
            "lessons_count": Lesson.objects.filter(owner=request.user).count(),
        }

    def get(self, request):
        form = UserProfileForm(instance=request.user)
        context = {"form": form}
        context.update(self._get_related_counts(request))
        return render(request, self.template_name, context)

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        context = {"form": form}
        context.update(self._get_related_counts(request))
        return render(request, self.template_name, context)
