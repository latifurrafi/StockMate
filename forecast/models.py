from django.db import models
from main_app.models import Product

class ForecastModel(models.Model):
    """Model to store trained Prophet models for products"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='forecast_app_model')
    model_file = models.FileField(upload_to='forecast_models/')
    last_trained = models.DateTimeField(auto_now=True)
    metrics = models.JSONField(default=dict, help_text="Model performance metrics")
    
    def __str__(self):
        return f"Forecast Model for {self.product.name} (Last trained: {self.last_trained})"


class DemandForecast(models.Model):
    """Model to store forecasted demand for products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecast_app_forecasts')
    date = models.DateField()
    forecast_value = models.FloatField(help_text="Forecasted demand quantity")
    lower_bound = models.FloatField(help_text="Lower bound of forecast (95% confidence interval)")
    upper_bound = models.FloatField(help_text="Upper bound of forecast (95% confidence interval)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'date')
        ordering = ['product', 'date']
    
    def __str__(self):
        return f"{self.product.name} - {self.date} - Forecast: {self.forecast_value:.2f}"
