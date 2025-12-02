from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from quizzes.models import Quiz, QuizAttempt
from quizzes.utils import grade_quiz_submission

from .forms import ClassroomForm, ClassroomJoinForm, LessonAssignForm, QuizAssignmentForm
from .models import Classroom, ClassroomMembership, QuizAssignment
from lessons.models import Lesson


class ClassroomListView(LoginRequiredMixin, View):
    template_name = "classrooms/list.html"

    def get(self, request):
        owned_classes = Classroom.objects.filter(owner=request.user).prefetch_related("memberships")
        enrolled_classes = Classroom.objects.filter(memberships__user=request.user).exclude(owner=request.user).select_related("owner")

        context = {
            "owned_classes": owned_classes,
            "enrolled_classes": enrolled_classes,
            "create_form": ClassroomForm(),
            "join_form": ClassroomJoinForm(),
        }
        return render(request, self.template_name, context)


class ClassroomCreateView(LoginRequiredMixin, View):
    def post(self, request):
        if not getattr(request.user, "is_instructor", lambda: False)():
            messages.error(request, "Only instructors can create classes.")
            return redirect("classrooms:list")

        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.owner = request.user
            classroom.save()
            messages.success(request, f'Class "{classroom.name}" created. Share the code {classroom.code} to invite students.')
            return redirect("classrooms:detail", pk=classroom.pk)

        owned_classes = Classroom.objects.filter(owner=request.user)
        enrolled_classes = Classroom.objects.filter(memberships__user=request.user).exclude(owner=request.user)
        return render(
            request,
            "classrooms/list.html",
            {
                "owned_classes": owned_classes,
                "enrolled_classes": enrolled_classes,
                "create_form": form,
                "join_form": ClassroomJoinForm(),
            },
        )


class ClassroomJoinView(LoginRequiredMixin, View):
    def post(self, request):
        form = ClassroomJoinForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please enter a valid class code.")
            return redirect("classrooms:list")

        code = form.cleaned_data["code"]
        classroom = Classroom.objects.filter(code=code).first()
        if not classroom:
            messages.error(request, "No class found with that code.")
            return redirect("classrooms:list")

        if classroom.owner_id == request.user.id:
            messages.info(request, "You already own this class.")
            return redirect("classrooms:detail", pk=classroom.pk)

        membership, created = ClassroomMembership.objects.get_or_create(
            classroom=classroom,
            user=request.user,
            defaults={"role": ClassroomMembership.Role.STUDENT},
        )
        if created:
            messages.success(request, f"You joined {classroom.name}.")
        else:
            messages.info(request, f"You are already in {classroom.name}.")
        return redirect("classrooms:detail", pk=classroom.pk)


class ClassroomDetailView(LoginRequiredMixin, View):
    template_name = "classrooms/detail.html"

    def get(self, request, pk: int):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not self._has_access(request.user, classroom):
            messages.error(request, "You do not have access to this class.")
            return redirect("classrooms:list")

        memberships = classroom.memberships.select_related("user")
        assignments = classroom.assignments.select_related("quiz", "quiz__material").prefetch_related(
            "attempts__user"
        )
        is_owner = classroom.owner_id == request.user.id
        attempts_by_assignment: dict[int, list[QuizAttempt]] = {}
        user_attempts: dict[int, QuizAttempt | None] = {}
        for assignment in assignments:
            attempts = list(assignment.attempts.all())
            attempts_by_assignment[assignment.id] = attempts
            user_attempts[assignment.id] = next((a for a in attempts if a.user_id == request.user.id), None)
            assignment.attempts_list = attempts  # attach for template convenience
            assignment.user_attempt = user_attempts[assignment.id]
        return render(
            request,
            self.template_name,
            {
                "classroom": classroom,
                "memberships": memberships,
                "assignments": assignments,
                "is_owner": is_owner,
                "attempts_by_assignment": attempts_by_assignment,
                "user_attempts": user_attempts,
            },
        )

    def _has_access(self, user, classroom: Classroom) -> bool:
        if classroom.owner_id == user.id:
            return True
        return ClassroomMembership.objects.filter(classroom=classroom, user=user).exists()


class QuizAssignmentCreateView(LoginRequiredMixin, View):
    template_name = "classrooms/assignment_form.html"

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if not getattr(request.user, "is_instructor", lambda: False)():
            messages.error(request, "Only instructors can assign quizzes.")
            return redirect("classrooms:list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk: int | None = None, quiz_id: int | None = None):
        classroom = self._resolve_classroom(request, pk) if pk else None
        quiz = self._resolve_quiz(request, quiz_id) if quiz_id else None
        form = QuizAssignmentForm(user=request.user, classroom=classroom, quiz=quiz)
        return render(
            request,
            self.template_name,
            {"form": form, "classroom": classroom, "quiz": quiz},
        )

    def post(self, request, pk: int | None = None, quiz_id: int | None = None):
        classroom = self._resolve_classroom(request, pk) if pk else None
        quiz = self._resolve_quiz(request, quiz_id) if quiz_id else None
        form = QuizAssignmentForm(request.POST, user=request.user)

        if form.is_valid():
            assignment: QuizAssignment = form.save(commit=False)
            if assignment.classroom.owner_id != request.user.id:
                messages.error(request, "You can only assign quizzes to your own classes.")
                return redirect("classrooms:list")
            if assignment.quiz.owner_id != request.user.id:
                messages.error(request, "You can only assign quizzes you own.")
                return redirect("classrooms:list")
            if assignment.quiz.status != Quiz.Status.READY:
                messages.error(request, "Only ready quizzes can be assigned.")
                return redirect("classrooms:list")
            assignment.created_by = request.user
            if not assignment.title:
                assignment.title = assignment.quiz.title or "Quiz assignment"
            assignment.save()
            messages.success(request, "Quiz assigned to class.")
            return redirect("classrooms:detail", pk=assignment.classroom_id)

        return render(
            request,
            self.template_name,
            {"form": form, "classroom": classroom, "quiz": quiz},
        )

    def _resolve_classroom(self, request, classroom_id: int | None) -> Classroom | None:
        if classroom_id is None:
            return None
        return get_object_or_404(Classroom, pk=classroom_id, owner=request.user)

    def _resolve_quiz(self, request, quiz_id: int | None) -> Quiz | None:
        if quiz_id is None:
            return None
        return get_object_or_404(Quiz, pk=quiz_id, owner=request.user)


class LessonAssignView(LoginRequiredMixin, View):
    template_name = "classrooms/lesson_assign.html"

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if not getattr(request.user, "is_instructor", lambda: False)():
            messages.error(request, "Only instructors can assign lessons.")
            return redirect("classrooms:list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk: int):
        classroom = get_object_or_404(Classroom, pk=pk, owner=request.user)
        form = LessonAssignForm(user=request.user)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "classroom": classroom,
            },
        )

    def post(self, request, pk: int):
        classroom = get_object_or_404(Classroom, pk=pk, owner=request.user)
        form = LessonAssignForm(request.POST, user=request.user)
        if form.is_valid():
            lesson: Lesson = form.cleaned_data["lesson"]
            lesson.classroom = classroom
            lesson.save(update_fields=["classroom", "updated_at"])
            messages.success(request, f'Lesson "{lesson.title}" assigned to {classroom.name}.')
            return redirect("classrooms:detail", pk=classroom.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "classroom": classroom,
            },
        )


class AssignmentTakeView(LoginRequiredMixin, View):
    template_name = "classrooms/assignment_take.html"

    def get(self, request, pk: int):
        assignment = self._get_assignment(request, pk)
        if not assignment:
            return redirect("classrooms:list")
        quiz = assignment.quiz
        questions = list(quiz.questions.all())
        now = timezone.now()
        entries = [{"question": question, "result": None} for question in questions]
        deadline_seconds = None
        if assignment.due_at:
            remaining = (assignment.due_at - now).total_seconds()
            deadline_seconds = int(remaining) if remaining > 0 else 0

        time_limit_seconds = None
        if quiz.timer_minutes:
            time_limit_seconds = quiz.timer_minutes * 60
        if deadline_seconds is not None:
            time_limit_seconds = (
                min(time_limit_seconds, deadline_seconds) if time_limit_seconds is not None else deadline_seconds
            )

        existing_attempt = None
        if assignment.classroom.owner_id != request.user.id:
            existing_attempt = QuizAttempt.objects.filter(assignment=assignment, user=request.user).first()

        submitted = False
        score = total = percent = None
        attempts_used = 0
        max_attempts = assignment.max_attempts or 1
        if existing_attempt:
            submitted = True
            score = existing_attempt.score
            total = existing_attempt.total_questions
            percent = float(existing_attempt.percent)
            attempts_used = existing_attempt.attempts_used
            for entry in entries:
                qid = str(entry["question"].id)
                stored = existing_attempt.answers.get(qid, {})
                entry["result"] = {
                    "user_answer": stored.get("user_answer", ""),
                    "correct": stored.get("correct", False),
                }

        allow_submit = assignment.quiz.status == Quiz.Status.READY
        if assignment.classroom.owner_id != request.user.id:
            if assignment.due_at and now >= assignment.due_at:
                allow_submit = False
            elif attempts_used >= max_attempts:
                allow_submit = False
        return render(
            request,
            self.template_name,
            {
                "assignment": assignment,
                "quiz": quiz,
                "questions": questions,
                "entries": entries,
                "show_answers": assignment.show_answers or assignment.classroom.owner_id == request.user.id,
                "submitted": submitted,
                "score": score,
                "total": total,
                "percent": percent,
                "attempts_used": attempts_used,
                "max_attempts": max_attempts,
                "allow_submit": allow_submit,
                "deadline_seconds": deadline_seconds,
                "time_limit_seconds": time_limit_seconds,
            },
        )

    def post(self, request, pk: int):
        assignment = self._get_assignment(request, pk)
        if not assignment:
            return redirect("classrooms:list")

        quiz = assignment.quiz
        questions = list(quiz.questions.all())

        existing_attempt = None
        max_attempts = assignment.max_attempts or 1
        attempts_used = 0
        if assignment.classroom.owner_id != request.user.id:
            existing_attempt = QuizAttempt.objects.filter(assignment=assignment, user=request.user).first()
            if existing_attempt:
                attempts_used = existing_attempt.attempts_used
            if attempts_used >= max_attempts:
                # Student has exhausted attempts; show last attempt summary.
                messages.info(request, f"You have used all {max_attempts} attempt(s) for this quiz.")
                if existing_attempt:
                    entries = []
                    for question in questions:
                        qid = str(question.id)
                        stored = existing_attempt.answers.get(qid, {})
                        entries.append(
                            {
                                "question": question,
                                "result": {
                                    "user_answer": stored.get("user_answer", ""),
                                    "correct": stored.get("correct", False),
                                },
                            }
                        )
                    return render(
                        request,
                        self.template_name,
                        {
                            "assignment": assignment,
                            "quiz": quiz,
                            "questions": questions,
                            "entries": entries,
                            "submitted": True,
                            "score": existing_attempt.score,
                            "total": existing_attempt.total_questions,
                            "percent": float(existing_attempt.percent),
                            "show_answers": assignment.show_answers
                            or assignment.classroom.owner_id == request.user.id,
                            "allow_submit": False,
                            "deadline_seconds": None,
                            "time_limit_seconds": None,
                            "attempts_used": attempts_used,
                            "max_attempts": max_attempts,
                        },
                    )

        now = timezone.now()
        if (
            assignment.due_at
            and now >= assignment.due_at
            and assignment.classroom.owner_id != request.user.id
            and not request.POST.get("auto_submit")
        ):
            messages.error(request, "This assignment can no longer be submitted; the deadline has passed.")
            return redirect("classrooms:detail", pk=assignment.classroom_id)

        entries, score, total, percent = grade_quiz_submission(questions, request.POST)

        answers_payload: dict[str, Any] = {}
        for entry in entries:
            answers_payload[str(entry["question"].id)] = {
                "user_answer": entry["result"]["user_answer"],
                "correct": entry["result"]["correct"],
            }

        # Update or create the user's attempt record, tracking how many times they've submitted.
        if existing_attempt:
            attempts_used = existing_attempt.attempts_used
        attempts_used_for_save = attempts_used
        if assignment.classroom.owner_id != request.user.id:
            attempts_used_for_save = attempts_used + 1

        QuizAttempt.objects.update_or_create(
            assignment=assignment,
            user=request.user,
            defaults={
                "quiz": quiz,
                "score": score,
                "total_questions": total,
                "percent": percent,
                "answers": answers_payload,
                "attempts_used": attempts_used_for_save,
            },
        )

        messages.success(request, "Quiz submitted.")
        return render(
            request,
            self.template_name,
            {
                "assignment": assignment,
                "quiz": quiz,
                "questions": questions,
                "entries": entries,
                "submitted": True,
                "score": score,
                "total": total,
                "percent": percent,
                "show_answers": assignment.show_answers or assignment.classroom.owner_id == request.user.id,
                "allow_submit": False,
                "attempts_used": attempts_used_for_save,
                "max_attempts": max_attempts,
                "deadline_seconds": None,
                "time_limit_seconds": None,
            },
        )

    def _get_assignment(self, request, pk: int) -> QuizAssignment | None:
        assignment = get_object_or_404(
            QuizAssignment.objects.select_related("classroom", "quiz", "quiz__material"),
            pk=pk,
        )
        if assignment.quiz.status != Quiz.Status.READY:
            messages.error(request, "This quiz is not ready yet.")
            return None
        if assignment.classroom.owner_id == request.user.id:
            return assignment
        if ClassroomMembership.objects.filter(classroom=assignment.classroom, user=request.user).exists():
            return assignment
        messages.error(request, "You do not have access to this assignment.")
        return None
