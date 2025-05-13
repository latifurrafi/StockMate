from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('forecasts', views.DemandForecastViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('products/<int:product_id>/forecast/', views.product_forecast, name='product-forecast'),
    path('products/<int:product_id>/forecast/train/', views.train_forecast_model, name='train-forecast-model'),
    path('products/<int:product_id>/forecast/status/', views.forecast_model_status, name='forecast-model-status'),
] 