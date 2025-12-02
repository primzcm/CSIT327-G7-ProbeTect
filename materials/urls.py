from django.urls import path

from .views import (
    MaterialDeleteView,
    MaterialLibraryView,
    MaterialPublicDownloadView,
    MaterialUploadView,
)

app_name = "materials"

urlpatterns = [
    path("upload/", MaterialUploadView.as_view(), name="upload"),
    path("library/", MaterialLibraryView.as_view(), name="library"),
    path("<int:pk>/file/", MaterialPublicDownloadView.as_view(), name="public_file"),
    path("<int:pk>/delete/", MaterialDeleteView.as_view(), name="delete"),
]
