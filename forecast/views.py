from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from main_app.models import Product, StockTransaction
from forecast.models import ForecastModel, DemandForecast


@login_required
def product_forecast_view(request, product_id):
    """View for displaying product demand forecasts"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if we have a forecast model for this product
    has_model = ForecastModel.objects.filter(product=product).exists()
    
    # Get forecasts
    forecasts = DemandForecast.objects.filter(
        product=product,
        date__gte=timezone.now().date()
    ).order_by('date')[:30]  # Next 30 days by default
    
    # Get recent stock transactions
    transactions = StockTransaction.objects.filter(
        product=product
    ).order_by('-date')[:20]
    
    context = {
        'product': product,
        'has_model': has_model,
        'has_forecast_data': forecasts.exists(),
        'forecasts': forecasts,
        'transactions': transactions,
    }
    
    return render(request, 'product_forecast.html', context)
