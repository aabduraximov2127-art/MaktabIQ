from rest_framework import permissions, viewsets

from common.permissions import IsAdmin, user_role

from .models import Lesson
from .serializers import LessonSerializer


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    filterset_fields = ["class_room", "subject", "teacher", "date"]

    def get_queryset(self):
        qs = Lesson.objects.select_related("class_room", "subject", "teacher__user")
        role = user_role(self.request.user)
        user = self.request.user

        if role in {"ADMIN", "SUPERADMIN"}:
            return qs
        if role == "TEACHER":
            return qs.filter(teacher__user=user)
        if role == "STUDENT":
            return qs.filter(class_room__students__user=user)
        if role == "PARENT":
            return qs.filter(class_room__students__parent_links__parent__user=user)
        return qs.none()

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]
