from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import EmailAuthenticationForm, InstructorSignUpForm, StudentSignUpForm, UserProfileForm
from .models import User
from materials.supabase import SupabaseStorageError


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
        edit_mode = request.GET.get("edit") in {"1", "true", "yes"}
        context = {"form": form, "edit_mode": edit_mode}
        context.update(self._get_related_counts(request))
        return render(request, self.template_name, context)

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Profile updated.")
                return redirect("profile")
            except SupabaseStorageError as exc:
                form.add_error("profile_photo", f"Could not upload profile photo: {exc}")
        context = {"form": form, "edit_mode": True}
        context.update(self._get_related_counts(request))
        return render(request, self.template_name, context)


class PublicProfileView(LoginRequiredMixin, View):
    """View for viewing another user's public profile and their visible materials."""
    template_name = "accounts/public_profile.html"

    def get(self, request, username: str):
        profile_user = get_object_or_404(User, username=username)
        is_own_profile = profile_user.id == request.user.id

        from materials.models import Material
        from classrooms.models import ClassroomMembership

        # Determine which materials to show based on visibility
        if is_own_profile:
            # Show all materials for own profile
            materials = Material.objects.filter(owner=profile_user).order_by("-created_at")
            share_class = False
        else:
            # Check if users share a class (either both are members, or one owns and the other is a member)
            from classrooms.models import Classroom

            # Get classrooms where request.user is a member or owner
            user_classroom_ids = set(
                list(
                    ClassroomMembership.objects.filter(user=request.user).values_list("classroom_id", flat=True)
                )
                + list(Classroom.objects.filter(owner=request.user).values_list("id", flat=True))
            )

            # Get classrooms where profile_user is a member or owner
            profile_classroom_ids = set(
                list(
                    ClassroomMembership.objects.filter(user=profile_user).values_list("classroom_id", flat=True)
                )
                + list(Classroom.objects.filter(owner=profile_user).values_list("id", flat=True))
            )

            share_class = bool(user_classroom_ids & profile_classroom_ids)

            # Show PUBLIC materials always, and CLASS materials if they share a class
            if share_class:
                materials = Material.objects.filter(
                    owner=profile_user,
                    visibility__in=[Material.Visibility.PUBLIC, Material.Visibility.CLASS],
                ).order_by("-created_at")
            else:
                materials = Material.objects.filter(
                    owner=profile_user,
                    visibility=Material.Visibility.PUBLIC,
                ).order_by("-created_at")

        # Get public stats (only count public materials for others)
        if is_own_profile:
            materials_count = Material.objects.filter(owner=profile_user).count()
        else:
            materials_count = materials.count()

        context = {
            "profile_user": profile_user,
            "is_own_profile": is_own_profile,
            "materials": materials[:20],  # Limit to 20 most recent
            "materials_count": materials_count,
            "share_class": share_class if not is_own_profile else False,
        }
        return render(request, self.template_name, context)


class ProfileSearchView(LoginRequiredMixin, View):
    """Search and discover public profiles."""
    template_name = "accounts/profile_search.html"

    def get(self, request):
        from materials.models import Material

        search_query = request.GET.get("q", "").strip()
        users = User.objects.none()

        if search_query:
            # Search by username, first name, last name, or headline
            users = User.objects.filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(headline__icontains=search_query)
            ).exclude(id=request.user.id).order_by("-date_joined")[:50]

            # Annotate with public materials count
            for user in users:
                user.public_materials_count = Material.objects.filter(
                    owner=user, visibility=Material.Visibility.PUBLIC
                ).count()

        context = {
            "search_query": search_query,
            "users": users,
        }
        return render(request, self.template_name, context)
