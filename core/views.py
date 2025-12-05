from datetime import date, datetime
import calendar
from django.shortcuts import render, redirect
from django.urls import reverse  # we'll need this too
from .constants import MODULE_WEEKLY_SCHEDULE
from .models import Student, Module, AttendanceRecord, Exam, ExamResult, Teacher
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "login.html", {
                "error": "Invalid username or password.",
            })

        login(request, user)

        if hasattr(user, "student"):
            return redirect("student_home")
        elif hasattr(user, "teacher"):
            return redirect("teacher_home")
        else:
            return redirect("student_home")

    return render(request, "login.html")

def logout_view(request):
    logout(request)          # clear the session
    return redirect("login") # send user back to login page


# Student views
@login_required
def student_home(request):
    if not hasattr(request.user, "student"):
        return redirect("login")
    # existing logic:
    today = date.today()
    upcoming_exams = Exam.objects.filter(date__gte=today).order_by("date", "time")[:3]
    return render(request, "student/index.html", {"upcoming_exams": upcoming_exams})


def get_month_weekdays(year, month):
    """
    Return all Monday–Friday dates for the given month/year.
    """
    days = []
    _, last_day = calendar.monthrange(year, month)
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() < 5:  # 0=Mon ... 4=Fri
            days.append(d)
    return days

@login_required
def student_attendance(request):
    # Only students can access
    if not hasattr(request.user, "student"):
        return redirect("login")

    student = request.user.student  # linked via OneToOneField

    today = date.today()

    # Get month/year from query or default to current
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    dates = get_month_weekdays(year, month)

    # Order modules as you like (Math, English, History, Chemistry)
    modules = list(Module.objects.all())
    desired_order = ["Math", "English", "History", "Chemistry"]
    modules.sort(
        key=lambda m: desired_order.index(m.name) if m.name in desired_order else len(desired_order)
    )

    # Attendance records for THIS student, this month
    records = AttendanceRecord.objects.filter(
        student=student,
        date__year=year,
        date__month=month,
    ).select_related("module")

    # Build lookup: (module_id, date) -> status ("P"/"A")
    attendance_map = {}
    for rec in records:
        key = (rec.module_id, rec.date)
        attendance_map[key] = rec.status

    # Build table rows: one per module, cells per date
    table_rows = []
    for module in modules:
        cells = []
        for d in dates:
            status = attendance_map.get((module.id, d))  # None, "P" or "A"
            cells.append({
                "date": d,
                "status": status,
            })
        table_rows.append({
            "module": module,
            "cells": cells,
        })

    context = {
        "student": student,
        "month_name": calendar.month_name[month],
        "year": year,
        "dates": dates,
        "table_rows": table_rows,
        "error": None,
    }
    return render(request, "student/student_attendance.html", context)


@login_required
def student_marks(request):
    # Only students can access this page
    if not hasattr(request.user, "student"):
        return redirect("login")

    student = request.user.student  # The logged-in student
    today = date.today()

    # Fetch past exam results for THIS student only
    results = ExamResult.objects.filter(
        student=student,
        exam__date__lt=today
    ).select_related("exam").order_by("-exam__date")

    rows = []
    for res in results:
        mark = res.mark

        # Determine status based on mark
        if mark is None:
            status = "Pending"
        elif mark >= PASS_MARK:
            status = "Pass"
        else:
            status = "Fail"

        rows.append({
            "exam": res.exam,
            "mark": mark,
            "status": status,
        })

    return render(request, "student/student_marks.html", {
        "rows": rows,
        "error": None,
    })


# Teacher views
@login_required
def teacher_home(request):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    return render(request, "teacher/teacher_dash.html")

@login_required
def teacher_students(request):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    today = date.today()

    # --- 1) Read selected date from GET ---
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # --- 2) Read selected module from GET (default = Math) ---
    selected_module_name = request.GET.get("module", "Math")

    # --- 3) Prevent future dates ---
    if selected_date > today:
        modules = Module.objects.all().order_by("name")
        context = {
            "has_lesson_today": False,
            "today": today,
            "selected_date": selected_date,
            "selected_module_name": selected_module_name,
            "modules": modules,
            "error": "You cannot manage attendance for a future date.",
        }
        return render(request, "teacher/teacher_attendance.html", context)

    # --- 4) Get or create selected module object ---
    selected_module, _ = Module.objects.get_or_create(name=selected_module_name)

    # --- 5) Check if there is a lesson for this module on that weekday ---
    weekday = selected_date.weekday()  # 0..6
    module_schedule = MODULE_WEEKLY_SCHEDULE.get(selected_module_name, {})
    lesson_time = module_schedule.get(weekday)

    modules = Module.objects.all().order_by("name")

    if lesson_time is None:
        # No lesson of that module on this day
        context = {
            "has_lesson_today": False,
            "today": today,
            "selected_date": selected_date,
            "selected_module_name": selected_module_name,
            "modules": modules,
            "error": None,
        }
        return render(request, "teacher/teacher_attendance.html", context)

    # --- 6) There IS a lesson -> get all students ---
    students = Student.objects.all().order_by("student_code")

    # --- 7) Handle Update (POST) ---
    if request.method == "POST":
        for student in students:
            field_name = f"status_{student.id}"
            status = request.POST.get(field_name)  # "P", "A" or None

            if status in ("P", "A"):
                AttendanceRecord.objects.update_or_create(
                    student=student,
                    module=selected_module,
                    date=selected_date,
                    defaults={"status": status},
                )

        # Redirect back to same date + module
        return redirect(
            f"{reverse('teacher_students')}?date={selected_date.isoformat()}&module={selected_module_name}"
        )

    # --- 8) Handle Display (GET) – build rows for that module & date ---
    rows = []
    for student in students:
        record = AttendanceRecord.objects.filter(
            student=student,
            module=selected_module,
            date=selected_date,
        ).first()
        status = record.status if record else None
        rows.append({
            "student": student,
            "status": status,
        })

    context = {
        "has_lesson_today": True,
        "today": today,
        "selected_date": selected_date,
        "selected_module_name": selected_module_name,
        "selected_module": selected_module,
        "lesson_time": lesson_time,
        "rows": rows,
        "modules": modules,
        "error": None,
    }
    return render(request, "teacher/teacher_attendance.html", context)

@login_required
def teacher_exam(request):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    today = date.today()

    upcoming_exams = Exam.objects.filter(
        date__gte=today
    ).order_by("date", "time")

    past_exams = Exam.objects.filter(
        date__lt=today
    ).order_by("-date", "-time")

    return render(request, "teacher/teacher_exam.html", {
        "upcoming_exams": upcoming_exams,
        "past_exams": past_exams,
    })

@login_required
def teacher_exam_create(request):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    if request.method == "POST":
        title = request.POST.get("title")
        date_str = request.POST.get("date")
        time = request.POST.get("time")
        place = request.POST.get("place")

        errors = []
        form_data = {
            "title": title,
            "date": date_str,
            "time": time,
            "place": place,
        }

        # Simple validation
        if not title:
            errors.append("Title is required.")
        if not date_str:
            errors.append("Date is required.")
        if not time:
            errors.append("Time is required.")
        if not place:
            errors.append("Place is required.")

        try:
            exam_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            errors.append("Invalid date format.")
            exam_date = None

        if errors or exam_date is None:
            return render(request, "teacher/create_exam.html", {
                "errors": errors,
                "form": form_data,
            })

        # Create the exam
        Exam.objects.create(
            title=title,
            date=exam_date,
            time=time,   # stored as simple string "HH:MM"
            place=place,
        )

        # Redirect to main exam page (where upcoming exams will be listed)
        return redirect("teacher_exam")

    # GET – show empty form
    return render(request, "teacher/create_exam.html")


@login_required
def teacher_exam_update(request, exam_id):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        title = request.POST.get("title")
        date_str = request.POST.get("date")
        time = request.POST.get("time")
        place = request.POST.get("place")

        errors = []

        if not title:
            errors.append("Title is required.")
        if not date_str:
            errors.append("Date is required.")
        if not time:
            errors.append("Time is required.")
        if not place:
            errors.append("Place is required.")

        try:
            exam_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            errors.append("Invalid date format.")
            exam_date = None

        if errors or exam_date is None:
            # Re-render the form with entered values + errors
            return render(request, "teacher/update_exam.html", {
                "exam": exam,
                "errors": errors,
                "form": {
                    "title": title,
                    "date": date_str,
                    "time": time,
                    "place": place,
                },
            })

        # All good -> update the exam
        exam.title = title
        exam.date = exam_date
        exam.time = time
        exam.place = place
        exam.save()

        return redirect("teacher_exam")

    # GET -> show form with current exam data
    form_data = {
        "title": exam.title,
        "date": exam.date.strftime("%Y-%m-%d"),
        "time": exam.time,
        "place": exam.place,
    }

    return render(request, "teacher/update_exam.html", {
        "exam": exam,
        "form": form_data,
        "errors": [],
    })

@login_required
def teacher_exam_delete(request, exam_id):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == "POST":
        exam.delete()
    return redirect("teacher_exam")

PASS_MARK = 40  # or whatever
@login_required
def teacher_exam_grade_students(request, exam_id):
    if not hasattr(request.user, "teacher"):
        return redirect("login")
    exam = get_object_or_404(Exam, id=exam_id)
    students = Student.objects.all().order_by("student_code")

    if request.method == "POST":
        for student in students:
            field_name = f"mark_{student.id}"
            mark_str = request.POST.get(field_name, "").strip()

            if mark_str == "":
                # no mark entered -> keep as None
                ExamResult.objects.update_or_create(
                    exam=exam,
                    student=student,
                    defaults={"mark": None},
                )
            else:
                try:
                    mark = int(mark_str)
                except ValueError:
                    mark = None

                ExamResult.objects.update_or_create(
                    exam=exam,
                    student=student,
                    defaults={"mark": mark},
                )

        return redirect("teacher_exam")  # back to exam list after saving

    # GET – build rows
    rows = []
    results = {
        (r.student_id): r
        for r in ExamResult.objects.filter(exam=exam)
    }

    for student in students:
        result = results.get(student.id)
        mark = result.mark if result else None

        # derive status for display
        if mark is None:
            status = "Pending"
        elif mark >= PASS_MARK:
            status = "Pass"
        else:
            status = "Fail"

        rows.append({
            "student": student,
            "mark": mark,
            "status": status,
        })

    context = {
        "exam": exam,
        "rows": rows,
    }
    return render(request, "teacher/grade_students.html", context)

