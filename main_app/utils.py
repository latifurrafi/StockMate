from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
import os
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict={}):
    """
    Generate a PDF from an HTML template and context data
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    
    # Create PDF
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("UTF-8")), 
        result,
        encoding='UTF-8',
        link_callback=fetch_resources
    )
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def fetch_resources(uri, rel):
    """
    Callback to handle resource files (CSS, images) for the PDF generation
    """
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    else:
        path = os.path.join(settings.STATIC_ROOT, uri)
    
    return path 

def create_notification(recipient, notification_type, title, message, link=None):
    """
    Create a notification for a user
    """
    from main_app.models import Notification
    
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    return notification

def notify_low_stock(product):
    """
    Create low stock notifications for all staff users
    """
    from django.contrib.auth.models import User
    
    title = f"Low Stock Alert: {product.name}"
    message = f"The stock level for {product.name} has fallen below the reorder level ({product.stock}/{product.reorder_level})."
    link = f"/products/{product.id}/"
    
    # Notify all staff users
    for user in User.objects.filter(is_staff=True):
        create_notification(user, 'low_stock', title, message, link)

def notify_new_order(order, user=None):
    """
    Create notifications for a new order
    """
    from django.contrib.auth.models import User, Group
    
    title = f"New Order #{order.id}"
    message = f"A new order has been placed for customer {order.customer.name if order.customer else 'N/A'}."
    link = f"/orders/{order.id}/"
    
    # Notify all staff users
    sales_staff = User.objects.filter(groups__name='Sales Staff')
    admin_users = User.objects.filter(is_staff=True)
    
    for user in set(list(sales_staff) + list(admin_users)):
        create_notification(user, 'new_order', title, message, link)

def notify_stock_transaction(transaction, user):
    """
    Create notifications for stock transactions
    """
    from django.contrib.auth.models import User, Group
    
    action = "added to" if transaction.transaction_type == "IN" else "removed from"
    title = f"Stock {action.title()} Inventory"
    message = f"{user.username} {action} inventory: {transaction.quantity} units of {transaction.product.name}"
    link = f"/transactions/{transaction.id}/"
    
    # Notify all inventory managers and admins
    inventory_managers = User.objects.filter(groups__name='Inventory Manager')
    admin_users = User.objects.filter(is_staff=True)
    
    for recipient in set(list(inventory_managers) + list(admin_users)):
        if recipient != user:  # Don't notify the user who made the transaction
            create_notification(recipient, f"stock_{transaction.transaction_type.lower()}", title, message, link)

def notify_supplier_update(supplier, is_new=False, user=None):
    """
    Create notifications for supplier updates
    """
    from django.contrib.auth.models import User
    
    action = "Added" if is_new else "Updated"
    title = f"Supplier {action}: {supplier.name}"
    message = f"Supplier {supplier.name} has been {action.lower()}."
    link = f"/suppliers/{supplier.id}/"
    
    # Notify all admin users
    for recipient in User.objects.filter(is_staff=True):
        if user is None or recipient != user:
            create_notification(recipient, 'supplier', title, message, link) 