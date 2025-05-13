from django.core.management.base import BaseCommand
from django.db import transaction
from main_app.models import Product
from main_app.services.forecast_service import ForecastService
import logging
import time
import concurrent.futures

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Train demand forecasting models for products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=int,
            help='ID of a specific product to train model for',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to forecast ahead (default: 90)',
        )
        parser.add_argument(
            '--min-transactions',
            type=int,
            default=30,
            help='Minimum number of transactions required to train a model (default: 30)',
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Train models in parallel',
        )

    def handle(self, *args, **options):
        product_id = options.get('product_id')
        days = options.get('days')
        min_transactions = options.get('min_transactions')
        parallel = options.get('parallel')
        
        start_time = time.time()
        
        if product_id:
            # Train for a specific product
            self.stdout.write(self.style.WARNING(f"Training forecast model for product ID {product_id}..."))
            success, message = ForecastService.train_model(product_id, periods=days)
            
            if success:
                self.stdout.write(self.style.SUCCESS(message))
            else:
                self.stdout.write(self.style.ERROR(message))
                
        else:
            # Train for all products with sufficient data
            self.stdout.write(self.style.WARNING("Training forecast models for all eligible products..."))
            
            # Get all active products
            products = Product.objects.filter(is_active=True)
            self.stdout.write(f"Found {products.count()} active products")
            
            success_count = 0
            error_count = 0
            skipped_count = 0
            
            if parallel:
                # Train models in parallel using ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(self._train_model_for_product, product.id, days): product.id for product in products}
                    
                    for future in concurrent.futures.as_completed(futures):
                        product_id = futures[future]
                        try:
                            result, message = future.result()
                            if result:
                                success_count += 1
                                self.stdout.write(self.style.SUCCESS(f"[Product {product_id}] {message}"))
                            else:
                                if "Insufficient historical data" in message:
                                    skipped_count += 1
                                    self.stdout.write(self.style.WARNING(f"[Product {product_id}] {message}"))
                                else:
                                    error_count += 1
                                    self.stdout.write(self.style.ERROR(f"[Product {product_id}] {message}"))
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f"[Product {product_id}] Error: {str(e)}"))
            else:
                # Train models sequentially
                for product in products:
                    success, message = self._train_model_for_product(product.id, days)
                    
                    if success:
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS(f"[Product {product.id}] {message}"))
                    else:
                        if "Insufficient historical data" in message:
                            skipped_count += 1
                            self.stdout.write(self.style.WARNING(f"[Product {product.id}] {message}"))
                        else:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f"[Product {product.id}] {message}"))
            
            # Print summary
            elapsed_time = time.time() - start_time
            self.stdout.write("\nForecast Training Summary:")
            self.stdout.write(f"- Total products: {products.count()}")
            self.stdout.write(f"- Successfully trained: {success_count}")
            self.stdout.write(f"- Skipped (insufficient data): {skipped_count}")
            self.stdout.write(f"- Errors: {error_count}")
            self.stdout.write(f"- Time elapsed: {elapsed_time:.2f} seconds")
    
    def _train_model_for_product(self, product_id, days):
        """Helper method to train model for a single product"""
        try:
            return ForecastService.train_model(product_id, periods=days)
        except Exception as e:
            logger.exception(f"Error training model for product {product_id}")
            return False, f"Error: {str(e)}" 