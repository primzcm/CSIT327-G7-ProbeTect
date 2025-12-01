from django.urls import path

from .views import MaterialPublicDownloadView, MaterialUploadView

app_name = "materials"

urlpatterns = [
    path("upload/", MaterialUploadView.as_view(), name="upload"),
    path("<int:pk>/file/", MaterialPublicDownloadView.as_view(), name="public_file"),
]
