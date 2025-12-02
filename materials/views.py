from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from .forms import MaterialUploadForm
from .models import Material
from .supabase import SupabaseStorageError, delete_file, download_file, upload_file
from quizzes.models import QuizQuestion


class MaterialUploadView(LoginRequiredMixin, View):
    template_name = "materials/upload.html"
    form_class = MaterialUploadForm

    def get(self, request: HttpRequest) -> HttpResponse:
        form = self.form_class()
        materials = request.user.materials.all()[:10]
        return render(request, self.template_name, {
            "form": form,
            "materials": materials,
            "QuizQuestion": QuizQuestion
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        form = self.form_class(request.POST, request.FILES)
        materials = request.user.materials.all()[:10]
        if form.is_valid():
            pdf_file = form.cleaned_data["pdf"]
            try:
                storage_path, public_url = upload_file(pdf_file, owner_id=request.user.id)
            except SupabaseStorageError as exc:
                form.add_error("pdf", str(exc))
            else:
                material = Material.objects.create(
                    owner=request.user,
                    title=form.cleaned_data.get("title", ""),
                    subject=form.cleaned_data.get("subject", ""),
                    description=form.cleaned_data.get("description", ""),
                    visibility=form.cleaned_data.get("visibility"),
                    storage_path=storage_path,
                    public_url=public_url,
                    content_type=getattr(pdf_file, "content_type", ""),
                    file_size=getattr(pdf_file, "size", None),
                    original_filename=pdf_file.name,
                )
                material.refresh_from_db()  # ensure title fallback applied
                messages.success(request, "PDF uploaded. We will start processing it shortly.")
                return redirect("materials:upload")
        if form.errors:
            messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {
            "form": form,
            "materials": materials,
            "QuizQuestion": QuizQuestion
        })


class MaterialPublicDownloadView(LoginRequiredMixin, View):
    """
    Serve a material file to authorised users, honouring visibility flags.
    - PRIVATE: owner only
    - PUBLIC: any authenticated user
    - CLASS: users who share a classroom with the owner (including owners)
    """

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        material = get_object_or_404(Material, pk=pk)

        # Owner can always access their own files
        if material.owner_id != request.user.id:
            # Check visibility rules for non-owners
            if material.visibility == Material.Visibility.PRIVATE:
                return HttpResponseForbidden("You do not have access to this file.")

            if material.visibility == Material.Visibility.CLASS:
                from classrooms.models import Classroom, ClassroomMembership

                user_classroom_ids = set(
                    list(
                        ClassroomMembership.objects.filter(user=request.user).values_list(
                            "classroom_id", flat=True
                        )
                    )
                    + list(Classroom.objects.filter(owner=request.user).values_list("id", flat=True))
                )
                owner_classroom_ids = set(
                    list(
                        ClassroomMembership.objects.filter(user=material.owner).values_list(
                            "classroom_id", flat=True
                        )
                    )
                    + list(Classroom.objects.filter(owner=material.owner).values_list("id", flat=True))
                )

                if not (user_classroom_ids & owner_classroom_ids):
                    return HttpResponseForbidden("You do not have access to this file.")

        try:
            file_bytes = download_file(material.storage_path)
        except SupabaseStorageError as exc:
            messages.error(request, f"Could not download file: {exc}")
            return redirect("materials:upload")

        response = HttpResponse(
            file_bytes,
            content_type=material.content_type or "application/octet-stream",
        )
        # Let the browser decide whether to display inline or download
        response["Content-Disposition"] = f'inline; filename="{material.original_filename or material.title or "material"}"'
        return response


class MaterialLibraryView(LoginRequiredMixin, View):
    """
    List all of the current user's materials with quick actions.
    This is linked from the dashboard and the upload screen's "Manage library" button.
    """

    template_name = "materials/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        materials = (
            Material.objects.filter(owner=request.user)
            .order_by("-created_at")
        )
        return render(
            request,
            self.template_name,
            {
                "materials": materials,
            },
        )


class MaterialDeleteView(LoginRequiredMixin, View):
    """
    Delete a material and its backing Supabase file.
    Only the owner may delete.
    """

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        material = get_object_or_404(Material, pk=pk, owner=request.user)
        storage_path = material.storage_path

        # Delete DB record first; storage deletion is best-effort.
        material.delete()
        if storage_path:
            try:
                delete_file(storage_path)
            except SupabaseStorageError:
                # Best-effort clean up; don't block UI if storage delete fails.
                pass

        messages.success(request, "Material deleted.")

        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(reverse("materials:library"))
