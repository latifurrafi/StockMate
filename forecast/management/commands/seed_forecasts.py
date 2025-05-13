import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
import os
import joblib
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json

from main_app.models import Product
from forecast.models import ForecastModel, DemandForecast

class Command(BaseCommand):
    help = 'Seed forecast models and data for all products'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Number of forecast days to generate')
        parser.add_argument('--reset', action='store_true', help='Reset existing forecast data')

    def handle(self, *args, **options):
        days = options['days']
        reset = options['reset']
        
        # Get all products
        products = Product.objects.all()
        
        if not products:
            self.stdout.write(self.style.WARNING('No products found in the database.'))
            return
        
        # If reset, delete all existing forecast models and data
        if reset:
            self.stdout.write('Resetting all forecast data...')
            ForecastModel.objects.all().delete()
            DemandForecast.objects.all().delete()
        
        # Create temporary directory for model files if it doesn't exist
        os.makedirs('media/forecast_models', exist_ok=True)
        
        # Process each product
        for product in products:
            self.stdout.write(f"Creating forecast for: {product.name}")
            
            # Check if model already exists
            if ForecastModel.objects.filter(product=product).exists() and not reset:
                self.stdout.write(self.style.WARNING(f"- Forecast model already exists for {product.name}, skipping..."))
                continue
            
            # Generate dummy forecast model
            model = self._create_dummy_model()
            
            # Save model to temporary file
            model_path = f'media/forecast_models/temp_model_{product.id}.json'
            with open(model_path, 'w') as f:
                f.write(model_to_json(model))
            
            # Create forecast model record
            forecast_model, created = ForecastModel.objects.get_or_create(
                product=product,
                defaults={
                    'metrics': {
                        'mse': round(np.random.uniform(0.5, 10), 2),
                        'mae': round(np.random.uniform(0.5, 5), 2),
                        'rmse': round(np.random.uniform(1, 7), 2)
                    }
                }
            )
            
            # Read the file and save it to the model instance
            with open(model_path, 'rb') as f:
                file_content = f.read()
                model_filename = f'prophet_model_{product.id}_{datetime.now().strftime("%Y%m%d")}.json'
                forecast_model.model_file.save(model_filename, ContentFile(file_content))
            
            # Clean up temporary file
            if os.path.exists(model_path):
                os.remove(model_path)
            
            # Generate dummy forecasts
            self._create_dummy_forecasts(product, days)
            
            self.stdout.write(self.style.SUCCESS(f"- Successfully created forecast for {product.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"Completed! Created forecasts for {products.count()} products."))
    
    def _create_dummy_model(self):
        """Create a dummy Prophet model for demo purposes"""
        # Create a simple Prophet model
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True
        )
        
        # Create a simple training dataset
        current_date = datetime.now().date()
        dates = [current_date - timedelta(days=i) for i in range(90, 0, -1)]
        
        # Generate random values with some patterns
        values = []
        for i in range(len(dates)):
            # Add day of week effect (higher on weekends)
            day_of_week = dates[i].weekday()
            weekend_boost = 5 if day_of_week >= 5 else 0
            
            # Add an upward trend
            trend = i / 10
            
            # Add some randomness
            noise = np.random.normal(0, 3)
            
            # Combine factors for final value
            value = max(0, 10 + trend + weekend_boost + noise)
            values.append(round(value))
        
        # Create dataframe and fit model
        df = pd.DataFrame({
            'ds': dates,
            'y': values
        })
        
        model.fit(df)
        return model
    
    def _create_dummy_forecasts(self, product, days):
        """Create dummy forecast data points for a product"""
        # Delete existing forecasts for this product
        DemandForecast.objects.filter(product=product).delete()
        
        current_date = datetime.now().date()
        forecasts_to_create = []
        
        # Base value - use product's price as a factor to create variety
        base_value = max(5, round(float(product.price) / 2))
        
        for i in range(days):
            forecast_date = current_date + timedelta(days=i)
            
            # Add day of week effect (higher on weekends)
            day_of_week = forecast_date.weekday()
            weekend_boost = 0.3 if day_of_week >= 5 else 0
            
            # Add an upward trend
            trend = i / 100
            
            # Add some randomness
            noise = np.random.normal(0, 0.2)
            
            # Combine factors for final values
            mean_value = base_value * (1 + trend + weekend_boost + noise)
            lower_bound = max(0, mean_value * 0.8)
            upper_bound = mean_value * 1.2
            
            forecasts_to_create.append(
                DemandForecast(
                    product=product,
                    date=forecast_date,
                    forecast_value=round(mean_value, 2),
                    lower_bound=round(lower_bound, 2),
                    upper_bound=round(upper_bound, 2)
                )
            )
        
        # Bulk create forecasts
        DemandForecast.objects.bulk_create(forecasts_to_create) 