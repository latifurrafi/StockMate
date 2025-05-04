import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_project.settings')
django.setup()

# Import models
from django.contrib.auth.models import User
from main_app.models import (
    UserProfile, Category, Product, StockIn, StockOut, Order, 
    LowStockAlert, ActivityLog, Supplier, Report
)

# Clear existing data (optional)
# User.objects.all().delete()
# UserProfile.objects.all().delete()
# Category.objects.all().delete()
# Product.objects.all().delete()
# StockIn.objects.all().delete()
# StockOut.objects.all().delete()
# Order.objects.all().delete()
# Notification.objects.all().delete()
# LowStockAlert.objects.all().delete()
# ActivityLog.objects.all().delete()
# Supplier.objects.all().delete()
# Report.objects.all().delete()

# Create users
users = [
    {'username': 'admin', 'email': 'admin@example.com', 'password': 'admin123', 'is_staff': True, 'is_superuser': True},
    {'username': 'john_doe', 'email': 'john@example.com', 'password': 'password123', 'first_name': 'John', 'last_name': 'Doe'},
    {'username': 'jane_smith', 'email': 'jane@example.com', 'password': 'password123', 'first_name': 'Jane', 'last_name': 'Smith'},
    {'username': 'bob_johnson', 'email': 'bob@example.com', 'password': 'password123', 'first_name': 'Bob', 'last_name': 'Johnson'},
    {'username': 'sarah_williams', 'email': 'sarah@example.com', 'password': 'password123', 'first_name': 'Sarah', 'last_name': 'Williams'},
]

# Get existing users instead of creating new ones
created_users = list(User.objects.all())
print(f"Found {len(created_users)} existing users")

# Skip user profile creation since they should already exist
# for user in created_users:
#     locations = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
#     bios = [
#         f"Inventory manager with {random.randint(1, 15)} years of experience.",
#         "Supply chain professional passionate about efficiency.",
#         "Retail specialist focused on stock management.",
#         "Operations manager with expertise in inventory control.",
#         "Logistics coordinator with a detail-oriented approach."
#     ]
    
#     UserProfile.objects.create(
#         user=user,
#         bio=random.choice(bios),
#         location=random.choice(locations)
#     )
#     print(f"Created profile for: {user.username}")

# Create categories
categories = [
    "Electronics",
    "Office Supplies",
    "Furniture",
    "Kitchen & Dining",
    "Apparel",
    "Health & Beauty",
    "Sports & Outdoors",
    "Toys & Games"
]

created_categories = []
# Get all existing categories first
existing_categories = Category.objects.all()
for category_name in categories:
    # Try to find an existing category
    category_matches = existing_categories.filter(name=category_name)
    if category_matches.exists():
        category = category_matches.first()
        created_categories.append(category)
        print(f"Using existing category: {category.name}")
    else:
        # Create a new category if it doesn't exist
        category = Category.objects.create(name=category_name)
        created_categories.append(category)
        print(f"Created category: {category.name}")

# Create products
products_data = [
    # Electronics
    {"name": "Laptop", "description": "15-inch laptop with 8GB RAM", "price": "899.99", "stock": 25, "category": "Electronics"},
    {"name": "Smartphone", "description": "Latest model smartphone", "price": "699.99", "stock": 50, "category": "Electronics"},
    {"name": "Wireless Earbuds", "description": "Bluetooth wireless earbuds", "price": "129.99", "stock": 75, "category": "Electronics"},
    {"name": "Desktop Monitor", "description": "24-inch HD monitor", "price": "249.99", "stock": 15, "category": "Electronics"},
    {"name": "Tablet", "description": "10-inch tablet with 64GB storage", "price": "349.99", "stock": 30, "category": "Electronics"},
    
    # Office Supplies
    {"name": "Printer Paper", "description": "500 sheets of printer paper", "price": "9.99", "stock": 200, "category": "Office Supplies"},
    {"name": "Ballpoint Pens", "description": "Pack of 12 blue ballpoint pens", "price": "4.99", "stock": 150, "category": "Office Supplies"},
    {"name": "Sticky Notes", "description": "Assorted colors sticky notes", "price": "3.99", "stock": 100, "category": "Office Supplies"},
    {"name": "Stapler", "description": "Standard desktop stapler", "price": "8.99", "stock": 40, "category": "Office Supplies"},
    {"name": "File Folders", "description": "Box of 50 manila file folders", "price": "12.99", "stock": 60, "category": "Office Supplies"},
    
    # Furniture
    {"name": "Office Chair", "description": "Ergonomic office chair", "price": "199.99", "stock": 10, "category": "Furniture"},
    {"name": "Desk", "description": "Computer desk with drawers", "price": "249.99", "stock": 8, "category": "Furniture"},
    {"name": "Bookshelf", "description": "5-shelf bookcase", "price": "129.99", "stock": 12, "category": "Furniture"},
    {"name": "Filing Cabinet", "description": "3-drawer filing cabinet", "price": "99.99", "stock": 15, "category": "Furniture"},
    {"name": "Conference Table", "description": "8-person conference table", "price": "499.99", "stock": 5, "category": "Furniture"},
    
    # Kitchen & Dining
    {"name": "Coffee Maker", "description": "12-cup programmable coffee maker", "price": "49.99", "stock": 20, "category": "Kitchen & Dining"},
    {"name": "Microwave", "description": "Countertop microwave oven", "price": "89.99", "stock": 15, "category": "Kitchen & Dining"},
    {"name": "Dish Set", "description": "16-piece ceramic dish set", "price": "39.99", "stock": 25, "category": "Kitchen & Dining"},
    {"name": "Cutlery Set", "description": "24-piece stainless steel cutlery set", "price": "29.99", "stock": 30, "category": "Kitchen & Dining"},
    {"name": "Blender", "description": "High-speed blender", "price": "69.99", "stock": 18, "category": "Kitchen & Dining"},
    
    # Apparel
    {"name": "T-Shirt", "description": "Cotton crew neck t-shirt", "price": "19.99", "stock": 100, "category": "Apparel"},
    {"name": "Jeans", "description": "Classic fit blue jeans", "price": "39.99", "stock": 75, "category": "Apparel"},
    {"name": "Hoodie", "description": "Pullover hoodie sweatshirt", "price": "29.99", "stock": 50, "category": "Apparel"},
    {"name": "Socks", "description": "Pack of 6 athletic socks", "price": "12.99", "stock": 120, "category": "Apparel"},
    {"name": "Winter Jacket", "description": "Insulated winter jacket", "price": "89.99", "stock": 25, "category": "Apparel"},
]

created_products = []
# Get all existing products
existing_products = Product.objects.all()
for product_data in products_data:
    category_name = product_data.pop("category")
    category = next((c for c in created_categories if c.name == category_name), None)
    
    if category:
        product_name = product_data["name"]
        product_matches = existing_products.filter(name=product_name)
        
        if product_matches.exists():
            product = product_matches.first()
            created_products.append(product)
            print(f"Using existing product: {product.name}")
        else:
            product_data["category"] = category
            product_data["price"] = Decimal(product_data["price"])
            product = Product.objects.create(**product_data)
            created_products.append(product)
            print(f"Created product: {product.name}")

# Create suppliers
suppliers_data = [
    {"name": "Global Electronics Inc.", "contact_info": "John Smith", "address": "123 Tech Blvd, San Jose, CA", "email": "info@globalelectronics.com", "phone": "555-123-4567"},
    {"name": "Office World", "contact_info": "Mary Johnson", "address": "456 Business Ave, Chicago, IL", "email": "sales@officeworld.com", "phone": "555-234-5678"},
    {"name": "Furniture Plus", "contact_info": "Robert Davis", "address": "789 Comfort St, Boston, MA", "email": "contact@furnitureplus.com", "phone": "555-345-6789"},
    {"name": "Kitchen Essentials", "contact_info": "Sarah Wilson", "address": "321 Culinary Rd, Portland, OR", "email": "orders@kitchenessentials.com", "phone": "555-456-7890"},
    {"name": "Fashion Distributors", "contact_info": "James Brown", "address": "654 Style Ave, New York, NY", "email": "wholesale@fashiondist.com", "phone": "555-567-8901"},
]

created_suppliers = []
# Get all existing suppliers
existing_suppliers = Supplier.objects.all()
for supplier_data in suppliers_data:
    supplier_name = supplier_data["name"]
    supplier_matches = existing_suppliers.filter(name=supplier_name)
    
    if supplier_matches.exists():
        supplier = supplier_matches.first()
        created_suppliers.append(supplier)
        print(f"Using existing supplier: {supplier.name}")
    else:
        supplier = Supplier.objects.create(**supplier_data)
        created_suppliers.append(supplier)
        print(f"Created supplier: {supplier.name}")

# Create stock ins (past 3 months)
for _ in range(100):
    product = random.choice(created_products)
    quantity = random.randint(5, 50)
    days_ago = random.randint(0, 90)
    date = timezone.now() - timedelta(days=days_ago)
    
    stock_in = StockIn.objects.create(
        product=product,
        quantity=quantity,
        date=date
    )
    print(f"Created stock in: {quantity} units of {product.name}")

# Create stock outs (past 3 months)
for _ in range(125):
    product = random.choice(created_products)
    quantity = random.randint(1, 10)
    days_ago = random.randint(0, 90)
    date = timezone.now() - timedelta(days=days_ago)
    
    stock_out = StockOut.objects.create(
        product=product,
        quantity=quantity,
        date=date
    )
    print(f"Created stock out: {quantity} units of {product.name}")

# Skip order creation as the model has changed
# # Create orders (past 3 months)
# for _ in range(150):
#     customer = random.choice(created_users)
#     product = random.choice(created_products)
#     quantity = random.randint(1, 5)
#     days_ago = random.randint(0, 90)
#     order_date = timezone.now() - timedelta(days=days_ago)
#     
#     order = Order.objects.create(
#         customer=customer,
#         product=product,
#         quantity=quantity,
#         order_date=order_date
#     )
#     print(f"Created order: {quantity} units of {product.name} for {customer.username}")

# # Create notifications
# notification_messages = [
#     "New order received for {product}",
#     "Low stock alert for {product}",
#     "Restocked {product} with {quantity} units",
#     "Monthly inventory report is ready",
#     "Price update on {product}",
#     "New supplier added: {supplier}",
#     "{product} is now out of stock",
#     "System maintenance scheduled for tomorrow",
#     "{user} has updated product information for {product}",
#     "Your order #{order_id} has been processed"
# ]

# for _ in range(25):
#     user = random.choice(created_users)
#     product = random.choice(created_products)
#     supplier = random.choice(created_suppliers)
#     order_id = random.randint(1000, 9999)
    
#     message_template = random.choice(notification_messages)
#     message = message_template.format(
#         product=product.name,
#         quantity=random.randint(10, 50),
#         supplier=supplier.name,
#         user=random.choice(created_users).username,
#         order_id=order_id
#     )
    
#     days_ago = random.randint(0, 30)
#     created_at = timezone.now() - timedelta(days=days_ago)
#     is_read = random.choice([True, False])
    
#     notification = Notification.objects.create(
#         user=user,
#         message=message,
#         created_at=created_at,
#         is_read=is_read
#     )
#     print(f"Created notification for {user.username}: {message[:30]}...")

# Create low stock alerts
for product in random.sample(created_products, 10):
    min_stock = random.randint(5, 20)
    days_ago = random.randint(0, 30)
    date = timezone.now() - timedelta(days=days_ago)
    
    alert = LowStockAlert.objects.create(
        product=product,
        min_stock=min_stock,
        date=date
    )
    print(f"Created low stock alert for {product.name} at {min_stock} units")

# Create activity logs
actions = [
    "Added new product: {product}",
    "Updated stock for {product}",
    "Processed order #{order_id}",
    "Generated monthly report",
    "Modified product price: {product}",
    "Added new supplier: {supplier}",
    "Removed discontinued product: {product}",
    "Updated user permissions for {user}",
    "Logged in to the system",
    "Exported inventory data"
]

for _ in range(200):
    user = random.choice(created_users)
    product = random.choice(created_products)
    supplier = random.choice(created_suppliers)
    other_user = random.choice(created_users)
    order_id = random.randint(1000, 9999)
    
    action_template = random.choice(actions)
    action = action_template.format(
        product=product.name,
        supplier=supplier.name,
        user=other_user.username,
        order_id=order_id
    )
    
    days_ago = random.randint(0, 90)
    date = timezone.now() - timedelta(days=days_ago)
    
    log = ActivityLog.objects.create(
        user=user,
        action=action,
        date=date
    )
    print(f"Created activity log for {user.username}: {action[:30]}...")

# Create reports
report_types = [
    {"name": "Monthly Inventory Report - {month}", "description": "Complete inventory status as of the end of {month}."},
    {"name": "Sales Summary - {month}", "description": "Summary of all sales transactions during {month}."},
    {"name": "Low Stock Report - {month}", "description": "List of products with stock levels below minimum thresholds."},
    {"name": "Supplier Performance Report - {month}", "description": "Analysis of supplier delivery times and quality for {month}."},
    {"name": "Product Movement Analysis - {month}", "description": "Detailed analysis of product movement patterns during {month}."}
]

months = ["January", "February", "March", "April", "May"]

for month in months:
    for report_type in report_types:
        name = report_type["name"].format(month=month)
        description = report_type["description"].format(month=month)
        days_ago = months.index(month) * 30
        date = timezone.now() - timedelta(days=days_ago)
        
        report = Report.objects.create(
            name=name,
            description=description,
            date=date
        )
        print(f"Created report: {name}")

print("Dummy data generation complete!")