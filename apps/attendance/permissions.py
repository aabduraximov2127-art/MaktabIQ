from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.permissions import user_role


class CanManageAttendance(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return user_role(request.user) in {"ADMIN", "SUPERADMIN", "TEACHER"}


class CanSubmitParentReason(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.student.parent_links.filter(parent__user=request.user).exists()
