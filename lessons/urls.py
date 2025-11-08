from django.urls import path

from .views import LessonCreateView, LessonDeleteView, LessonEditView, LessonListView

app_name = 'lessons'

urlpatterns = [
    path('', LessonListView.as_view(), name='list'),
    path('create/', LessonCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', LessonEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', LessonDeleteView.as_view(), name='delete'),
]

