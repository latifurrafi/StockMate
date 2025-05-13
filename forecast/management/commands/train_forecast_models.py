from django.core.management.base import BaseCommand
from django.db import transaction
from main_app.models import Product
from forecast.services.forecast_service import ForecastService
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
        start_time = time.time()
        
        # Get command options
        product_id = options.get('product_id')
        days = options.get('days', 90)
        use_parallel = options.get('parallel', False)
        
        if product_id:
            # Train a specific product's model
            self.stdout.write(f"Training forecast model for product ID {product_id}")
            success, message = ForecastService.train_model(product_id, periods=days)
            if success:
                self.stdout.write(self.style.SUCCESS(message))
            else:
                self.stdout.write(self.style.ERROR(message))
            return

        # Train models for all products
        products = Product.objects.all()
        total_products = products.count()
        
        self.stdout.write(f"Training forecast models for {total_products} products")
        
        if use_parallel:
            self._train_models_parallel(products, days)
        else:
            self._train_models_sequential(products, days)
            
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Completed in {elapsed_time:.2f} seconds"))

    def _train_models_sequential(self, products, days):
        """Train models one by one"""
        success_count = 0
        failed_count = 0
        
        for i, product in enumerate(products, start=1):
            self.stdout.write(f"[{i}/{products.count()}] Training model for {product.name}")
            
            try:
                success, message = ForecastService.train_model(product.id, periods=days)
                if success:
                    success_count += 1
                    self.stdout.write(f"  ✓ {message}")
                else:
                    failed_count += 1
                    self.stdout.write(f"  ✗ {message}")
            except Exception as e:
                failed_count += 1
                self.stdout.write(f"  ✗ Error: {str(e)}")
                logger.exception(f"Error training model for product {product.id}")
                
        self.stdout.write(f"Results: {success_count} succeeded, {failed_count} failed")

    def _train_models_parallel(self, products, days):
        """Train models in parallel using ThreadPoolExecutor"""
        success_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_product = {
                executor.submit(ForecastService.train_model, product.id, days): product
                for product in products
            }
            
            total = len(future_to_product)
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_product):
                product = future_to_product[future]
                completed += 1
                
                self.stdout.write(f"[{completed}/{total}] Processing {product.name}")
                
                try:
                    success, message = future.result()
                    if success:
                        success_count += 1
                        self.stdout.write(f"  ✓ {message}")
                    else:
                        failed_count += 1
                        self.stdout.write(f"  ✗ {message}")
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(f"  ✗ Error: {str(e)}")
                    logger.exception(f"Error training model for product {product.id}")
                    
        self.stdout.write(f"Results: {success_count} succeeded, {failed_count} failed") 