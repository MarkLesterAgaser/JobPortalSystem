from django.urls import path
from . import views

urlpatterns = [
    path('', views.employer_list, name='home'),
    path('employers/', views.employer_list, name='employer_list'),
    path('employers/add/', views.employer_add, name='employer_add'),
    path('employers/<int:pk>/', views.employer_detail, name='employer_detail'),
    path('employers/<int:pk>/edit/', views.employer_edit, name='employer_edit'),
    path('employers/<int:pk>/toggle/', views.employer_toggle, name='employer_toggle'),
    path('employers/<int:pk>/profile/', views.employer_profile, name='employer_profile'),
    path('employers/<int:pk>/jobs/', views.employer_job_history, name='employer_job_history'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/toggle/', views.category_toggle, name='category_toggle'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/add/', views.enrollment_add, name='enrollment_add'),
    path('enrollments/<int:pk>/edit/', views.enrollment_edit, name='enrollment_edit'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
    path('employers/<int:pk>/course/', views.employer_set_course, name='employer_set_course'),
]