from collections import defaultdict

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.subjects.models import Subject
from apps.users.models import StudentProfile
from common.audit import log_action
from common.permissions import user_role

from .models import Grade
from .permissions import CanManageGrade
from .serializers import GradeSerializer


class GradeViewSet(viewsets.ModelViewSet):
    serializer_class = GradeSerializer
    permission_classes = [CanManageGrade]
    filterset_fields = ["student", "subject", "quarter", "academic_year", "grade_type"]
    search_fields = ["student__user__first_name", "student__user__last_name"]

    def get_queryset(self):
        qs = Grade.objects.select_related("student__user", "subject", "teacher__user", "quarter")
        role = user_role(self.request.user)
        user = self.request.user

        if role in {"ADMIN", "SUPERADMIN"}:
            return qs
        if role == "TEACHER":
            return qs.filter(teacher__user=user)
        if role == "STUDENT":
            return qs.filter(student__user=user)
        if role == "PARENT":
            return qs.filter(student__parent_links__parent__user=user)
        return qs.none()

    def perform_create(self, serializer):
        teacher_profile = getattr(self.request.user, "teacher_profile", None)
        grade = serializer.save(teacher=teacher_profile)
        log_action(
            self.request.user,
            "GRADE_CREATED",
            target=str(grade.student),
            description=f"{grade.subject}: {grade.value}",
            request=self.request,
        )
        from apps.notifications.tasks import notify_new_grade

        notify_new_grade.delay(grade.id)

    def perform_update(self, serializer):
        grade = serializer.save()
        log_action(
            self.request.user,
            "GRADE_CHANGED",
            target=str(grade.student),
            description=f"{grade.subject}: {grade.value}",
            request=self.request,
        )

    @action(detail=False, methods=["get"])
    def annual(self, request):
        student_id = request.query_params.get("student")
        academic_year_id = request.query_params.get("academic_year")
        if not student_id or not academic_year_id:
            return Response(
                {"success": False, "message": "student va academic_year parametrlari kerak", "errors": {}},
                status=400,
            )

        student = get_object_or_404(StudentProfile, pk=student_id)
        grades = self.get_queryset().filter(student=student, academic_year_id=academic_year_id)

        by_subject = defaultdict(lambda: defaultdict(list))
        for grade in grades:
            by_subject[grade.subject_id][grade.quarter.number].append(grade.value)

        results = []
        for subject_id, quarters in by_subject.items():
            subject = Subject.objects.get(pk=subject_id)
            quarter_averages = {
                str(q_num): round(sum(values) / len(values), 2) for q_num, values in quarters.items()
            }
            annual_average = round(sum(quarter_averages.values()) / len(quarter_averages), 2)
            results.append(
                {
                    "subject": subject_id,
                    "subject_name": subject.name,
                    "quarter_averages": quarter_averages,
                    "annual_average": annual_average,
                }
            )

        return Response({"success": True, "results": results})
