from django.db import models
from django.contrib.auth.models import User


class Module(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    student_code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.student_code} - {self.full_name}"

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ("P", "Present"),
        ("A", "Absent"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ("student", "module", "date")

    def __str__(self):
        return f"{self.student} - {self.module} - {self.date} - {self.get_status_display()}"

class Exam(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    time = models.CharField(max_length=20)  # store as "HH:MM"
    place = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return f"{self.title} on {self.date}"

class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    mark = models.IntegerField(null=True, blank=True)  # 0–100
    # optional: cache status if you want
    # status: "Pending" / "Pass" / "Fail" computed from mark

    class Meta:
        unique_together = ("exam", "student")

    def __str__(self):
        return f"{self.exam} - {self.student} - {self.mark}"
