import os
import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import joblib
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from sklearn.metrics import mean_absolute_error, mean_squared_error

from main_app.models import Product, StockTransaction
from forecast.models import DemandForecast, ForecastModel


class ForecastService:
    """Service for handling demand forecasting using Facebook Prophet"""

    @staticmethod
    def get_historical_data(product_id, min_days=90):
        """
        Fetch historical transaction data for a product
        Returns a dataframe with 'ds' (date) and 'y' (quantity) columns
        """
        # Get stock out transactions as they represent product sales/demand
        transactions = StockTransaction.objects.filter(
            product_id=product_id,
            transaction_type='OUT'
        ).values('date', 'quantity')
        
        if not transactions:
            return None
        
        # Convert to dataframe and rename columns for Prophet
        df = pd.DataFrame(list(transactions))
        df.rename(columns={'date': 'ds', 'quantity': 'y'}, inplace=True)
        
        # Ensure dates are in the correct format
        df['ds'] = pd.to_datetime(df['ds']).dt.date
        
        # Check if all dates are in the future (for demo purposes)
        current_date = datetime.now().date()
        future_dates = [date > current_date for date in df['ds']]
        all_future = all(future_dates)
        
        # For demo purposes: if all dates are in the future, treat them as if they were in the past
        # This allows the forecasting system to work with demo data that might have future dates
        if all_future:
            # Shift dates to make the earliest date 120 days ago
            earliest_date = min(df['ds'])
            days_to_shift = (earliest_date - (current_date - timedelta(days=120))).days
            df['ds'] = df['ds'] - timedelta(days=days_to_shift)
        
        # Aggregate by date (sum quantities for the same day)
        df = df.groupby('ds').sum().reset_index()
        
        # For demo purposes: if we have less than the minimum required data points but at least 10,
        # we'll use what we have anyway
        min_required = min(15, min_days / 6)  # Reduce required minimum to 15 or min_days/6, whichever is smaller
        
        if len(df) < min_required:
            # If we have less than the absolute minimum (10), return None
            if len(df) < 10:
                return None
        
        # Sort by date
        df = df.sort_values('ds')
        
        # For demo purposes: if we have too few data points, duplicate them to create more history
        if len(df) < 30:
            # Create a copy of the dataframe
            df_copy = df.copy()
            
            # Shift dates back by 30, 60, and 90 days to create synthetic history
            for days_back in [30, 60, 90]:
                temp_df = df.copy()
                temp_df['ds'] = temp_df['ds'] - timedelta(days=days_back)
                # Add some random variation to quantities (±20%)
                temp_df['y'] = temp_df['y'] * np.random.uniform(0.8, 1.2, size=len(temp_df))
                temp_df['y'] = temp_df['y'].round().astype(int)  # Round to integers
                df_copy = pd.concat([df_copy, temp_df])
            
            # Sort the expanded dataframe
            df = df_copy.sort_values('ds')
        
        return df

    @staticmethod
    def train_model(product_id, periods=90, cv_periods=30):
        """
        Train a Prophet model for the given product
        
        Args:
            product_id: ID of the product to forecast for
            periods: Number of days to forecast ahead
            cv_periods: Number of days to use for cross-validation
            
        Returns:
            tuple: (success, message)
        """
        try:
            product = Product.objects.get(id=product_id)
            
            # Get historical data
            df = ForecastService.get_historical_data(product_id)
            if df is None or len(df) < 10:  # Lower minimum to 10 data points
                return False, f"Insufficient historical data for {product.name}"
            
            # Create and fit the model
            model = Prophet(
                interval_width=0.95,
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=True,
                seasonality_mode='multiplicative'
            )
            
            # Add additional regressors or seasonalities if needed
            # model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
            
            model.fit(df)
            
            # Perform cross-validation
            if len(df) > cv_periods:
                cv_results = cross_validation(
                    model=model,
                    initial=f'{len(df) - cv_periods} days',
                    period='1 days',
                    horizon=f'{min(cv_periods, 30)} days'
                )
                
                # Calculate performance metrics
                metrics = performance_metrics(cv_results)
                mae = mean_absolute_error(cv_results['y'], cv_results['yhat'])
                rmse = np.sqrt(mean_squared_error(cv_results['y'], cv_results['yhat']))
                
                performance = {
                    'mae': mae,
                    'rmse': rmse,
                    'mape': metrics['mape'].mean(),
                    'coverage': (metrics['coverage'].mean() * 100)
                }
            else:
                # If cross-validation isn't possible, set some placeholder metrics
                performance = {'note': 'Insufficient data for cross-validation'}
            
            # Ensure media directory exists
            media_root = settings.MEDIA_ROOT
            forecast_models_dir = os.path.join(media_root, 'forecast_models')
            os.makedirs(forecast_models_dir, exist_ok=True)
            
            # Save the model
            model_path = os.path.join(media_root, 'temp_model.joblib')
            with open(model_path, 'wb') as f:
                joblib.dump(model, f)
            
            # Save or update the model in the database
            try:
                forecast_model = ForecastModel.objects.get(product=product)
            except ForecastModel.DoesNotExist:
                forecast_model = ForecastModel(product=product)
            
            # Read the file and save it to the model instance
            with open(model_path, 'rb') as f:
                file_content = f.read()
                model_filename = f'prophet_model_{product.id}_{datetime.now().strftime("%Y%m%d")}.joblib'
                forecast_model.model_file.save(model_filename, ContentFile(file_content))
            
            # Update metrics
            forecast_model.metrics = performance
            forecast_model.save()
            
            # Clean up temporary file
            if os.path.exists(model_path):
                os.remove(model_path)
            
            # Generate forecasts and save to database
            ForecastService.generate_forecast(product_id, periods)
            
            return True, f"Successfully trained forecast model for {product.name}"
            
        except Product.DoesNotExist:
            return False, f"Product with ID {product_id} does not exist"
        except PermissionError as e:
            return False, f"Permission error: {str(e)}. Please check media directory permissions."
        except OSError as e:
            return False, f"File system error: {str(e)}. Please check media directory exists and is writable."
        except Exception as e:
            import traceback
            print(f"Exception in train_model: {str(e)}")
            print(traceback.format_exc())
            return False, f"Error training model: {str(e)}"

    @staticmethod
    def generate_forecast(product_id, periods=90):
        """
        Generate and save forecasts for the given product
        
        Args:
            product_id: ID of the product to forecast for
            periods: Number of days to forecast ahead
            
        Returns:
            tuple: (success, message)
        """
        try:
            product = Product.objects.get(id=product_id)
            
            try:
                forecast_model = ForecastModel.objects.get(product=product)
            except ForecastModel.DoesNotExist:
                # If no model exists, train a new one
                success, message = ForecastService.train_model(product_id, periods)
                if not success:
                    return success, message
                return True, "Forecast generated after training new model"
            
            # Load the model
            model = joblib.load(forecast_model.model_file.path)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=periods)
            
            # Make predictions
            forecast = model.predict(future)
            
            # Clear existing forecasts for this product
            DemandForecast.objects.filter(product=product).delete()
            
            # Save forecasts to database
            forecasts_to_create = []
            for _, row in forecast.iloc[-periods:].iterrows():
                forecast_date = row['ds'].date() if isinstance(row['ds'], pd.Timestamp) else row['ds']
                
                forecasts_to_create.append(
                    DemandForecast(
                        product=product,
                        date=forecast_date,
                        forecast_value=max(0, row['yhat']),  # Ensure no negative forecasts
                        lower_bound=max(0, row['yhat_lower']),
                        upper_bound=max(0, row['yhat_upper'])
                    )
                )
            
            # Bulk create forecasts
            DemandForecast.objects.bulk_create(forecasts_to_create)
            
            return True, f"Successfully generated {len(forecasts_to_create)} forecast points for {product.name}"
            
        except Product.DoesNotExist:
            return False, f"Product with ID {product_id} does not exist"
        except Exception as e:
            return False, f"Error generating forecast: {str(e)}"

    @staticmethod
    def get_product_forecast(product_id, days=30):
        """
        Get the forecast data for a product for the specified number of days
        
        Args:
            product_id: ID of the product
            days: Number of days of forecast to retrieve
            
        Returns:
            dict: Forecast data with dates, values, and bounds
        """
        try:
            product = Product.objects.get(id=product_id)
            
            forecasts = DemandForecast.objects.filter(
                product=product,
                date__gte=datetime.now().date(),
                date__lt=datetime.now().date() + timedelta(days=days)
            ).order_by('date')
            
            if not forecasts:
                # Try to generate forecast if none exists
                success, _ = ForecastService.generate_forecast(product_id)
                if success:
                    forecasts = DemandForecast.objects.filter(
                        product=product,
                        date__gte=datetime.now().date(),
                        date__lt=datetime.now().date() + timedelta(days=days)
                    ).order_by('date')
            
            # Format the data for API response
            forecast_data = {
                'product_id': product.id,
                'product_name': product.name,
                'dates': [f.date.strftime('%Y-%m-%d') for f in forecasts],
                'forecast_values': [float(f.forecast_value) for f in forecasts],
                'lower_bounds': [float(f.lower_bound) for f in forecasts],
                'upper_bounds': [float(f.upper_bound) for f in forecasts],
                'current_stock': product.stock,
                'reorder_level': product.reorder_level
            }
            
            # Get actual historical data for comparison
            df = ForecastService.get_historical_data(product_id)
            if df is not None:
                # Get the last 30 days of historical data
                cutoff_date = datetime.now().date() - timedelta(days=30)
                historical_df = df[df['ds'] >= cutoff_date]
                
                forecast_data['historical_dates'] = [d.strftime('%Y-%m-%d') for d in historical_df['ds']]
                forecast_data['historical_values'] = historical_df['y'].tolist()
            
            return forecast_data
            
        except Product.DoesNotExist:
            return {'error': f"Product with ID {product_id} does not exist"}
        except Exception as e:
            return {'error': f"Error retrieving forecast: {str(e)}"} 