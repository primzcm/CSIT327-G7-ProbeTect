from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import MaterialUploadForm
from .models import Material
from .supabase import SupabaseStorageError, download_file, upload_file
from quizzes.models import QuizQuestion


class MaterialUploadView(LoginRequiredMixin, View):
    template_name = "materials/upload.html"
    form_class = MaterialUploadForm

    def get(self, request):
        form = self.form_class()
        materials = request.user.materials.all()[:10]
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

    def get(self, request, pk: int):
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

    def post(self, request):
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
