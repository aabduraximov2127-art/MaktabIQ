from rest_framework import permissions, viewsets

from common.permissions import IsAdmin, user_role

from .models import AcademicYear, ClassRoom, Quarter
from .serializers import AcademicYearSerializer, ClassRoomSerializer, QuarterSerializer


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    filterset_fields = ["is_active"]

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class QuarterViewSet(viewsets.ModelViewSet):
    queryset = Quarter.objects.select_related("academic_year")
    serializer_class = QuarterSerializer
    filterset_fields = ["academic_year", "number"]

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class ClassRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassRoomSerializer
    search_fields = ["name"]
    filterset_fields = ["school", "grade", "academic_year", "curator"]

    def get_queryset(self):
        qs = ClassRoom.objects.select_related("school", "academic_year", "curator__user")
        role = user_role(self.request.user)
        user = self.request.user

        if role in {"ADMIN", "SUPERADMIN"}:
            return qs
        if role == "TEACHER":
            return (qs.filter(curator__user=user) | qs.filter(lessons__teacher__user=user)).distinct()
        if role == "STUDENT":
            return qs.filter(students__user=user).distinct()
        if role == "PARENT":
            return qs.filter(students__parent_links__parent__user=user).distinct()
        return qs.none()

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]
