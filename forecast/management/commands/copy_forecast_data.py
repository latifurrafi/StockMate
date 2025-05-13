from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Copy forecast data from main_app tables to forecast app tables'

    def handle(self, *args, **options):
        # Check if old tables exist before attempting to copy data
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'main_app_forecastmodel'")
        old_model_table_exists = bool(cursor.fetchone())

        cursor.execute("SHOW TABLES LIKE 'main_app_demandforecast'")
        old_forecast_table_exists = bool(cursor.fetchone())

        if old_model_table_exists and old_forecast_table_exists:
            self.stdout.write("Found old forecast data tables. Copying data...")
            try:
                # Copy ForecastModel data
                cursor.execute("""
                    INSERT INTO forecast_forecastmodel (id, model_file, last_trained, metrics, product_id)
                    SELECT id, model_file, last_trained, metrics, product_id
                    FROM main_app_forecastmodel
                """)
                
                model_count = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f"Copied {model_count} forecast models"))
                
                # Copy DemandForecast data
                cursor.execute("""
                    INSERT INTO forecast_demandforecast (id, date, forecast_value, lower_bound, upper_bound, created_at, product_id) 
                    SELECT id, date, forecast_value, lower_bound, upper_bound, created_at, product_id
                    FROM main_app_demandforecast
                """)
                
                forecast_count = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f"Copied {forecast_count} demand forecasts"))
                
                # Optionally: reset sequences
                cursor.execute("SELECT MAX(id) FROM forecast_forecastmodel")
                max_model_id = cursor.fetchone()[0] or 0
                cursor.execute(f"ALTER TABLE forecast_forecastmodel AUTO_INCREMENT = {max_model_id + 1}")
                
                cursor.execute("SELECT MAX(id) FROM forecast_demandforecast")
                max_forecast_id = cursor.fetchone()[0] or 0
                cursor.execute(f"ALTER TABLE forecast_demandforecast AUTO_INCREMENT = {max_forecast_id + 1}")
                
                self.stdout.write(self.style.SUCCESS("Successfully copied all forecast data"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error copying data: {str(e)}"))
                logger.exception("Error copying forecast data")
        else:
            self.stdout.write("Old forecast tables not found. No data to copy.") 