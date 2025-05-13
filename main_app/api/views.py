from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from main_app.models import Product
from forecast.models import DemandForecast, ForecastModel
from forecast.services.forecast_service import ForecastService
from .serializers import (
    ProductSerializer,
    DemandForecastSerializer,
    ForecastModelSerializer,
    ForecastResponseSerializer
)


class DemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing demand forecasts
    """
    queryset = DemandForecast.objects.all().order_by('product', 'date')
    serializer_class = DemandForecastSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter forecasts by product_id if provided
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id', None)
        
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        
        # Default to fetching only future forecasts
        return queryset.filter(date__gte=timezone.now().date())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_forecast(request, product_id):
    """
    Get the forecast data for a product
    """
    # Ensure the product exists
    product = get_object_or_404(Product, id=product_id)
    
    # Get forecast days from query params or default to 30
    days = request.query_params.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    # Get forecast data
    forecast_data = ForecastService.get_product_forecast(product_id, days)
    
    # If there was an error, return it
    if 'error' in forecast_data:
        return Response({'error': forecast_data['error']}, status=status.HTTP_400_BAD_REQUEST)
    
    # Serialize and return the data
    serializer = ForecastResponseSerializer(forecast_data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def train_forecast_model(request, product_id):
    """
    Manually trigger training of forecast model for a product
    """
    # Ensure the product exists
    product = get_object_or_404(Product, id=product_id)
    
    # Get forecast days from query params or default to 90
    days = request.data.get('days', 90)
    try:
        days = int(days)
    except ValueError:
        days = 90
    
    try:
        # Train the model
        success, message = ForecastService.train_model(product_id, periods=days)
        
        if success:
            # Get the updated model
            model = ForecastModel.objects.get(product_id=product_id)
            serializer = ForecastModelSerializer(model)
            
            return Response({
                'success': True,
                'message': message,
                'model': serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return Response({
            'success': False,
            'message': f"Error training model: {str(e)}",
            'details': error_details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forecast_model_status(request, product_id):
    """
    Get the status of the forecast model for a product
    """
    # Ensure the product exists
    product = get_object_or_404(Product, id=product_id)
    
    try:
        # Get the model if it exists
        model = ForecastModel.objects.get(product_id=product_id)
        serializer = ForecastModelSerializer(model)
        
        return Response({
            'exists': True,
            'model': serializer.data
        })
    except ForecastModel.DoesNotExist:
        return Response({
            'exists': False,
            'message': 'No forecast model exists for this product'
        }) 