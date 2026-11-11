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
    path('jobs/', views.jobpost_list, name='jobpost_list'),
    path('jobs/add/', views.jobpost_add, name='jobpost_add'),
    path('jobs/<int:pk>/edit/', views.jobpost_edit, name='jobpost_edit'),
    path('jobs/<int:pk>/delete/', views.jobpost_delete, name='jobpost_delete'),
    path('jobs/<int:pk>/requirements/', views.jobpost_requirements, name='jobpost_requirements'),
    path('requirements/<int:pk>/delete/', views.requirement_delete, name='requirement_delete'),
    path('jobs/<int:pk>/publish/', views.jobpost_set_status, {'action': 'publish'}, name='jobpost_publish'),
    path('jobs/<int:pk>/close/', views.jobpost_set_status, {'action': 'close'}, name='jobpost_close'),
    path('jobs/<int:pk>/fill/', views.jobpost_set_status, {'action': 'fill'}, name='jobpost_fill'),
    path('browse/', views.job_search, name='job_search'),
    path('jobs/<int:pk>/', views.jobpost_detail, name='jobpost_detail'),
]