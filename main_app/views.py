from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Sum, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import login
import csv
from datetime import datetime, timedelta
import json

from .models import (
    Product, StockTransaction, StockIn, StockOut, Supplier, 
    Category, ActivityLog, LowStockAlert, Order, OrderItem, 
    Customer, Report, UserProfile, Notification, CustomerPortalOrder, CustomerPortalOrderItem
)
from forecast.models import ForecastModel, DemandForecast
from .forms import CustomUserCreationForm

# Import the render_to_pdf function from utils
from .utils import render_to_pdf

# Import the notification functions from utils
from .utils import (
    create_notification,
    notify_low_stock,
    notify_stock_transaction,
    notify_new_order,
    notify_supplier_update,
)

# ===== Dashboard =====
@login_required
def dashboard(request):
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # Key metrics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_suppliers = Supplier.objects.count()
    
    # Category stats
    top_categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:5]
    
    # Recent activity log
    recent_activity = ActivityLog.objects.select_related('user').order_by('-date')[:10]
    
    # Low stock alerts
    low_stock_items = Product.objects.filter(
        stock__lte=F('reorder_level')
    ).select_related('category')[:10]
    
    # Stock transactions for the last 7 days
    stock_in_data = StockTransaction.objects.filter(
        transaction_type='IN', 
        date__gte=seven_days_ago
    ).values('date__date').annotate(
        total=Count('id')
    ).order_by('date__date')
    
    stock_out_data = StockTransaction.objects.filter(
        transaction_type='OUT', 
        date__gte=seven_days_ago
    ).values('date__date').annotate(
        total=Count('id')
    ).order_by('date__date')
    
    # Process data for chart
    dates = []
    stock_in_counts = []
    stock_out_counts = []
    
    # Create arrays for the last 7 days
    for i in range(7):
        date = (today - timedelta(days=6-i)).date()
        date_str = date.strftime('%a')  # Short day name (Mon, Tue, etc.)
        dates.append(date_str)
        
        # Find stock in for this date
        in_data = next((item for item in stock_in_data if item['date__date'] == date), None)
        stock_in_counts.append(in_data['total'] if in_data else 0)
        
        # Find stock out for this date
        out_data = next((item for item in stock_out_data if item['date__date'] == date), None)
        stock_out_counts.append(out_data['total'] if out_data else 0)
    
    # Prepare recent transactions for display
    recent_transactions = []
    
    # Add stock in transactions
    for trans in StockTransaction.objects.filter(transaction_type='IN').select_related('product', 'supplier').order_by('-date')[:5]:
        recent_transactions.append({
            'type': 'stock_in',
            'product_name': trans.product.name,
            'quantity': trans.quantity,
            'date': trans.date.strftime('%b %d, %Y'),
            'supplier': trans.supplier.name if trans.supplier else 'N/A',
            'order_id': None
        })
    
    # Add stock out transactions
    for trans in StockTransaction.objects.filter(transaction_type='OUT').select_related('product').order_by('-date')[:5]:
        recent_transactions.append({
            'type': 'stock_out',
            'product_name': trans.product.name,
            'quantity': trans.quantity,
            'date': trans.date.strftime('%b %d, %Y'),
            'supplier': None,
            'order_id': trans.reference or 'N/A'
        })
    
    # Sort combined transactions by date (newest first)
    recent_transactions.sort(key=lambda x: x['date'], reverse=True)
    recent_transactions = recent_transactions[:5]  # Limit to 5 total
    
    # Inventory value
    inventory_value = Product.objects.aggregate(
        total_value=Sum(
            ExpressionWrapper(F('stock') * F('price'), output_field=DecimalField())
        )
    )['total_value'] or 0
    
    # Recent orders
    recent_orders = Order.objects.select_related('customer').order_by('-order_date')[:5]
    
    context = {
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'total_suppliers': total_suppliers,
        'top_categories': top_categories,
        'recent_activity': recent_activity,
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions,
        'inventory_value': inventory_value,
        'recent_orders': recent_orders,
        'chart_dates': json.dumps(dates),
        'chart_stock_in': json.dumps(stock_in_counts),
        'chart_stock_out': json.dumps(stock_out_counts),
        'low_stock_count': low_stock_items.count()
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def dashboard_pdf_report(request):
    """Generate a PDF report of dashboard data"""
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Key metrics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_suppliers = Supplier.objects.count()
    
    # Top categories
    top_categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:5]
    
    # Low stock alerts
    low_stock_items = Product.objects.filter(
        stock__lte=F('reorder_level')
    ).select_related('category')[:10]
    
    # Monthly stock transactions (last 7 days)
    seven_days_ago = today - timedelta(days=7)
    stock_in_data = StockTransaction.objects.filter(
        transaction_type='IN', 
        date__gte=seven_days_ago
    ).values('date__date').annotate(
        total=Count('id')
    ).order_by('date__date')
    
    stock_out_data = StockTransaction.objects.filter(
        transaction_type='OUT', 
        date__gte=seven_days_ago
    ).values('date__date').annotate(
        total=Count('id')
    ).order_by('date__date')
    
    # Process stock data for display
    dates = []
    stock_in_counts = []
    stock_out_counts = []
    
    # Fill in dates and get data for the last 7 days
    for i in range(7):
        date = (today - timedelta(days=i)).date()
        dates.insert(0, date.strftime('%Y-%m-%d'))
        
        # Find stock in for this date
        in_data = next((item for item in stock_in_data if item['date__date'] == date), None)
        stock_in_counts.insert(0, in_data['total'] if in_data else 0)
        
        # Find stock out for this date
        out_data = next((item for item in stock_out_data if item['date__date'] == date), None)
        stock_out_counts.insert(0, out_data['total'] if out_data else 0)
    
    # Recent activity
    recent_activity = ActivityLog.objects.select_related('user').order_by('-date')[:10]
    
    # Context for the PDF template
    context = {
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'total_suppliers': total_suppliers,
        'top_categories': top_categories,
        'low_stock_items': low_stock_items,
        'recent_activity': recent_activity,
        'dates': dates,
        'stock_in_counts': stock_in_counts,
        'stock_out_counts': stock_out_counts,
        'now': timezone.now().strftime('%B %d, %Y at %I:%M %p')
    }
    
    # Generate PDF
    pdf = render_to_pdf('pdf/dashboard_report.html', context)
    
    # Return PDF response with appropriate filename
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"dashboard_report_{timezone.now().strftime('%Y%m%d')}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    # If PDF generation failed
    return HttpResponse("Error generating PDF", status=400)

# ===== Products =====
@login_required
def products(request):
    # Get all products with filters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock_status', '')
    
    products_list = Product.objects.select_related('category').all()
    
    # Apply filters
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) | 
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        products_list = products_list.filter(category__id=category_filter)
    
    if stock_filter:
        if stock_filter == 'low':
            products_list = products_list.filter(stock__lte=F('reorder_level'))
        elif stock_filter == 'out':
            products_list = products_list.filter(stock=0)
        elif stock_filter == 'in_stock':
            products_list = products_list.filter(stock__gt=F('reorder_level'))
    
    # Pagination
    paginator = Paginator(products_list, 10)  # Show 10 products per page
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'products': products_page,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_filter': stock_filter
    }
    
    return render(request, 'products.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # Get transaction history
    transactions = StockTransaction.objects.filter(product=product).order_by('-date')[:10]
    
    # Stock level over time
    stock_data = []
    current_stock = product.stock
    
    for transaction in reversed(list(transactions)):
        if transaction.transaction_type == 'IN':
            current_stock -= transaction.quantity
        else:
            current_stock += transaction.quantity
        
        stock_data.append({
            'date': transaction.date.strftime('%Y-%m-%d'),
            'stock': current_stock
        })
    
    # Recent orders containing this product
    recent_orders = OrderItem.objects.filter(product=product).select_related('order').order_by('-order__order_date')[:5]
    
    context = {
        'product': product,
        'transactions': transactions,
        'stock_data': json.dumps(stock_data),
        'recent_orders': recent_orders,
    }
    
    return render(request, 'product_detail.html', context)

@login_required
@permission_required('main_app.add_product')
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        initial_stock = int(request.POST.get('initial_stock', 0))
        reorder_level = int(request.POST.get('reorder_level', 5))
        category_id = request.POST.get('category')
        supplier_ids = request.POST.getlist('suppliers')
        image = request.FILES.get('image')
        
        try:
            category = Category.objects.get(id=category_id)
            
            # Create new product
            product = Product.objects.create(
                name=name,
                sku=sku,
                description=description,
                price=price,
                stock=initial_stock,
                reorder_level=reorder_level,
                category=category
            )
            
            # Add suppliers
            if supplier_ids:
                suppliers = Supplier.objects.filter(id__in=supplier_ids)
                product.suppliers.add(*suppliers)
            
            if image:
                product.image = image
                product.save()
            
            # If initial stock is provided, create a stock in record
            if initial_stock > 0:
                StockTransaction.objects.create(
                    product=product,
                    quantity=initial_stock,
                    transaction_type='IN',
                    reason='purchase',
                    date=timezone.now(),
                    created_by=request.user,
                    notes="Initial stock"
                )
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Added new product: {product.name}",
                date=timezone.now(),
                content_type='product',
                object_id=product.id
            )
            
            messages.success(request, f"Successfully added new product: {product.name}")
            return redirect('product_detail', pk=product.id)
            
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
            return redirect('add_product')
    
    # GET request - show form
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    
    context = {
        'categories': categories,
        'suppliers': suppliers
    }
    
    return render(request, 'add_product.html', context)

@login_required
@permission_required('main_app.change_product')
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        reorder_level = int(request.POST.get('reorder_level', 5))
        category_id = request.POST.get('category')
        supplier_ids = request.POST.getlist('suppliers')
        image = request.FILES.get('image')
        
        try:
            category = Category.objects.get(id=category_id)
            
            # Update product
            product.name = name
            product.sku = sku
            product.description = description
            product.price = price
            product.reorder_level = reorder_level
            product.category = category
            
            if image:
                product.image = image
            
            product.save()
            
            # Update suppliers
            product.suppliers.clear()
            if supplier_ids:
                suppliers = Supplier.objects.filter(id__in=supplier_ids)
                product.suppliers.add(*suppliers)
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Updated product: {product.name}",
                date=timezone.now(),
                content_type='product',
                object_id=product.id
            )
            
            messages.success(request, f"Successfully updated product: {product.name}")
            return redirect('product_detail', pk=product.id)
            
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
            return redirect('edit_product', pk=pk)
    
    # GET request - show form with product data
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    
    context = {
        'product': product,
        'categories': categories,
        'suppliers': suppliers,
        'selected_suppliers': [s.id for s in product.suppliers.all()]
    }
    
    return render(request, 'edit_product.html', context)

# ===== Categories =====
@login_required
def categories(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        # Create new category
        category = Category.objects.create(
            name=name,
            description=description
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Added new category: {category.name}",
            date=timezone.now(),
            content_type='category',
            object_id=category.id
        )
        
        messages.success(request, f"Successfully added new category: {category.name}")
        return redirect('categories')
    
    # GET request - show categories
    all_categories = Category.objects.annotate(product_count=Count('products'))
    
    context = {
        'categories': all_categories
    }
    
    return render(request, 'categories.html', context)

# ===== Suppliers =====
@login_required
def suppliers(request):
    all_suppliers = Supplier.objects.all()
    
    context = {
        'suppliers': all_suppliers
    }
    
    return render(request, 'suppliers.html', context)

@login_required
@permission_required('main_app.add_supplier')
def add_supplier(request):
    """Add a new supplier"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        contact_name = request.POST.get('contact_name')
        
        # Create supplier
        supplier = Supplier.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            contact_info=contact_name
        )
        
        # Create notification for new supplier
        notify_supplier_update(supplier, is_new=True, user=request.user)
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Added new supplier: {name}"
        )
        
        messages.success(request, f"Supplier {name} added successfully!")
        return redirect('suppliers')
    
    return render(request, 'add_supplier.html')

# ===== Stock In/Out =====
@login_required
def stock_transaction(request):
    """Combined view for both stock in and stock out transactions."""
    if request.method == 'POST':
        transaction_type = request.POST.get('transaction_type')
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        reference = request.POST.get('reference', '')
        notes = request.POST.get('notes', '')
        date = request.POST.get('date', timezone.now())
        
        try:
            product = Product.objects.get(id=product_id)
            supplier = None
            customer = None
            reason = 'purchase'
            unit_price = product.price
            
            # Process based on transaction type
            if transaction_type == 'IN':
                supplier_id = request.POST.get('supplier')
                unit_price = request.POST.get('unit_price', product.price)
                reason = request.POST.get('reason', 'purchase')
                
                if supplier_id:
                    supplier = Supplier.objects.get(id=supplier_id)
                    
            elif transaction_type == 'OUT':
                customer_id = request.POST.get('customer')
                reason = request.POST.get('reason', 'sale')
                
                # Check if there's enough stock
                if product.stock < quantity:
                    messages.error(request, f"Not enough stock for {product.name}. Current stock: {product.stock}")
                    return redirect('stock_transaction')
                
                if customer_id:
                    customer = Customer.objects.get(id=customer_id)
            
            # Create stock transaction
            transaction = StockTransaction.objects.create(
                product=product,
                quantity=quantity,
                transaction_type=transaction_type,
                supplier=supplier,
                customer=customer,
                reason=reason,
                reference=reference,
                unit_price=unit_price,
                notes=notes,
                date=date,
                created_by=request.user
            )
            
            # Create notification for stock transaction
            notify_stock_transaction(transaction, request.user)
            
            # Check if stock is below reorder level and notify if it is
            if product.stock <= product.reorder_level:
                notify_low_stock(product)
            
            # Log activity
            action_text = "Added" if transaction_type == 'IN' else "Removed"
            ActivityLog.objects.create(
                user=request.user,
                action=f"{action_text} {quantity} units of {product.name} {'to' if transaction_type == 'IN' else 'from'} inventory",
                date=timezone.now(),
                content_type='stocktransaction',
                object_id=transaction.id
            )
            
            messages.success(request, f"Successfully {action_text.lower()} {quantity} units of {product.name} {'to' if transaction_type == 'IN' else 'from'} inventory.")
            return redirect('stock_transaction')
            
        except Product.DoesNotExist:
            messages.error(request, "Product not found.")
        except Supplier.DoesNotExist:
            messages.error(request, "Supplier not found.")
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
        
        return redirect('stock_transaction')
    
    # GET request - show form and records for both types
    transactions = StockTransaction.objects.select_related(
        'product', 'supplier', 'customer'
    ).order_by('-date')[:20]  # Show the 20 most recent transactions
    
    products = Product.objects.all()
    suppliers = Supplier.objects.all()
    customers = Customer.objects.all()
    
    context = {
        'transactions': transactions,
        'products': products,
        'suppliers': suppliers,
        'customers': customers,
        'today': timezone.now().strftime('%Y-%m-%d')
    }
    
    return render(request, 'stock.html', context)

@login_required
def stock_in(request):
    if request.method == 'POST':
        # Redirect POST requests to the combined view with 'IN' type
        return stock_transaction(request)
    
    # GET request - redirect to the combined view with the 'in' tab active
    return redirect('stock_transaction')

@login_required
def stock_out(request):
    if request.method == 'POST':
        # Redirect POST requests to the combined view with 'OUT' type
        return stock_transaction(request)
    
    # GET request - redirect to the combined view with the 'out' tab active
    return redirect('stock_transaction')

# ===== Inventory Transactions =====
@login_required
def transaction_list(request):
    transaction_type = request.GET.get('type', '')
    product_id = request.GET.get('product', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    transactions = StockTransaction.objects.select_related('product', 'supplier', 'customer').order_by('-date')
    
    # Apply filters
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)
    
    # For filters
    products = Product.objects.all()
    
    context = {
        'transactions': transactions_page,
        'products': products,
        'filters': {
            'transaction_type': transaction_type,
            'product_id': product_id,
            'start_date': start_date,
            'end_date': end_date
        }
    }
    
    return render(request, 'transactions.html', context)

@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(StockTransaction, pk=pk)
    
    context = {
        'transaction': transaction
    }
    
    return render(request, 'transaction_detail.html', context)

@login_required
@permission_required('main_app.delete_stocktransaction')
def transaction_delete(request, pk):
    transaction = get_object_or_404(StockTransaction, pk=pk)
    
    if request.method == 'POST':
        # Store info for success message
        product_name = transaction.product.name
        quantity = transaction.quantity
        transaction_type = transaction.get_transaction_type_display()
        
        # Reverse the inventory adjustment
        if transaction.transaction_type == 'IN':
            transaction.product.stock -= transaction.quantity
        else:  # OUT
            transaction.product.stock += transaction.quantity
        
        transaction.product.save()
        
        # Delete the transaction
        transaction.delete()
        
        messages.success(
            request, 
            f"Successfully deleted {transaction_type} transaction of {quantity} units of {product_name}."
        )
        return redirect('transactions')
    
    # For GET requests, confirm deletion via the template
    return render(request, 'transaction_delete_confirm.html', {'transaction': transaction})

# ===== Orders =====
@login_required
def order(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        notes = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        
        try:
            customer = Customer.objects.get(id=customer_id)
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                status='pending',
                notes=notes,
                created_by=request.user
            )
            
            # Process order items
            for i in range(len(product_ids)):
                if i < len(quantities) and i < len(prices):  # Make sure we have matching data
                    try:
                        product = Product.objects.get(id=product_ids[i])
                        quantity = int(quantities[i])
                        price = float(prices[i])
                        
                        # Skip items with zero quantity
                        if quantity <= 0:
                            continue
                            
                        # Create order item
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price=price
                        )
                        
                        # Create stock transaction for this order item
                        StockTransaction.objects.create(
                            product=product,
                            quantity=quantity,
                            transaction_type='OUT',
                            reference=f"Order #{order.id}",
                            notes=f"Order for {customer.name if customer else 'Walk-in Customer'}",
                            customer=customer,
                            created_by=request.user
                        )
                        
                        # Update product stock
                        product.stock -= quantity
                        product.save()
                        
                        # Check if product is now low on stock
                        if product.stock <= product.reorder_level:
                            notify_low_stock(product)
                    except Product.DoesNotExist:
                        messages.error(request, f"Product with ID {product_ids[i]} not found.")
            
            # Create notification for new order
            notify_new_order(order, request.user)
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created new order #{order.id}"
            )
            
            messages.success(request, f"Order #{order.id} created successfully!")
            return redirect('order_detail', pk=order.id)
            
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
            return redirect('orders')
    
    # GET request - show orders and order form
    all_orders = Order.objects.select_related('customer').order_by('-order_date')
    
    # Pagination
    paginator = Paginator(all_orders, 10)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)
    
    available_products = Product.objects.filter(stock__gt=0)
    customers = Customer.objects.all()
    
    context = {
        'orders': orders_page,
        'products': available_products,
        'customers': customers
    }
    
    return render(request, 'orders.html', context)

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order_items = order.items.select_related('product').all()
    
    context = {
        'order': order,
        'order_items': order_items
    }
    
    return render(request, 'order_detail.html', context)

@login_required
@permission_required('main_app.change_order')
def complete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if order.status in ['completed', 'cancelled']:
        messages.error(request, f"Order #{order.id} is already {order.get_status_display()}.")
        return redirect('order_detail', pk=order.id)
    
    # Update status
    order.status = 'completed'
    order.save()
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action=f"Completed order #{order.id}",
        date=timezone.now(),
        content_type='order',
        object_id=order.id
    )
    
    messages.success(request, f"Order #{order.id} has been marked as completed.")
    return redirect('order_detail', pk=order.id)

# ===== Customers =====
@login_required
def customers(request):
    all_customers = Customer.objects.all()
    
    # Pagination
    paginator = Paginator(all_customers, 10)
    page_number = request.GET.get('page')
    customers_page = paginator.get_page(page_number)
    
    context = {
        'customers': customers_page
    }
    
    return render(request, 'customers.html', context)

@login_required
@permission_required('main_app.add_customer')
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_info = request.POST.get('contact_info')
        address = request.POST.get('address', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone')
        
        # Create new customer
        customer = Customer.objects.create(
            name=name,
            contact_info=contact_info,
            address=address,
            email=email,
            phone=phone
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Added new customer: {customer.name}",
            date=timezone.now(),
            content_type='customer',
            object_id=customer.id
        )
        
        messages.success(request, f"Successfully added new customer: {customer.name}")
        return redirect('customers')
    
    return render(request, 'add_customer.html')

# ===== Low Stock Items =====
@login_required
def low_stock_items(request):
    low_stock_products = Product.objects.filter(
        stock__lt=F('reorder_level')
    ).select_related('category')
    
    low_stock_categories = low_stock_products.values_list('category__name', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(low_stock_products, 10)
    page_number = request.GET.get('page')
    low_stock_page = paginator.get_page(page_number)
    
    context = {
        'low_stock_products': low_stock_page,
        'low_stock_categories': low_stock_categories,
        'low_stock_count': low_stock_products.count()
    }
    
    return render(request, 'low_stock_items.html', context)

# ===== Reports =====
@login_required
def reports(request):
    report_type = request.GET.get('type', 'overview')
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    low_stock = request.GET.get('low_stock', 'false').lower() == 'true'
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Overview data for all report types
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    low_stock_count = Product.objects.filter(stock__lte=F('reorder_level')).count()
    
    # Calculate total inventory value
    inventory_value_result = Product.objects.aggregate(
        total_value=Sum(
            ExpressionWrapper(F('stock') * F('price'), output_field=DecimalField())
        )
    )
    total_inventory_value = inventory_value_result['total_value'] or 0
    
    # Calculate total sales
    completed_orders = Order.objects.filter(status='completed')
    total_sales = sum(order.total_amount for order in completed_orders) if completed_orders.exists() else 0
    
    # Get category data for charts
    categories = Category.objects.annotate(
        product_count=Count('products'),
        value=Sum(
            ExpressionWrapper(
                F('products__stock') * F('products__price'),
                output_field=DecimalField()
            )
        )
    ).order_by('-value')
    
    # Prepare category chart data
    category_labels = [cat.name for cat in categories[:5]]
    category_values = [float(cat.value or 0) for cat in categories[:5]]
    
    # If there are other categories, add an "Others" category
    if categories.count() > 5:
        other_categories = categories[5:]
        other_value = sum(float(cat.value or 0) for cat in other_categories)
        category_labels.append('Others')
        category_values.append(other_value)
    
    # Sales trend data (last 12 months)
    sales_months = []
    sales_values = []
    
    # Get data for each of the last 12 months
    for i in range(11, -1, -1):
        month_start = timezone.now() - timedelta(days=30 * i + timezone.now().day - 1)
        month_end = month_start.replace(day=1) + timedelta(days=32)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        
        # Get orders for this month
        month_orders = Order.objects.filter(
            status='completed',
            order_date__gte=month_start,
            order_date__lte=month_end
        )
        
        month_total = sum(order.total_amount for order in month_orders)
        sales_months.append(month_start.strftime('%b'))
        sales_values.append(float(month_total))
    
    # Specific report data based on type
    if report_type == 'inventory':
        query = Product.objects.annotate(
            total_value=ExpressionWrapper(F('stock') * F('price'), output_field=DecimalField())
        ).select_related('category')
        
        # Apply low stock filter if requested
        if low_stock:
            query = query.filter(stock__lte=F('reorder_level'))
            
        report_data = query.order_by('-total_value')
        
        # Summary for inventory report
        summary = {
            'total_products': report_data.count(),
            'total_value': sum(p.total_value for p in report_data),
            'low_stock_count': report_data.filter(stock__lt=F('reorder_level')).count(),
            'out_of_stock_count': report_data.filter(stock=0).count()
        }
        
        # Get top products by value
        top_products = report_data.order_by('-total_value')[:10]
        top_product_labels = [p.name for p in top_products]
        top_product_values = [float(p.total_value) for p in top_products]
        
    elif report_type == 'transactions':
        # Filter transactions by date
        report_data = StockTransaction.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        ).select_related('product', 'supplier', 'customer').order_by('-date')
        
        # Summary
        stock_in = report_data.filter(transaction_type='IN')
        stock_out = report_data.filter(transaction_type='OUT')
        
        stock_in_value = sum(t.total_value for t in stock_in)
        stock_out_value = sum(t.total_value for t in stock_out)
        
        summary = {
            'total_transactions': report_data.count(),
            'stock_in_count': stock_in.count(),
            'stock_out_count': stock_out.count(),
            'stock_in_value': stock_in_value,
            'stock_out_value': stock_out_value,
            'net_stock_value': stock_in_value - stock_out_value
        }
        
    elif report_type == 'sales':
        # Filter completed orders
        report_data = Order.objects.filter(
            status='completed',
            order_date__gte=start_date_obj,
            order_date__lte=end_date_obj
        ).select_related('customer').prefetch_related('items__product').order_by('-order_date')
        
        # Summary
        summary = {
            'total_orders': report_data.count(),
            'total_sales': sum(order.total_amount for order in report_data) if report_data.count() > 0 else 0,
            'avg_order_value': sum(order.total_amount for order in report_data) / report_data.count() if report_data.count() > 0 else 0,
            'total_items_sold': sum(item.quantity for order in report_data for item in order.items.all())
        }
        
        # Get top selling products
        top_selling_products = OrderItem.objects.filter(
            order__status='completed',
            order__order_date__gte=start_date_obj,
            order__order_date__lte=end_date_obj
        ).values('product__name').annotate(
            units_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('price'))
        ).order_by('-units_sold')[:5]
        
        top_product_labels = [p['product__name'] for p in top_selling_products]
        top_product_values = [p['units_sold'] for p in top_selling_products]
    
    elif report_type == 'supplier':
        # Get all suppliers with their transaction data
        suppliers = Supplier.objects.all()
        
        # Add metrics to each supplier
        for supplier in suppliers:
            # Count products associated with this supplier
            supplier.product_count = supplier.products.count()
            
            # Calculate total purchase value
            supplier_transactions = StockTransaction.objects.filter(
                supplier=supplier,
                transaction_type='IN',
                date__gte=start_date_obj,
                date__lte=end_date_obj
            )
            
            total_purchases = sum(t.total_value for t in supplier_transactions)
            supplier.total_purchases = total_purchases
            
            # Get last order date
            last_transaction = supplier_transactions.order_by('-date').first()
            supplier.last_order_date = last_transaction.date if last_transaction else None
            
            # Calculate reliability score (example metric)
            on_time_deliveries = supplier_transactions.filter(notes__icontains='on time').count()
            if supplier_transactions.count() > 0:
                supplier.reliability = (on_time_deliveries / supplier_transactions.count()) * 100
            else:
                supplier.reliability = 0
        
        # Sort suppliers by total purchases (descending)
        report_data = sorted(suppliers, key=lambda s: s.total_purchases, reverse=True)
        
        # Prepare chart data
        top_suppliers = report_data[:5] if len(report_data) > 5 else report_data
        supplier_labels = [s.name for s in top_suppliers]
        supplier_volumes = [float(s.total_purchases) for s in top_suppliers]
        supplier_quality = [s.reliability for s in top_suppliers]
        
        # Summary statistics
        active_suppliers = len([s for s in suppliers if s.is_active])
        total_purchases = sum(s.total_purchases for s in suppliers)
        
        summary = {
            'total_suppliers': len(suppliers),
            'active_suppliers': active_suppliers,
            'total_purchases': total_purchases,
            'avg_delivery_days': 3  # Placeholder, would need to calculate from actual delivery data
        }
    
    else:  # overview
        report_data = None
        summary = {
            'total_products': total_products,
            'active_products': active_products,
            'total_inventory_value': total_inventory_value,
            'total_sales': total_sales,
            'low_stock_count': low_stock_count
        }
        supplier_labels = []
        supplier_volumes = []
        supplier_quality = []
    
    # Export to PDF if requested
    if request.GET.get('export') == 'pdf':
        template_name = 'pdf/report.html'
        context = {
            'report_type': report_type,
            'report_data': report_data,
            'summary': summary,
            'start_date': start_date,
            'end_date': end_date,
            'category_labels': category_labels,
            'category_values': category_values,
            'sales_months': sales_months,
            'sales_values': sales_values,
            'top_product_labels': top_product_labels if 'top_product_labels' in locals() else [],
            'top_product_values': top_product_values if 'top_product_values' in locals() else [],
            'supplier_labels': supplier_labels if 'supplier_labels' in locals() else [],
            'supplier_volumes': supplier_volumes if 'supplier_volumes' in locals() else [],
            'supplier_quality': supplier_quality if 'supplier_quality' in locals() else [],
            'generated_on': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        pdf = render_to_pdf(template_name, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"{report_type}_report_{timezone.now().strftime('%Y%m%d')}.pdf"
            content = f"attachment; filename={filename}"
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Error generating PDF", status=400)
        
    # Export to CSV if requested
    elif request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'inventory':
            writer.writerow(['Product', 'SKU', 'Category', 'Supplier', 'Stock', 'Price', 'Total Value'])
            for product in report_data:
                writer.writerow([
                    product.name,
                    product.sku or '',
                    product.category.name,
                    ', '.join(s.name for s in product.suppliers.all()),
                    product.stock,
                    product.price,
                    product.total_value
                ])
                
        elif report_type == 'transactions':
            writer.writerow(['Date', 'Type', 'Product', 'Quantity', 'Price', 'Total', 'Reference'])
            for transaction in report_data:
                writer.writerow([
                    transaction.date.strftime('%Y-%m-%d %H:%M'),
                    transaction.get_transaction_type_display(),
                    transaction.product.name,
                    transaction.quantity,
                    transaction.unit_price or 0,
                    transaction.total_value,
                    transaction.reference or ''
                ])
                
        elif report_type == 'sales':
            writer.writerow(['Order #', 'Date', 'Customer', 'Items', 'Total Amount', 'Status'])
            for order in report_data:
                writer.writerow([
                    order.id,
                    order.order_date.strftime('%Y-%m-%d %H:%M'),
                    order.customer.name,
                    order.item_count,
                    order.total_amount,
                    order.get_status_display()
                ])
                
        elif report_type == 'supplier':
            writer.writerow(['Supplier', 'Products', 'Total Purchases', 'Last Order', 'Status', 'Reliability'])
            for supplier in report_data:
                writer.writerow([
                    supplier.name,
                    supplier.product_count,
                    supplier.total_purchases,
                    supplier.last_order_date.strftime('%Y-%m-%d') if supplier.last_order_date else 'Never',
                    'Active' if supplier.is_active else 'Inactive',
                    f"{supplier.reliability:.1f}%"
                ])
        
        return response
    
    # Pagination for web view
    if report_data:
        paginator = Paginator(report_data, 20)
        page_number = request.GET.get('page')
        report_page = paginator.get_page(page_number)
    else:
        report_page = None
    
    context = {
        'report_type': report_type,
        'report_data': report_page,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
        'total_products': total_products,
        'active_products': active_products,
        'total_inventory_value': total_inventory_value,
        'total_sales': total_sales,
        'low_stock_count': low_stock_count,
        'low_stock': low_stock,
        'category_labels': json.dumps(category_labels),
        'category_values': json.dumps(category_values),
        'sales_months': json.dumps(sales_months),
        'sales_values': json.dumps(sales_values),
        'top_product_labels': json.dumps(top_product_labels) if 'top_product_labels' in locals() else json.dumps([]),
        'top_product_values': json.dumps(top_product_values) if 'top_product_values' in locals() else json.dumps([]),
        'supplier_labels': json.dumps(supplier_labels) if 'supplier_labels' in locals() else json.dumps([]),
        'supplier_volumes': json.dumps(supplier_volumes) if 'supplier_volumes' in locals() else json.dumps([]),
        'supplier_quality': json.dumps(supplier_quality) if 'supplier_quality' in locals() else json.dumps([]),
    }
    
    return render(request, 'report.html', context)

# ===== Profile =====
@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Basic user info
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        
        # Profile info
        user_profile.bio = request.POST.get('bio', user_profile.bio)
        user_profile.location = request.POST.get('location', user_profile.location)
        
        # Profile picture
        if 'profile_picture' in request.FILES:
            user_profile.profile_picture = request.FILES['profile_picture']
        
        user_profile.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')
    
    # Recent activity
    recent_activity = ActivityLog.objects.filter(user=request.user).order_by('-date')[:10]
    
    context = {
        'user_profile': user_profile,
        'recent_activity': recent_activity
    }
    
    return render(request, 'profile.html', context)

# ===== Other =====
@login_required
def add_notification(request):
    return render(request, 'add_notification.html')

@login_required
def top_categories(request):
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:10]
    
    context = {
        'categories': categories
    }
    
    return render(request, 'top_categories.html', context)

@login_required
def recent_activity(request):
    activities = ActivityLog.objects.order_by('-date')
    
    # Pagination
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    activities_page = paginator.get_page(page_number)
    
    context = {
        'activities': activities_page
    }
    
    return render(request, 'recent_activity.html', context)

# ===== API Endpoints for Ajax =====
@login_required
def get_product_info(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': product.stock,
            'category': product.category.name,
            'suppliers': [{'id': s.id, 'name': s.name} for s in product.suppliers.all()]
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

# ===== User Management =====
@login_required
@permission_required('auth.view_user')
def users(request):
    """View for admins to manage users"""
    from django.contrib.auth.models import User
    
    # Get all users
    users_list = User.objects.all().order_by('-date_joined')
    
    # Filter by search query if provided
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Ensure all users have profiles
    for user in users_list:
        UserProfile.objects.get_or_create(user=user)
    
    # Pagination
    paginator = Paginator(users_list, 15)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    # Count user stats
    staff_count = User.objects.filter(is_staff=True).count()
    admin_count = User.objects.filter(is_superuser=True).count()
    active_count = User.objects.filter(is_active=True).count()
    
    context = {
        'users': users_page,
        'staff_count': staff_count,
        'admin_count': admin_count,
        'active_count': active_count,
        'total_count': User.objects.count(),
        'search_query': search_query
    }
    
    return render(request, 'users.html', context)

@login_required
@permission_required('auth.view_user')
def users_pdf_report(request):
    """Generate a PDF report of users"""
    from django.contrib.auth.models import User
    
    # Get parameters from the request
    search_query = request.GET.get('search', '')
    
    # Get all users
    users_list = User.objects.all().order_by('-date_joined')
    
    # Apply search filter if provided
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Ensure all users have profiles
    for user in users_list:
        UserProfile.objects.get_or_create(user=user)
    
    # Count user stats
    staff_count = User.objects.filter(is_staff=True).count()
    admin_count = User.objects.filter(is_superuser=True).count()
    active_count = User.objects.filter(is_active=True).count()
    
    # Context for the PDF template
    context = {
        'users': users_list,
        'staff_count': staff_count,
        'admin_count': admin_count,
        'active_count': active_count,
        'total_count': User.objects.count(),
        'search_query': search_query,
        'now': timezone.now().strftime('%B %d, %Y at %I:%M %p')
    }
    
    # Generate PDF
    pdf = render_to_pdf('pdf/users_report.html', context)
    
    # Return PDF response with appropriate filename
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"users_report_{timezone.now().strftime('%Y%m%d')}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    # If PDF generation failed
    return HttpResponse("Error generating PDF", status=400)

# ===== Notifications =====
@login_required
def notifications(request):
    """View all notifications"""
    user_notifications = Notification.objects.filter(recipient=request.user)
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        user_notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications')
    
    # Pagination
    paginator = Paginator(user_notifications, 20)  # Show 20 notifications per page
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)
    
    context = {
        'notifications': notifications_page,
    }
    
    return render(request, 'notifications.html', context)

@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        
        # If notification has a link and this is not an AJAX request, redirect to it
        if notification.link and not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return redirect(notification.link)
        
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

@login_required
def delete_notification(request, pk):
    """Delete a notification"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.delete()
        messages.success(request, "Notification deleted successfully.")
        return redirect('notifications')
    except Notification.DoesNotExist:
        messages.error(request, "Notification not found.")
        return redirect('notifications')

@login_required
def get_unread_notification_count(request):
    """Get the number of unread notifications (for AJAX calls)"""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})

# Context processor for notifications
def notifications_processor(request):
    """Context processor to add notification data to all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
        return {
            'unread_notification_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }

@login_required
def new_order(request):
    """View specifically for creating new orders"""
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        notes = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        
        try:
            customer = Customer.objects.get(id=customer_id)
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                status='pending',
                notes=notes,
                created_by=request.user
            )
            
            # Process order items
            for i in range(len(product_ids)):
                if i < len(quantities) and i < len(prices):  # Make sure we have matching data
                    try:
                        product = Product.objects.get(id=product_ids[i])
                        quantity = int(quantities[i])
                        price = float(prices[i])
                        
                        # Skip items with zero quantity
                        if quantity <= 0:
                            continue
                            
                        # Create order item
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price=price
                        )
                        
                        # Create stock transaction for this order item
                        StockTransaction.objects.create(
                            product=product,
                            quantity=quantity,
                            transaction_type='OUT',
                            reference=f"Order #{order.id}",
                            notes=f"Order for {customer.name if customer else 'Walk-in Customer'}",
                            customer=customer,
                            created_by=request.user
                        )
                        
                        # Update product stock
                        product.stock -= quantity
                        product.save()
                        
                        # Check if product is now low on stock
                        if product.stock <= product.reorder_level:
                            notify_low_stock(product)
                    except Product.DoesNotExist:
                        messages.error(request, f"Product with ID {product_ids[i]} not found.")
            
            # Create notification for new order
            notify_new_order(order, request.user)
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created new order #{order.id}"
            )
            
            messages.success(request, f"Order #{order.id} created successfully!")
            return redirect('order_detail', pk=order.id)
            
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
            return redirect('new_order')
    
    # GET request - show the form for creating a new order
    available_products = Product.objects.filter(stock__gt=0)
    customers = Customer.objects.all()
    
    context = {
        'products': available_products,
        'customers': customers
    }
    
    return render(request, 'new_order.html', context)

def register(request):
    """View for user registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create a UserProfile for the new user
            UserProfile.objects.create(user=user)
            
            # Log activity
            ActivityLog.objects.create(
                user=user,
                action=f"New user registered: {user.username}",
                date=timezone.now(),
                content_type='user',
                object_id=user.id
            )
            
            # Auto-login the user after registration
            login(request, user)
            
            messages.success(request, f"Account created successfully! Welcome, {user.username}!")
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})

@login_required
def product_forecast_view(request, product_id):
    """View for displaying product demand forecasts - redirects to forecast app"""
    from django.shortcuts import redirect
    
    # Get the referer to prevent redirect loops
    referer = request.META.get('HTTP_REFERER', '')
    if 'forecast' in referer:
        # We're already in the forecast app, don't redirect again
        from django.http import Http404
        raise Http404("This URL should be handled by the forecast app")
        
    return redirect('forecast:product_forecast', product_id=product_id)

# ===== Customer Portal =====
def customer_portal_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        try:
            # Find customer by email and phone
            customer = Customer.objects.get(email=email, phone=phone)
            
            # Store customer ID in session
            request.session['customer_id'] = customer.id
            request.session['customer_name'] = customer.name
            
            messages.success(request, f"Welcome back, {customer.name}!")
            return redirect('customer_portal_home')
            
        except Customer.DoesNotExist:
            messages.error(request, "No customer found with that email and phone number.")
    
    return render(request, 'customer_portal/login.html')

def customer_portal_logout(request):
    # Clear customer session data
    if 'customer_id' in request.session:
        del request.session['customer_id']
    if 'customer_name' in request.session:
        del request.session['customer_name']
    
    messages.success(request, "You have been logged out successfully.")
    return redirect('customer_portal_login')

def customer_portal_required(view_func):
    """Decorator to check if customer is logged into the portal"""
    def wrapped(request, *args, **kwargs):
        if 'customer_id' not in request.session:
            messages.warning(request, "Please log in to access the customer portal.")
            return redirect('customer_portal_login')
        return view_func(request, *args, **kwargs)
    return wrapped

@customer_portal_required
def customer_portal_home(request):
    customer_id = request.session['customer_id']
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get recent orders
    recent_orders = CustomerPortalOrder.objects.filter(customer=customer).order_by('-order_date')[:5]
    
    # Get featured/recommended products
    featured_products = Product.objects.filter(is_active=True, stock__gt=0).order_by('?')[:6]
    
    context = {
        'customer': customer,
        'recent_orders': recent_orders,
        'featured_products': featured_products,
    }
    
    return render(request, 'customer_portal/home.html', context)

@customer_portal_required
def customer_portal_products(request):
    # Get filters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with all active products with stock
    products = Product.objects.filter(is_active=True, stock__gt=0)
    
    # Apply filters
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # default to name
        products = products.order_by('name')
    
    # Get all categories for filter dropdown
    categories = Category.objects.all()
    
    # Paginate results
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    context = {
        'products': products_page,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'sort_by': sort_by,
    }
    
    return render(request, 'customer_portal/products.html', context)

@customer_portal_required
def customer_portal_product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    # Get related products in the same category
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id).order_by('?')[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    
    return render(request, 'customer_portal/product_detail.html', context)

@customer_portal_required
def customer_portal_cart(request):
    # Initialize cart if it doesn't exist in session
    if 'cart' not in request.session:
        request.session['cart'] = {}
    
    cart = request.session['cart']
    cart_items = []
    total = 0
    
    # Process cart items
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            subtotal = float(product.price) * int(quantity)
            total += subtotal
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except Product.DoesNotExist:
            # Remove invalid product from cart
            del cart[product_id]
            request.session.modified = True
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': len(cart_items)
    }
    
    return render(request, 'customer_portal/cart.html', context)

@customer_portal_required
def customer_portal_add_to_cart(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        
        # Check if there's enough stock
        if product.stock < quantity:
            messages.error(request, f"Sorry, only {product.stock} units available for {product.name}.")
            return redirect('customer_portal_product_detail', pk=pk)
        
        # Initialize cart if it doesn't exist
        if 'cart' not in request.session:
            request.session['cart'] = {}
        
        # Update cart
        cart = request.session['cart']
        product_id = str(product.id)
        
        if product_id in cart:
            # Update quantity if product already in cart
            cart[product_id] = int(cart[product_id]) + quantity
        else:
            # Add new product to cart
            cart[product_id] = quantity
        
        # Mark session as modified
        request.session.modified = True
        
        messages.success(request, f"Added {quantity} {product.name} to your cart.")
        
        # Redirect based on source
        next_page = request.POST.get('next', 'customer_portal_cart')
        return redirect(next_page)
    
    return redirect('customer_portal_products')

@customer_portal_required
def customer_portal_update_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        
        if 'cart' not in request.session:
            request.session['cart'] = {}
        
        cart = request.session['cart']
        
        if action == 'remove' and product_id in cart:
            # Remove item from cart
            del cart[product_id]
            request.session.modified = True
            messages.success(request, "Item removed from cart.")
        
        elif action == 'update' and product_id in cart:
            # Update quantity
            quantity = int(request.POST.get('quantity', 1))
            
            # Validate quantity against stock
            try:
                product = Product.objects.get(id=product_id)
                if quantity > product.stock:
                    messages.error(request, f"Only {product.stock} units available.")
                    quantity = product.stock
                
                if quantity > 0:
                    cart[product_id] = quantity
                    messages.success(request, "Cart updated successfully.")
                else:
                    del cart[product_id]
                    messages.success(request, "Item removed from cart.")
                
                request.session.modified = True
            except Product.DoesNotExist:
                del cart[product_id]
                request.session.modified = True
    
    return redirect('customer_portal_cart')

@customer_portal_required
def customer_portal_checkout(request):
    customer_id = request.session['customer_id']
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Check if cart is empty
    if 'cart' not in request.session or not request.session['cart']:
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('customer_portal_products')
    
    if request.method == 'POST':
        # Create order
        shipping_address = request.POST.get('shipping_address')
        contact_phone = request.POST.get('contact_phone')
        notes = request.POST.get('notes', '')
        payment_method = request.POST.get('payment_method', 'Credit Card')
        
        # Validate inputs
        if not shipping_address or not contact_phone:
            messages.error(request, "Please provide shipping address and contact phone.")
            return redirect('customer_portal_checkout')
        
        # Create order
        order = CustomerPortalOrder.objects.create(
            customer=customer,
            shipping_address=shipping_address,
            contact_phone=contact_phone,
            notes=notes,
            payment_method=payment_method,
            payment_status='completed'  # In a real system, this would be handled by payment gateway
        )
        
        # Process cart items
        cart = request.session['cart']
        order_items = []
        stock_transactions = []
        
        for product_id, quantity in cart.items():
            try:
                product = Product.objects.get(id=product_id)
                
                # Final stock check
                if product.stock < int(quantity):
                    messages.error(request, f"Sorry, only {product.stock} units available for {product.name}.")
                    order.delete()  # Rollback order creation
                    return redirect('customer_portal_cart')
                
                # Create order item
                order_item = CustomerPortalOrderItem(
                    order=order,
                    product=product,
                    quantity=int(quantity),
                    price=product.price
                )
                order_items.append(order_item)
                
                # Create stock transaction (will be processed later)
                stock_transaction = StockTransaction(
                    product=product,
                    quantity=int(quantity),
                    transaction_type='OUT',
                    reason='sale',
                    reference=f"Portal Order #{order.id}",
                    customer=customer,
                    notes=f"Online order by {customer.name}"
                )
                stock_transactions.append(stock_transaction)
                
            except Product.DoesNotExist:
                continue
        
        # Bulk create order items
        CustomerPortalOrderItem.objects.bulk_create(order_items)
        
        # Process stock transactions
        for transaction in stock_transactions:
            transaction.save()
        
        # Update order total
        order.update_total()
        
        # Create internal order and link it to the portal order
        internal_order = Order.objects.create(
            customer=customer,
            status='pending',
            notes=f"Online order via customer portal. Shipping to: {shipping_address}",
            created_by=None  # No internal user created this
        )
        
        # Link the portal order with the internal order
        order.internal_order = internal_order
        order.save()
        
        # Copy items to internal order
        for item in order_items:
            OrderItem.objects.create(
                order=internal_order,
                product=item.product,
                quantity=item.quantity,
                price=item.price
            )
        
        # Create notification for new order
        notify_new_order(internal_order, None)
        
        # Clear cart
        del request.session['cart']
        request.session.modified = True
        
        # Redirect to confirmation page
        messages.success(request, "Your order has been placed successfully!")
        return redirect('customer_portal_order_confirmation', order_id=order.id)
    
    # For GET requests, prepare checkout form
    cart = request.session['cart']
    cart_items = []
    total = 0
    
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            subtotal = float(product.price) * int(quantity)
            total += subtotal
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except Product.DoesNotExist:
            del cart[product_id]
            request.session.modified = True
    
    context = {
        'customer': customer,
        'cart_items': cart_items,
        'total': total,
        'cart_count': len(cart_items)
    }
    
    return render(request, 'customer_portal/checkout.html', context)

@customer_portal_required
def customer_portal_order_confirmation(request, order_id):
    customer_id = request.session['customer_id']
    order = get_object_or_404(CustomerPortalOrder, id=order_id, customer_id=customer_id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'customer_portal/order_confirmation.html', context)

@customer_portal_required
def customer_portal_orders(request):
    customer_id = request.session['customer_id']
    orders = CustomerPortalOrder.objects.filter(customer_id=customer_id).order_by('-order_date')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    context = {
        'orders': orders_page,
    }
    
    return render(request, 'customer_portal/order.html', context)

@customer_portal_required
def customer_portal_order_detail(request, order_id):
    customer_id = request.session['customer_id']
    order = get_object_or_404(CustomerPortalOrder, id=order_id, customer_id=customer_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cancel_order' and order.status in ['pending', 'processing']:
            order.update_status('cancelled')
            messages.success(request, 'Order has been cancelled successfully.')
            return redirect('customer_portal_orders')
        
        if action == 'update_status' and request.user.is_staff:
            new_status = request.POST.get('status')
            if new_status:
                try:
                    order.update_status(new_status)
                    messages.success(request, f'Order status updated to {order.get_status_display()}.')
                except ValueError as e:
                    messages.error(request, str(e))
            
            # If tracking number is provided, update it
            tracking_number = request.POST.get('tracking_number')
            if tracking_number:
                order.tracking_number = tracking_number
                order.save()
                messages.success(request, 'Tracking number has been updated.')
    
    context = {
        'order': order,
    }
    
    return render(request, 'customer_portal/orders_details.html', context)



