from django.contrib import admin
from django.urls import path
from core import views
from django.shortcuts import redirect

def redirect_to_login(request):
    return redirect("login")


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", redirect_to_login),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Student pages
    path('student/home/', views.student_home, name='student_home'),
    path('student/attendance/', views.student_attendance, name='student_attendance'),
    path('student/marks/', views.student_marks, name='student_marks'),

    # Teacher pages
    path('teacher/home/', views.teacher_home, name='teacher_home'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    # exam releated
    path('teacher/exam/', views.teacher_exam, name='teacher_exam'),
    path('teacher/exam/create/', views.teacher_exam_create, name='teacher_exam_create'),
    path('teacher/exam/update/<int:exam_id>/', views.teacher_exam_update, name='teacher_exam_update'),    
    path('teacher/exam/grade/<int:exam_id>/', views.teacher_exam_grade_students, name='teacher_exam_grade_students'),
    path(
    'teacher/exam/delete/<int:exam_id>/',
    views.teacher_exam_delete,
    name='teacher_exam_delete'
),

]
