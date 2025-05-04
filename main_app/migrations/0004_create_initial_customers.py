from django.db import migrations, connection
from django.utils import timezone

def create_initial_customers(apps, schema_editor):
    """Create initial customers from existing order customers (users)."""
    Order = apps.get_model('main_app', 'Order')
    User = apps.get_model('auth', 'User')
    Customer = apps.get_model('main_app', 'Customer')
    
    # Get all order.customer_id values from the existing database
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT DISTINCT customer_id FROM main_app_order;")
        user_ids = [row[0] for row in cursor.fetchall()]
    except Exception:
        # Table might not exist yet
        return
    
    # Create a customer record for each user
    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            Customer.objects.create(
                id=user_id,  # Use the same ID to preserve relationships
                name=f"{user.first_name} {user.last_name}" if user.first_name else user.username,
                contact_info=user.email or "No contact info",
                phone="Not provided",
                email=user.email,
                created_at=timezone.now()
            )
        except User.DoesNotExist:
            # Create a placeholder customer if the user doesn't exist
            Customer.objects.create(
                id=user_id,
                name=f"Customer {user_id}",
                contact_info="Unknown",
                phone="Not provided",
                created_at=timezone.now()
            )

class Migration(migrations.Migration):
    dependencies = [
        ('main_app', '0003_customer_remove_stockin_product_and_more'),
    ]

    operations = [
        migrations.RunPython(create_initial_customers),
    ] 