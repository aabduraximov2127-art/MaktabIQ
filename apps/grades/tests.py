from rest_framework import status
from rest_framework.test import APITestCase

from apps.classes.models import AcademicYear, ClassRoom, Quarter
from apps.schools.models import School
from apps.subjects.models import Subject
from apps.users.models import StudentProfile, TeacherProfile, User

from .models import Grade


class GradePermissionTests(APITestCase):
    def setUp(self):
        self.school = School.objects.create(name="School #1")
        self.academic_year = AcademicYear.objects.create(
            name="2026-2027", start_date="2026-09-01", end_date="2027-05-31", is_active=True
        )
        self.quarter1 = Quarter.objects.create(
            academic_year=self.academic_year, number=1, start_date="2026-09-01", end_date="2026-10-30"
        )
        self.class_a = ClassRoom.objects.create(
            school=self.school, name="9-A", grade=9, academic_year=self.academic_year
        )
        self.subject = Subject.objects.create(name="Matematika")

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

        self.grade1 = Grade.objects.create(
            student=self.student1,
            subject=self.subject,
            teacher=self.teacher,
            academic_year=self.academic_year,
            quarter=self.quarter1,
            value=8,
        )

    def test_teacher_can_create_grade(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/v1/grades/",
            {
                "student": self.student2.id,
                "subject": self.subject.id,
                "academic_year": self.academic_year.id,
                "quarter": self.quarter1.id,
                "value": 9,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_see_other_students_grade(self):
        self.client.force_authenticate(self.student2_user)
        response = self.client.get("/api/v1/grades/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_ids = [g["student"] for g in response.data["results"]]
        self.assertNotIn(self.student1.id, student_ids)

    def test_student_cannot_create_grade(self):
        self.client.force_authenticate(self.student1_user)
        response = self.client.post(
            "/api/v1/grades/",
            {
                "student": self.student1.id,
                "subject": self.subject.id,
                "academic_year": self.academic_year.id,
                "quarter": self.quarter1.id,
                "value": 9,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_annual_average_calculation(self):
        Quarter.objects.filter(academic_year=self.academic_year).delete()
        q1 = Quarter.objects.create(
            academic_year=self.academic_year, number=1, start_date="2026-09-01", end_date="2026-10-30"
        )
        q2 = Quarter.objects.create(
            academic_year=self.academic_year, number=2, start_date="2026-11-01", end_date="2026-12-30"
        )
        q3 = Quarter.objects.create(
            academic_year=self.academic_year, number=3, start_date="2027-01-10", end_date="2027-03-15"
        )
        q4 = Quarter.objects.create(
            academic_year=self.academic_year, number=4, start_date="2027-03-20", end_date="2027-05-25"
        )
        Grade.objects.all().delete()
        for quarter, value in [(q1, 8), (q2, 9), (q3, 8), (q4, 10)]:
            Grade.objects.create(
                student=self.student1,
                subject=self.subject,
                teacher=self.teacher,
                academic_year=self.academic_year,
                quarter=quarter,
                value=value,
            )

        self.client.force_authenticate(self.teacher_user)
        response = self.client.get(
            f"/api/v1/grades/annual/?student={self.student1.id}&academic_year={self.academic_year.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertEqual(result["annual_average"], 8.75)
