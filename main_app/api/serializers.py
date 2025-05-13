from rest_framework import serializers
from main_app.models import Product
from forecast.models import DemandForecast, ForecastModel


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'stock', 'reorder_level', 'category', 'price']


class DemandForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandForecast
        fields = ['id', 'product', 'date', 'forecast_value', 'lower_bound', 'upper_bound', 'created_at']


class ForecastModelSerializer(serializers.ModelSerializer):
    metrics = serializers.JSONField()
    
    class Meta:
        model = ForecastModel
        fields = ['id', 'product', 'last_trained', 'metrics']


class ForecastResponseSerializer(serializers.Serializer):
    """Serializer for the combined historical and forecast data response"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    dates = serializers.ListField(child=serializers.CharField())
    forecast_values = serializers.ListField(child=serializers.FloatField())
    lower_bounds = serializers.ListField(child=serializers.FloatField())
    upper_bounds = serializers.ListField(child=serializers.FloatField())
    current_stock = serializers.IntegerField()
    reorder_level = serializers.IntegerField()
    historical_dates = serializers.ListField(child=serializers.CharField(), required=False)
    historical_values = serializers.ListField(child=serializers.FloatField(), required=False) 