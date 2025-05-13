from django.urls import path
from . import views

app_name = 'forecast'

urlpatterns = [
    path('products/<int:product_id>/forecast/', views.product_forecast_view, name='product_forecast'),
] 