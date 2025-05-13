from django.db import models
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.user.username
    
class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    phone = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=200)
    address = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    suppliers = models.ManyToManyField(Supplier, related_name='products', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True)

    def stock_status(self):
        if self.stock <= 0:
            return "Out of Stock"
        elif self.stock <= self.reorder_level:
            return "Low Stock"
        else:
            return "In Stock"
    
    def stock_status_badge(self):
        status = self.stock_status()
        if status == "Out of Stock":
            return format_html('<span class="badge bg-danger">Out of Stock</span>')
        elif status == "Low Stock":
            return format_html('<span class="badge bg-warning">Low Stock</span>')
        else:
            return format_html('<span class="badge bg-success">In Stock</span>')
    
    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', self.image.url)
        return "No image"
    
    image_preview.short_description = "Preview"

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'pk': self.pk})

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    
    REASON_CHOICES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return from Customer'),
        ('return_to_supplier', 'Return to Supplier'),
        ('adjustment', 'Inventory Adjustment'),
        ('damaged', 'Damaged/Defective'),
        ('lost', 'Lost/Stolen'),
        ('other', 'Other'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    reference = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        is_new_record = self.pk is None
        
        # Save the transaction first
        super().save(*args, **kwargs)
        
        # Update product stock
        if is_new_record:
            if self.transaction_type == 'IN':
                self.product.stock += self.quantity
            elif self.transaction_type == 'OUT':
                self.product.stock -= self.quantity
            
            self.product.save()
    
    @property
    def total_value(self):
        if self.unit_price:
            return self.quantity * self.unit_price
        return 0
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity})"
    
    class Meta:
        ordering = ['-date']

# Use StockIn and StockOut as proxy models for backward compatibility
class StockIn(StockTransaction):
    class Meta:
        proxy = True
        
    def save(self, *args, **kwargs):
        self.transaction_type = 'IN'
        super().save(*args, **kwargs)

class StockOut(StockTransaction):
    class Meta:
        proxy = True
        
    def save(self, *args, **kwargs):
        self.transaction_type = 'OUT'
        super().save(*args, **kwargs)

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def item_count(self):
        return self.items.count()
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"
    
    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'pk': self.pk})

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total_price(self):
        return self.quantity * self.price
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity}) - Order #{self.order.id}"

class LowStockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_stock = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Alert: {self.product.name} - Min: {self.min_stock}"
    
    def resolve(self):
        self.is_resolved = True
        self.resolved_date = timezone.now()
        self.save()

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=50, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user}: {self.action} at {self.date}"
    
    class Meta:
        ordering = ['-date']

class Report(models.Model):
    REPORT_TYPES = [
        ('stock', 'Stock Report'),
        ('sales', 'Sales Report'),
        ('purchases', 'Purchases Report'),
        ('inventory', 'Inventory Valuation'),
        ('custom', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='custom')
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    parameters = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

# Signal to create low stock alerts automatically
@receiver(post_save, sender=Product)
def check_stock_level(sender, instance, **kwargs):
    if instance.stock <= instance.reorder_level and not LowStockAlert.objects.filter(product=instance, is_resolved=False).exists():
        LowStockAlert.objects.create(
            product=instance,
            min_stock=instance.reorder_level
        )

# Signal to handle order completion and stock reduction
@receiver(post_save, sender=Order)
def handle_order_completion(sender, instance, created, **kwargs):
    if not created and instance.status == 'completed':
        for item in instance.items.all():
            # Create stock out transaction
            StockTransaction.objects.create(
                product=item.product,
                quantity=item.quantity,
                transaction_type='OUT',
                reason='sale',
                customer=instance.customer,
                reference=f"Order #{instance.id}",
                unit_price=item.price,
                created_by=instance.created_by
            )

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('low_stock', 'Low Stock Alert'),
        ('new_order', 'New Order'),
        ('stock_in', 'Stock Added'),
        ('stock_out', 'Stock Removed'),
        ('supplier', 'Supplier Update'),
        ('system', 'System Notification'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)  # Optional link to related object
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.username}"

# ForecastModel and DemandForecast have been moved to the forecast app

class CustomerPortalOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='portal_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    contact_phone = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, default='Credit Card')
    payment_status = models.CharField(max_length=20, default='pending')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"Portal Order #{self.id} - {self.customer.name}"
    
    @property
    def item_count(self):
        return self.items.count()
    
    def update_total(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.save()
    
    class Meta:
        ordering = ['-order_date']

class CustomerPortalOrderItem(models.Model):
    order = models.ForeignKey(CustomerPortalOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        return self.quantity * self.price
    
    def save(self, *args, **kwargs):
        # If this is a new item being added
        if not self.pk:
            # Set price to current product price if not specified
            if not self.price:
                self.price = self.product.price
        
        super().save(*args, **kwargs)
        
        # Update order total
        self.order.update_total()
     
    