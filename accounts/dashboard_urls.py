from django.urls import path
from . import dashboard_views as dv

urlpatterns = [
    path('dashboards/overview/', dv.dashboard_overview, name='dashboard_overview'),
    path('dashboards/students/', dv.dashboard_students, name='dashboard_students'),
    path('dashboards/courses/', dv.dashboard_courses, name='dashboard_courses'),
    path('dashboards/departments/', dv.dashboard_departments, name='dashboard_departments'),
    path('dashboards/activity/', dv.dashboard_activity, name='dashboard_activity'),
]