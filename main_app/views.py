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
import csv
from datetime import datetime, timedelta
import json

from .models import (
    Product, StockTransaction, StockIn, StockOut, Supplier, 
    Category, ActivityLog, LowStockAlert, Order, OrderItem, 
    Customer, Report, UserProfile
)

# Import the render_to_pdf function from utils
from .utils import render_to_pdf

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
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_info = request.POST.get('contact_info')
        address = request.POST.get('address')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        # Create new supplier
        supplier = Supplier.objects.create(
            name=name,
            contact_info=contact_info,
            address=address,
            email=email,
            phone=phone
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Added new supplier: {supplier.name}",
            date=timezone.now(),
            content_type='supplier',
            object_id=supplier.id
        )
        
        messages.success(request, f"Successfully added new supplier: {supplier.name}")
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
                notes=notes,
                created_by=request.user
            )
            
            # Create order items
            total_amount = 0
            
            for i in range(len(product_ids)):
                product = Product.objects.get(id=product_ids[i])
                quantity = int(quantities[i])
                price = float(prices[i])
                
                # Check stock
                if product.stock < quantity:
                    messages.warning(request, f"Insufficient stock for {product.name}. Order created but item stock will be negative.")
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price
                )
                
                total_amount += quantity * price
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created order #{order.id} for {customer.name} worth ${total_amount:.2f}",
                date=timezone.now(),
                content_type='order',
                object_id=order.id
            )
            
            messages.success(request, f"Successfully created order #{order.id} for {customer.name}")
            return redirect('order_detail', pk=order.id)
            
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
            return redirect('orders')
        except Product.DoesNotExist:
            messages.error(request, "One or more products not found.")
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
    report_type = request.GET.get('type', 'inventory')
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    
    # Prepare report data
    if report_type == 'inventory':
        report_data = Product.objects.annotate(
            total_value=ExpressionWrapper(F('stock') * F('price'), output_field=DecimalField())
        ).select_related('category').order_by('-total_value')
        
        # Summary
        summary = {
            'total_products': report_data.count(),
            'total_value': sum(p.total_value for p in report_data),
            'low_stock_count': report_data.filter(stock__lt=F('reorder_level')).count(),
            'out_of_stock_count': report_data.filter(stock=0).count()
        }
        
    elif report_type == 'transactions':
        # Filter transactions by date
        report_data = StockTransaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('product', 'supplier', 'customer').order_by('-date')
        
        # Summary
        stock_in = report_data.filter(transaction_type='IN')
        stock_out = report_data.filter(transaction_type='OUT')
        
        summary = {
            'total_transactions': report_data.count(),
            'stock_in_count': stock_in.count(),
            'stock_out_count': stock_out.count(),
            'stock_in_value': sum(t.total_value for t in stock_in),
            'stock_out_value': sum(t.total_value for t in stock_out)
        }
        
    elif report_type == 'sales':
        # Filter completed orders
        report_data = Order.objects.filter(
            status='completed',
            order_date__gte=start_date,
            order_date__lte=end_date
        ).select_related('customer').prefetch_related('items__product').order_by('-order_date')
        
        # Summary
        summary = {
            'total_orders': report_data.count(),
            'total_sales': sum(order.total_amount for order in report_data),
            'avg_order_value': sum(order.total_amount for order in report_data) / report_data.count() if report_data.count() > 0 else 0,
            'total_items_sold': sum(item.quantity for order in report_data for item in order.items.all())
        }
    
    # Export to CSV if requested
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'inventory':
            writer.writerow(['Product', 'SKU', 'Category', 'Supplier', 'Stock', 'Price', 'Total Value'])
            for product in report_data:
                writer.writerow([
                    product.name,
                    product.sku,
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
                    transaction.unit_price,
                    transaction.total_value,
                    transaction.reference
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
        
        return response
    
    # Pagination for web view
    paginator = Paginator(report_data, 20)
    page_number = request.GET.get('page')
    report_page = paginator.get_page(page_number)
    
    context = {
        'report_type': report_type,
        'report_data': report_page,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
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



