from django.db import migrations
from django.utils import timezone

def migrate_stock_data(apps, schema_editor):
    """Migrate existing StockIn and StockOut data to the new StockTransaction model."""
    # First, try to find original StockIn/StockOut tables in the database
    StockTransaction = apps.get_model('main_app', 'StockTransaction')
    Product = apps.get_model('main_app', 'Product')
    
    # Try to access old stock data using raw SQL
    cursor = schema_editor.connection.cursor()
    
    # Try to get StockIn data
    try:
        cursor.execute("SELECT id, product_id, quantity, date FROM main_app_stockin;")
        stock_in_rows = cursor.fetchall()
        
        for row in stock_in_rows:
            try:
                product = Product.objects.get(id=row[1])
                StockTransaction.objects.create(
                    id=row[0],  # Keep the same ID
                    product=product,
                    quantity=row[2],
                    transaction_type='IN',
                    reason='purchase',
                    date=row[3] or timezone.now(),
                    created_at=timezone.now()
                )
            except Product.DoesNotExist:
                pass  # Skip if product doesn't exist
    except Exception:
        # Table might not exist or be empty
        pass
        
    # Try to get StockOut data
    try:
        cursor.execute("SELECT id, product_id, quantity, date FROM main_app_stockout;")
        stock_out_rows = cursor.fetchall()
        
        for row in stock_out_rows:
            try:
                product = Product.objects.get(id=row[1])
                StockTransaction.objects.create(
                    id=row[0] + 10000,  # Avoid ID conflicts with StockIn
                    product=product,
                    quantity=row[2],
                    transaction_type='OUT',
                    reason='sale',
                    date=row[3] or timezone.now(),
                    created_at=timezone.now()
                )
            except Product.DoesNotExist:
                pass  # Skip if product doesn't exist
    except Exception:
        # Table might not exist or be empty
        pass

def migrate_orders(apps, schema_editor):
    """Create OrderItems from existing Order model data."""
    Order = apps.get_model('main_app', 'Order')
    OrderItem = apps.get_model('main_app', 'OrderItem')
    Product = apps.get_model('main_app', 'Product')
    
    # Try to access the old order data using raw SQL to get product_id and quantity
    cursor = schema_editor.connection.cursor()
    
    try:
        cursor.execute("SELECT id, product_id, quantity FROM main_app_order;")
        order_rows = cursor.fetchall()
        
        for row in order_rows:
            order_id = row[0]
            product_id = row[1]
            quantity = row[2]
            
            try:
                order = Order.objects.get(id=order_id)
                product = Product.objects.get(id=product_id)
                
                # Create an OrderItem for this order
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
            except (Order.DoesNotExist, Product.DoesNotExist):
                pass  # Skip if order or product doesn't exist
    except Exception:
        # Table might not have those columns
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('main_app', '0004_create_initial_customers'),
    ]

    operations = [
        migrations.RunPython(migrate_stock_data),
        migrations.RunPython(migrate_orders),
    ] 