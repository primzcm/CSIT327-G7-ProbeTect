from __future__ import annotations

from django.urls import path

from .views import (
    AssignmentTakeView,
    ClassroomCreateView,
    ClassroomDetailView,
    ClassroomJoinView,
    ClassroomListView,
    QuizAssignmentCreateView,
)

app_name = "classrooms"

urlpatterns = [
    path("", ClassroomListView.as_view(), name="list"),
    path("create/", ClassroomCreateView.as_view(), name="create"),
    path("join/", ClassroomJoinView.as_view(), name="join"),
    path("<int:pk>/assign/", QuizAssignmentCreateView.as_view(), name="assign_for_class"),
    path("assign/quiz/<int:quiz_id>/", QuizAssignmentCreateView.as_view(), name="assign_for_quiz"),
    path("<int:pk>/", ClassroomDetailView.as_view(), name="detail"),
    path("assignments/<int:pk>/take/", AssignmentTakeView.as_view(), name="assignment_take"),
]
