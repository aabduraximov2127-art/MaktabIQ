from rest_framework import status
from rest_framework.test import APITestCase

from apps.classes.models import AcademicYear, ClassRoom
from apps.schools.models import School
from apps.users.models import ParentProfile, ParentStudent, StudentProfile, TeacherProfile, User

from .models import Attendance, AttendanceStatus


class AttendancePermissionTests(APITestCase):
    def setUp(self):
        self.school = School.objects.create(name="School #1")
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027", start_date="2026-09-01", end_date="2027-05-31", is_active=True
        )
        self.class_a = ClassRoom.objects.create(
            school=self.school, name="9-A", grade=9, academic_year=self.academic_year
        )

        self.teacher_user = User.objects.create_user(
            username="teacher1", password="Str0ngPass!23", role=User.Role.TEACHER
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, teacher_id="T-0001")

        self.student1_user = User.objects.create_user(
            username="student1", password="Str0ngPass!23", role=User.Role.STUDENT
        )
        self.student1 = StudentProfile.objects.create(
            user=self.student1_user, school=self.school, class_room=self.class_a, student_code="S-0001"
        )
        self.student2_user = User.objects.create_user(
            username="student2", password="Str0ngPass!23", role=User.Role.STUDENT
        )
        self.student2 = StudentProfile.objects.create(
            user=self.student2_user, school=self.school, class_room=self.class_a, student_code="S-0002"
        )

        self.parent_user = User.objects.create_user(
            username="parent1", password="Str0ngPass!23", role=User.Role.PARENT
        )
        self.parent = ParentProfile.objects.create(user=self.parent_user)
        ParentStudent.objects.create(parent=self.parent, student=self.student1)

        self.attendance1 = Attendance.objects.create(
            student=self.student1,
            class_room=self.class_a,
            date="2026-09-15",
            status=AttendanceStatus.ABSENT,
            marked_by=self.teacher,
        )
        self.attendance2 = Attendance.objects.create(
            student=self.student2,
            class_room=self.class_a,
            date="2026-09-15",
            status=AttendanceStatus.PRESENT,
            marked_by=self.teacher,
        )

    def test_parent_cannot_see_other_students_attendance(self):
        self.client.force_authenticate(self.parent_user)
        response = self.client.get("/api/v1/attendance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_ids = [a["student"] for a in response.data["results"]]
        self.assertIn(self.student1.id, student_ids)
        self.assertNotIn(self.student2.id, student_ids)

    def test_parent_can_submit_absence_reason(self):
        self.client.force_authenticate(self.parent_user)
        url = f"/api/v1/attendance/{self.attendance1.id}/submit_reason/"
        response = self.client.patch(url, {"parent_reason": "Farzandim kasal edi."})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.attendance1.refresh_from_db()
        self.assertEqual(self.attendance1.parent_reason, "Farzandim kasal edi.")

    def test_parent_cannot_submit_reason_for_other_student(self):
        self.client.force_authenticate(self.parent_user)
        url = f"/api/v1/attendance/{self.attendance2.id}/submit_reason/"
        response = self.client.patch(url, {"parent_reason": "..."})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_mark_attendance(self):
        self.client.force_authenticate(self.student1_user)
        response = self.client.post(
            "/api/v1/attendance/",
            {"student": self.student2.id, "class_room": self.class_a.id, "date": "2026-09-16", "status": "PRESENT"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
