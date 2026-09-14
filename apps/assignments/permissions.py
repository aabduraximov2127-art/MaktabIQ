from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.permissions import user_role


class CanManageAssignment(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return user_role(request.user) in {"ADMIN", "SUPERADMIN", "TEACHER"}

    def has_object_permission(self, request, view, obj):
        role = user_role(request.user)
        if role in {"ADMIN", "SUPERADMIN"}:
            return True
        if request.method in SAFE_METHODS:
            return True
        return obj.teacher.user_id == request.user.id
