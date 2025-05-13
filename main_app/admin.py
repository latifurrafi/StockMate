from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.contrib.filters.admin import (
    RangeNumericListFilter,
    RangeNumericFilter,
    BooleanRadioFilter,
    RangeDateTimeFilter,
)

from .models import (
    UserProfile, Category, Product, StockTransaction, StockIn, StockOut, 
    Order, OrderItem, LowStockAlert, ActivityLog, Supplier, Report, Customer, Notification, CustomerPortalOrder, CustomerPortalOrderItem
)

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
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
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'product_count', 'description')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Number of Products'

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active')
    search_fields = ('name', 'email', 'phone')
    list_filter = (('is_active', BooleanRadioFilter), ('created_at', RangeDateTimeFilter))
    
class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'stock', 'stock_status', 'image_preview')
    list_filter = ('category', 'suppliers', ('is_active', BooleanRadioFilter), ('stock', RangeNumericFilter))
    search_fields = ('name', 'sku', 'description')
    list_editable = ('price',)
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
class StockTransactionAdmin(ModelAdmin):
    list_display = ('id', 'product', 'transaction_type', 'quantity', 'date', 'reason', 'reference', 'created_by')
    list_filter = ('transaction_type', 'reason', ('date', RangeDateTimeFilter), 'product__category')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)

# StockIn Admin (proxy model)
@admin.register(StockIn)
class StockInAdmin(ModelAdmin):
    list_display = ('product', 'quantity', 'date', 'reason', 'supplier', 'reference', 'created_by')
    list_filter = ('reason', ('date', RangeDateTimeFilter), 'product__category', 'supplier')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('transaction_type', 'created_at')

# StockOut Admin (proxy model)
@admin.register(StockOut)
class StockOutAdmin(ModelAdmin):
    list_display = ('product', 'quantity', 'date', 'reason', 'customer', 'reference', 'created_by')
    list_filter = ('reason', ('date', RangeDateTimeFilter), 'product__category', 'customer')
    search_fields = ('product__name', 'reference', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('transaction_type', 'created_at')
    
# Order Admin
@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'customer', 'item_count', 'total_amount', 'status', 'order_date')
    list_filter = ('status', ('order_date', RangeDateTimeFilter))
    search_fields = ('customer__name', 'notes')
    date_hierarchy = 'order_date'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product__name')

# LowStockAlert Admin
@admin.register(LowStockAlert)
class LowStockAlertAdmin(ModelAdmin):
    list_display = ('product', 'min_stock', 'current_stock', 'date', 'is_resolved', 'resolved_date')
    list_filter = (('is_resolved', BooleanRadioFilter), ('date', RangeDateTimeFilter))
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
class ActivityLogAdmin(ModelAdmin):
    list_display = ('user', 'action', 'date', 'content_type', 'object_id')
    list_filter = (('date', RangeDateTimeFilter), 'user', 'content_type')
    search_fields = ('user__username', 'action')
    date_hierarchy = 'date'
    readonly_fields = ('date',)

# Supplier Admin
@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ('name', 'contact_info', 'email', 'phone', 'is_active')
    search_fields = ('name', 'contact_info', 'email', 'phone')
    list_filter = (('is_active', BooleanRadioFilter),)
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
class ReportAdmin(ModelAdmin):
    list_display = ('name', 'report_type', 'truncated_description', 'date', 'created_by')
    list_filter = ('report_type', ('date', RangeDateTimeFilter))
    search_fields = ('name', 'description')
    date_hierarchy = 'date'
    
    def truncated_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    truncated_description.short_description = 'Description'

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', ('is_read', BooleanRadioFilter), ('created_at', RangeDateTimeFilter))
    search_fields = ('title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

class CustomerPortalOrderItemInline(TabularInline):
    model = CustomerPortalOrderItem
    extra = 0
    readonly_fields = ('subtotal',)

@admin.register(CustomerPortalOrder)
class CustomerPortalOrderAdmin(ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'status', 'total_amount', 'payment_status')
    list_filter = ('status', 'payment_status', 'payment_method', ('order_date', RangeDateTimeFilter))
    search_fields = ('customer__name', 'shipping_address', 'notes')
    readonly_fields = ('order_date',)
    
    fieldsets = (
        (None, {'fields': ('customer', 'order_date', 'status', 'payment_status', 'payment_method')}),
        ('Contact & Shipping', {'fields': ('shipping_address', 'contact_phone')}),
        ('Financial', {'fields': ('total_amount', 'tracking_number')}),
        ('Notes', {'fields': ('notes',)})
    )
    
    inlines = [CustomerPortalOrderItemInline]

# Admin site customization
admin.site.site_header = "StockMate Inventory Management"
admin.site.site_title = "StockMate Admin"
admin.site.index_title = "StockMate Dashboard"
