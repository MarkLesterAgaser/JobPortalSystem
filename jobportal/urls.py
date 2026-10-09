from django.urls import path
from . import views

urlpatterns = [
    path('', views.employer_list, name='home'),
    path('employers/', views.employer_list, name='employer_list'),
    path('employers/add/', views.employer_add, name='employer_add'),
    path('employers/<int:pk>/', views.employer_detail, name='employer_detail'),
    path('employers/<int:pk>/edit/', views.employer_edit, name='employer_edit'),
    path('employers/<int:pk>/toggle/', views.employer_toggle, name='employer_toggle'),
]