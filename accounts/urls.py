from django.urls import path

from .views import (
    AuthLoginView,
    DashboardView,
    InstructorSignupView,
    ProfileSearchView,
    ProfileView,
    PublicProfileView,
    StudentSignupView,
    auth_logout,
)

urlpatterns = [
    path("login/", AuthLoginView.as_view(), name="login"),
    path("logout/", auth_logout, name="logout"),
    path("signup/student/", StudentSignupView.as_view(), name="signup_student"),
    path("signup/instructor/", InstructorSignupView.as_view(), name="signup_instructor"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profiles/search/", ProfileSearchView.as_view(), name="profile_search"),
    path("profiles/<str:username>/", PublicProfileView.as_view(), name="public_profile"),
]
