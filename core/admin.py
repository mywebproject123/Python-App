from django.contrib import admin
from .models import Module, Student, AttendanceRecord, Exam, ExamResult, Teacher

admin.site.register(Module)
admin.site.register(Student)
admin.site.register(AttendanceRecord)
admin.site.register(Exam)
admin.site.register(ExamResult)
admin.site.register(Teacher)