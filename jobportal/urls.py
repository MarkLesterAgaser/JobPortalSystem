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
]