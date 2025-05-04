from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import (
    UserProfile, Category, Product, StockTransaction, StockIn, StockOut, 
    Order, OrderItem, LowStockAlert, ActivityLog, Supplier, Report, Customer
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'truncated_bio', 'profile_picture_preview')
    search_fields = ('user__username', 'user__email', 'location')
    list_filter = ('location',)

    def truncated_bio(self, obj):
        return obj.bio[:50] + '...' if len(obj.bio) > 50 else obj.bio
    truncated_bio.short_description = 'Bio'

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.profile_picture.url)
        return "No Image"
    profile_picture_preview.short_description = 'Profile Picture'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'description')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Number of Products'

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('is_active', 'created_at')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'stock', 'stock_status', 'image_preview')
    list_filter = ('category', 'suppliers', 'is_active')
    search_fields = ('name', 'sku', 'description')
    list_editable = ('price', 'stock')
    readonly_fields = ('stock_status_badge', 'image_preview')
    filter_horizontal = ('suppliers',)
    fieldsets = (
        (None, {'fields': ('name', 'sku', 'description', 'category', 'suppliers')}),
        ('Pricing and Stock', {'fields': ('price', 'stock', 'reorder_level', 'stock_status_badge')}),
        ('Image', {'fields': ('image', 'image_preview')}),
        ('Metadata', {'fields': ('is_active', 'created_at', 'updated_at')})
    )
    readonly_fields = ('created_at', 'updated_at', 'stock_status_badge', 'image_preview')

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'transaction_type', 'quantity', 'date', 'reason', 'reference', 'created_by')
    list_filter = ('transaction_type', 'reason', 'date', 'product__category')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)

# StockIn Admin (proxy model)
@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'date', 'reason', 'supplier', 'reference', 'created_by')
    list_filter = ('reason', 'date', 'product__category', 'supplier')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('transaction_type', 'created_at')

# StockOut Admin (proxy model)
@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'date', 'reason', 'customer', 'reference', 'created_by')
    list_filter = ('reason', 'date', 'product__category', 'customer')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('transaction_type', 'created_at')
    
# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'item_count', 'total_amount', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('customer__name', 'notes')
    date_hierarchy = 'order_date'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product__name')

# LowStockAlert Admin
@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'min_stock', 'current_stock', 'date', 'is_resolved', 'resolved_date')
    list_filter = ('is_resolved', 'date')
    search_fields = ('product__name',)
    date_hierarchy = 'date'
    actions = ['mark_as_resolved']
    
    def current_stock(self, obj):
        return obj.product.stock
    current_stock.short_description = 'Current Stock'
    
    def mark_as_resolved(self, request, queryset):
        now = timezone.now()
        queryset.update(is_resolved=True, resolved_date=now)
        self.message_user(request, f"{queryset.count()} alerts marked as resolved.")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"

# ActivityLog Admin
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'date', 'content_type', 'object_id')
    list_filter = ('date', 'user', 'content_type')
    search_fields = ('user__username', 'action')
    date_hierarchy = 'date'
    readonly_fields = ('date',)

# Supplier Admin
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'email', 'phone', 'is_active')
    search_fields = ('name', 'contact_info', 'email', 'phone')
    list_filter = ('is_active',)
    fieldsets = (
        (None, {
            'fields': ('name', 'contact_info')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

# Report Admin
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'truncated_description', 'date', 'created_by')
    list_filter = ('report_type', 'date')
    search_fields = ('name', 'description')
    date_hierarchy = 'date'
    
    def truncated_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    truncated_description.short_description = 'Description'

# Admin site customization
admin.site.site_header = "Inventory Management System"
admin.site.site_title = "Inventory Admin"
admin.site.index_title = "Inventory Management Dashboard"

# Optional: Custom admin index to show dashboard
class InventoryAdminSite(admin.AdminSite):
    def index(self, request, extra_context=None):
        # Get some stats for the dashboard
        if extra_context is None:
            extra_context = {}
            
        # Products stats
        total_products = Product.objects.count()
        out_of_stock = Product.objects.filter(stock=0).count()
        low_stock = Product.objects.filter(stock__gt=0, stock__lte=10).count()
            
        # Order stats
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_this_month = Order.objects.filter(order_date__gte=start_of_month).count()
        
        # Recent activity
        recent_activity = ActivityLog.objects.all().order_by('-date')[:10]
            
        extra_context.update({
            'total_products': total_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'orders_this_month': orders_this_month,
            'recent_activity': recent_activity,
        })
            
        return super().index(request, extra_context)

# Uncomment below if you want to use the custom admin site
# inventory_admin_site = InventoryAdminSite(name='inventory_admin')
# inventory_admin_site.register(UserProfile, UserProfileAdmin)
# inventory_admin_site.register(Category, CategoryAdmin)
# ... register all models with the custom admin site
