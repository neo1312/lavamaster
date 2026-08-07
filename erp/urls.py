from django.urls import path

from erp import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('erp/receptionists/', views.receptionists, name='erp_receptionists'),
    path('erp/service-types/', views.service_types, name='erp_service_types'),
    path('erp/customers/', views.customers, name='erp_customers'),
]
