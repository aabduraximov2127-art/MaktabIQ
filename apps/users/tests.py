from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.classes.models import AcademicYear, ClassRoom
from apps.schools.models import School

from .models import ParentProfile, ParentStudent, StudentProfile, TeacherProfile, User


class StudentAccessPermissionTests(APITestCase):
    def setUp(self):
        self.school = School.objects.create(name="School #1")
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027", start_date="2026-09-01", end_date="2027-05-31", is_active=True
        )
        self.class_a = ClassRoom.objects.create(
            school=self.school, name="9-A", grade=9, academic_year=self.academic_year
        )
        self.class_b = ClassRoom.objects.create(
            school=self.school, name="9-B", grade=9, academic_year=self.academic_year
        )

        self.student_user = User.objects.create_user(
            username="student1", password="Str0ngPass!23", role=User.Role.STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user, school=self.school, class_room=self.class_a, student_code="S-0001"
        )

        self.other_student_user = User.objects.create_user(
            username="student2", password="Str0ngPass!23", role=User.Role.STUDENT
        )
        self.other_student_profile = StudentProfile.objects.create(
            user=self.other_student_user, school=self.school, class_room=self.class_a, student_code="S-0002"
        )

        self.admin_user = User.objects.create_user(
            username="admin1", password="Str0ngPass!23", role=User.Role.ADMIN, is_staff=True
        )

        self.parent_user = User.objects.create_user(
            username="parent1", password="Str0ngPass!23", role=User.Role.PARENT
        )
        self.parent_profile = ParentProfile.objects.create(user=self.parent_user)
        ParentStudent.objects.create(parent=self.parent_profile, student=self.student_profile)

    def test_student_cannot_view_other_student_profile(self):
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-detail", args=[self.other_student_profile.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_view_own_profile(self):
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_transfer_self(self):
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-transfer", args=[self.student_profile.id])
        response = self.client.post(url, {"new_class": self.class_b.id, "reason": "test"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_transfer_student(self):
        self.client.force_authenticate(self.admin_user)
        url = reverse("students:student-transfer", args=[self.student_profile.id])
        response = self.client.post(url, {"new_class": self.class_b.id, "reason": "admin decision"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.class_room_id, self.class_b.id)

    def test_parent_can_view_own_child_but_not_others(self):
        self.client.force_authenticate(self.parent_user)

        url_own = reverse("students:student-detail", args=[self.student_profile.id])
        response_own = self.client.get(url_own)
        self.assertEqual(response_own.status_code, status.HTTP_200_OK)

        url_other = reverse("students:student-detail", args=[self.other_student_profile.id])
        response_other = self.client.get(url_other)
        self.assertEqual(response_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_passport_hidden_from_student(self):
        self.student_profile.passport_number = "AB1234567"
        self.student_profile.save(update_fields=["passport_number"])
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.get(url)
        self.assertNotIn("passport_number", response.data)

    def test_parent_can_edit_own_child_profile(self):
        self.client.force_authenticate(self.parent_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.patch(url, {"phone": "+998900000011", "age": 16})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.student_profile.user.refresh_from_db()
        self.assertEqual(self.student_profile.user.phone, "+998900000011")
        self.assertEqual(self.student_profile.age, 16)

    def test_parent_cannot_edit_other_students_profile(self):
        self.client.force_authenticate(self.parent_user)
        url = reverse("students:student-detail", args=[self.other_student_profile.id])
        response = self.client.patch(url, {"phone": "+998900000099"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_parent_cannot_delete_student(self):
        self.client.force_authenticate(self.parent_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_parent_cannot_change_class_room_via_update(self):
        self.client.force_authenticate(self.parent_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.patch(url, {"class_room": self.class_b.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.class_room_id, self.class_a.id)

    def test_student_cannot_edit_own_profile(self):
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.patch(url, {"phone": "+998900000022"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_delete_own_profile(self):
        self.client.force_authenticate(self.student_user)
        url = reverse("students:student-detail", args=[self.student_profile.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_endpoint_has_no_update_method(self):
        # /me/ only exposes GET — there is no way for a student to PATCH their own
        # role/school/is_active through it.
        self.client.force_authenticate(self.student_user)
        response = self.client.patch(reverse("users:me"), {"role": "ADMIN"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TeacherViewSetStudentScopingTests(APITestCase):
    """Point 9 of the student permission spec: a student may only see teachers
    actually teaching their own class (subject teachers or curator)."""

    def setUp(self):
        self.school = School.objects.create(name="School #1")
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027", start_date="2026-09-01", end_date="2027-05-31", is_active=True
        )
        self.class_a = ClassRoom.objects.create(
            school=self.school, name="9-A", grade=9, academic_year=self.academic_year
        )
        self.class_b = ClassRoom.objects.create(
            school=self.school, name="9-B", grade=9, academic_year=self.academic_year
        )

        self.own_teacher_user = User.objects.create_user(
            username="teacher_own", password="Str0ngPass!23", role=User.Role.TEACHER
        )
        self.own_teacher = TeacherProfile.objects.create(user=self.own_teacher_user, teacher_id="T-0001")
        self.class_a.curator = self.own_teacher
        self.class_a.save(update_fields=["curator"])

        self.other_teacher_user = User.objects.create_user(
            username="teacher_other", password="Str0ngPass!23", role=User.Role.TEACHER
        )
        self.other_teacher = TeacherProfile.objects.create(user=self.other_teacher_user, teacher_id="T-0002")
        self.class_b.curator = self.other_teacher
        self.class_b.save(update_fields=["curator"])

        self.student_user = User.objects.create_user(
            username="student1", password="Str0ngPass!23", role=User.Role.STUDENT
        )
        StudentProfile.objects.create(
            user=self.student_user, school=self.school, class_room=self.class_a, student_code="S-0001"
        )

    def test_student_sees_only_own_class_teachers(self):
        self.client.force_authenticate(self.student_user)
        response = self.client.get("/api/v1/teachers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher_ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.own_teacher.id, teacher_ids)
        self.assertNotIn(self.other_teacher.id, teacher_ids)

    def test_admin_still_sees_all_teachers(self):
        admin = User.objects.create_user(username="admin1", password="Str0ngPass!23", role=User.Role.ADMIN)
        self.client.force_authenticate(admin)
        response = self.client.get("/api/v1/teachers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher_ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.own_teacher.id, teacher_ids)
        self.assertIn(self.other_teacher.id, teacher_ids)
