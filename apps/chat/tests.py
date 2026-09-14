from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import ChatMember, ChatRoom, Message


class ChatPermissionTests(APITestCase):
    def setUp(self):
        self.student1 = User.objects.create_user(username="s1", password="Str0ngPass!23", role=User.Role.STUDENT)
        self.student2 = User.objects.create_user(username="s2", password="Str0ngPass!23", role=User.Role.STUDENT)
        self.room = ChatRoom.objects.create(room_type=ChatRoom.RoomType.PRIVATE, name="Room 1")
        ChatMember.objects.create(chat_room=self.room, user=self.student1)

    def test_non_member_cannot_list_room_messages(self):
        Message.objects.create(chat_room=self.room, sender=self.student1, text="Salom")
        self.client.force_authenticate(self.student2)
        response = self.client.get(f"/api/v1/chat/messages/?chat_room={self.room.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_non_member_cannot_send_message(self):
        self.client.force_authenticate(self.student2)
        response = self.client.post(
            "/api/v1/chat/messages/", {"chat_room": self.room.id, "text": "Salom"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_send_message(self):
        self.client.force_authenticate(self.student1)
        response = self.client.post(
            "/api/v1/chat/messages/", {"chat_room": self.room.id, "text": "Salom"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
