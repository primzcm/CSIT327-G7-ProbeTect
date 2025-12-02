from django.urls import path

from .views import (
    GenerateQuizView,
    QuizDeleteView,
    QuizDetailView,
    QuizExportDOCXView,
    QuizExportPDFView,
    QuizListView,
    QuizScheduleView,
    QuizShareLinkView,
    SharedQuizTakeView,
    GenerateQuizFromListView,
)

app_name = 'quizzes'

urlpatterns = [
    path('shared/<slug:token>/', SharedQuizTakeView.as_view(), name='shared_take'),
    path('<int:pk>/share/', QuizShareLinkView.as_view(), name='share'),
    path('materials/<int:material_id>/generate/', GenerateQuizView.as_view(), name='generate'),
    path('materials/<int:material_id>/', QuizListView.as_view(), name='list_by_material'),
    path('generate/', GenerateQuizFromListView.as_view(), name='generate_from_list'),
    path('schedule/', QuizScheduleView.as_view(), name='schedule'),
    path('<int:pk>/delete/', QuizDeleteView.as_view(), name='delete'),
    path('<int:pk>/', QuizDetailView.as_view(), name='detail'),
    path('<int:pk>/export/pdf/', QuizExportPDFView.as_view(), name='export_pdf'),
    path('<int:pk>/export/docx/', QuizExportDOCXView.as_view(), name='export_docx'),
    path('', QuizListView.as_view(), name='list'),
]
