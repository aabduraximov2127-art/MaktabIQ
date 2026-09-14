from rest_framework.permissions import BasePermission


class IsChatMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        chat_room = obj if obj.__class__.__name__ == "ChatRoom" else obj.chat_room
        return chat_room.members.filter(user=request.user).exists()
