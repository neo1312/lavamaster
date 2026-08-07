from django.urls import path

from pos import views

urlpatterns = [
    path('', views.pos_home, name='pos_home'),
    path('orders/', views.orders_list, name='pos_orders_list'),
    path('orders/<int:pk>/', views.pos_order_detail, name='pos_order_detail'),
    path('orders/<int:pk>/ticket/', views.pos_order_ticket, name='pos_order_ticket'),
]
