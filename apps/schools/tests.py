from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import School


class SchoolAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="Str0ngPass!23", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(username="teacher", password="Str0ngPass!23", role=User.Role.TEACHER)

    def test_admin_can_create_school(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/schools/", {"name": "Maktab 1"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_teacher_cannot_create_school(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post("/api/v1/schools/", {"name": "Maktab 2"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anyone_authenticated_can_list_schools(self):
        School.objects.create(name="Maktab 3")
        self.client.force_authenticate(self.teacher)
        response = self.client.get("/api/v1/schools/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
