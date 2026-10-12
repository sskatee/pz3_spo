from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg
from django.shortcuts import render
from datetime import datetime
from django.db.models.functions import TruncMonth
from .models import AcademicGroup, Course, Department, StudentProfile


@login_required
def dashboard_overview(request):
    total_departments = Department.objects.count()
    total_groups = AcademicGroup.objects.count()
    total_courses = Course.objects.count()
    total_students = StudentProfile.objects.count()

    # Курсы по факультетам
    dept_courses = (
        Department.objects
        .annotate(courses_count=Count('courses'))
        .order_by('name')
    )
    pie_labels = [d.name for d in dept_courses]
    pie_values = [d.courses_count for d in dept_courses]


    # Студенты по факультетам
    dept_students = (
        Department.objects
        .annotate(students_count=Count('students'))
        .order_by('name')
    )
    bar_labels = [d.name for d in dept_students]
    bar_values = [d.students_count for d in dept_students]

    context = {
        'total_departments': total_departments,
        'total_groups': total_groups,
        'total_courses': total_courses,
        'total_students': total_students,
        'pie_labels': pie_labels,
        'pie_values': pie_values,
        'bar_labels': bar_labels,
        'bar_values': bar_values,
    }
    return render(request, 'dashboards/overview.html', context)


@login_required
def dashboard_students(request):
    dept_id = request.GET.get('department')

    groups_qs = AcademicGroup.objects.select_related('department')
    students_qs = (
        StudentProfile.objects
        .select_related('user', 'department', 'academic_group')
        .annotate(courses_count=Count('courses'))
        .order_by('user__username')
    )

    if dept_id:
        groups_qs = groups_qs.filter(department_id=dept_id)
        students_qs = students_qs.filter(department_id=dept_id)

    # Студенты по группам
    groups_data = (
        groups_qs
        .annotate(students_count=Count('students'))
        .order_by('name')
    )
    bar_labels = [g.name for g in groups_data]
    bar_values = [g.students_count for g in groups_data]

    departments = Department.objects.all().order_by('name')

    context = {
        'bar_labels': bar_labels,
        'bar_values': bar_values,
        'students': students_qs,
        'departments': departments,
        'selected_department': dept_id,
    }
    return render(request, 'dashboards/students.html', context)


@login_required
def dashboard_courses(request):
    dept_id = request.GET.get('department')

    courses_qs = Course.objects.select_related('department')
    if dept_id:
        courses_qs = courses_qs.filter(department_id=dept_id)

    # Топ-10 курсов
    top_courses = (
        courses_qs
        .annotate(students_count=Count('students'))
        .order_by('-students_count', 'title')[:10]
    )
    bar_labels = [c.title for c in top_courses]
    bar_values = [c.students_count for c in top_courses]


    # Среднее число курсов на студента
    avg_courses = (
        StudentProfile.objects
        .annotate(c=Count('courses'))
        .aggregate(avg=Avg('c'))
    )['avg'] or 0
    # Курсы без студентов
    empty_courses = courses_qs.filter(students__isnull=True).order_by('title')

    # Круговая диаграмма: количество курсов по факультетам
    dept_courses = (
        Department.objects
        .annotate(courses_count=Count('courses'))
        .order_by('name')
    )
    pie_labels = [d.name for d in dept_courses]
    pie_values = [d.courses_count for d in dept_courses]

    departments = Department.objects.all().order_by('name')

    context = {
        'bar_labels': bar_labels,
        'bar_values': bar_values,
        'avg_courses': round(avg_courses, 2),
        'empty_courses': empty_courses,
        'pie_labels': pie_labels,
        'pie_values': pie_values,
        'departments': departments,
        'selected_department': dept_id,
    }
    return render(request, 'dashboards/courses.html', context)

@login_required
def dashboard_departments(request):
    # Общая статистика по каждому факультету
    departments = (
        Department.objects
        .annotate(
            groups_count=Count('groups', distinct=True),
            courses_count=Count('courses', distinct=True),
            students_count=Count('students', distinct=True),
        )
        .order_by('-students_count')
    )

    # Рейтинг факультетов по числу студентов (для прогресс-бара)
    max_students = max([d.students_count for d in departments], default=1) or 1
    ranking = [
        {
            'name': d.name,
            'students': d.students_count,
            'percent': round(d.students_count / max_students * 100, 1),
        }
        for d in departments
    ]

    # Сравнение двух факультетов (выбор через GET)
    dept_a_id = request.GET.get('dept_a')
    dept_b_id = request.GET.get('dept_b')

    compare = None
    if dept_a_id and dept_b_id:
        dept_a = Department.objects.filter(id=dept_a_id).first()
        dept_b = Department.objects.filter(id=dept_b_id).first()
        if dept_a and dept_b:
            def stats(d):
                return {
                    'id': d.id,
                    'name': d.name,
                    'groups': d.groups.count(),
                    'courses': d.courses.count(),
                    'students': d.students.count(),
                }
            compare = {
                'a': stats(dept_a),
                'b': stats(dept_b),
            }

    # Столбчатая: три метрики по каждому факультету
    bar_labels = [d.name for d in departments]
    bar_groups = [d.groups_count for d in departments]
    bar_courses = [d.courses_count for d in departments]
    bar_students = [d.students_count for d in departments]

    context = {
        'departments': departments,
        'ranking': ranking,
        'compare': compare,
        'bar_labels': bar_labels,
        'bar_groups': bar_groups,
        'bar_courses': bar_courses,
        'bar_students': bar_students,
        'all_departments': Department.objects.all().order_by('name'),
        'dept_a_id': dept_a_id,
        'dept_b_id': dept_b_id,
    }
    return render(request, 'dashboards/departments.html', context)


@login_required
def dashboard_activity(request):
    # Динамика регистрации пользователей по месяцам
    users_by_month = (
        User.objects
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    line_labels = [u['month'].strftime('%m.%Y') if u['month'] else '—' for u in users_by_month]
    line_values = [u['count'] for u in users_by_month]

    # Динамика по курсам (по id — чем выше id, тем позже добавлен)
    courses_all = Course.objects.order_by('id')
    course_labels = [f"#{c.id} {c.title[:20]}" for c in courses_all]
    course_values = list(range(1, courses_all.count() + 1))  # кумулятивно

    # Heat-map: сколько студентов в каждой группе по каждому факультету
    # (по сути — загруженность)
    groups = (
        AcademicGroup.objects
        .select_related('department')
        .annotate(students_count=Count('students'))
        .order_by('-students_count')
    )
    max_group = max([g.students_count for g in groups], default=1) or 1
    heatmap = [
        {
            'name': g.name,
            'department': g.department.name,
            'students': g.students_count,
            'percent': round(g.students_count / max_group * 100),
        }
        for g in groups
    ]

    # KPI-метрики
    total_students = StudentProfile.objects.count()
    total_courses = Course.objects.count()
    total_groups = AcademicGroup.objects.count()
    avg_per_group = round(
        total_students / total_groups, 2
    ) if total_groups else 0

    # Распределение студентов по числу курсов (сколько студентов имеют 1, 2, 3... курсов)
    dist_qs = (
        StudentProfile.objects
        .annotate(c=Count('courses'))
        .values('c')
        .annotate(count=Count('id'))
        .order_by('c')
    )
    dist_labels = [f"{d['c']} курс(ов)" for d in dist_qs]
    dist_values = [d['count'] for d in dist_qs]

    context = {
        'line_labels': line_labels,
        'line_values': line_values,
        'course_labels': course_labels[:15],
        'course_values': course_values[:15],
        'heatmap': heatmap,
        'total_students': total_students,
        'total_courses': total_courses,
        'total_groups': total_groups,
        'avg_per_group': avg_per_group,
        'dist_labels': dist_labels,
        'dist_values': dist_values,
    }
    return render(request, 'dashboards/activity.html', context)