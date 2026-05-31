from django.urls import path
from . import views

app_name = "webhooks"

urlpatterns = [
    path("shopify/order-paid/", views.order_paid, name="shopify_order_paid"),
]
