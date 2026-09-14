from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdminOrTeacher, user_role
from common.realtime import push_message_to_chat

from .models import ChatMember, ChatRoom, Message
from .permissions import IsChatMember
from .serializers import ChatMemberSerializer, ChatRoomSerializer, MessageSerializer


class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        return ChatRoom.objects.filter(members__user=self.request.user).distinct().prefetch_related("members")

    def get_permissions(self):
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsAdminOrTeacher()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        room = serializer.save()
        ChatMember.objects.get_or_create(chat_room=room, user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrTeacher])
    def add_member(self, request, pk=None):
        room = get_object_or_404(ChatRoom, pk=pk)
        user_id = request.data.get("user")
        member, created = ChatMember.objects.get_or_create(chat_room=room, user_id=user_id)
        return Response(ChatMemberSerializer(member).data, status=201 if created else 200)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChatMember]
    filterset_fields = ["chat_room"]

    def get_queryset(self):
        role = user_role(self.request.user)
        if role in {"ADMIN", "SUPERADMIN"}:
            return Message.objects.select_related("sender", "chat_room")
        return Message.objects.filter(chat_room__members__user=self.request.user).select_related(
            "sender", "chat_room"
        )

    def perform_create(self, serializer):
        chat_room = serializer.validated_data["chat_room"]
        self.check_object_permissions(self.request, chat_room)
        message = serializer.save(sender=self.request.user)
        push_message_to_chat(
            chat_room.id,
            {
                "id": message.id,
                "chat_room": chat_room.id,
                "sender": message.sender_id,
                "sender_name": message.sender.get_full_name(),
                "text": message.text,
                "created_at": message.created_at.isoformat(),
            },
        )
