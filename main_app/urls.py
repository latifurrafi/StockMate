from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', views.register, name='register'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/pdf-report/', views.dashboard_pdf_report, name='dashboard_pdf_report'),
    
    # Products
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/forecast/', views.product_forecast_view, name='product_forecast'),
    path('api/products/<int:product_id>/info/', views.get_product_info, name='get_product_info'),
    
    # Categories
    path('categories/', views.categories, name='categories'),
    
    # Suppliers
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    
    # Customers
    path('customers/', views.customers, name='customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    
    # Inventory
    path('stock/', views.stock_transaction, name='stock_transaction'),
    path('stock/in/', views.stock_in, name='stock_in'),
    path('stock/out/', views.stock_out, name='stock_out'),
    path('transactions/', views.transaction_list, name='transactions'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('low-stock-items/', views.low_stock_items, name='low_stock_items'),
    
    # Orders
    path('orders/', views.order, name='order'),
    path('orders/new/', views.new_order, name='new_order'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/complete/', views.complete_order, name='complete_order'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/top-categories/', views.top_categories, name='top_categories'),
    
    # User
    path('profile/', views.profile, name='profile'),
    path('users/', views.users, name='users'),
    path('users/pdf-report/', views.users_pdf_report, name='users_pdf_report'),
    
    # Activity
    path('activity/', views.recent_activity, name='recent_activity'),
    path('notifications/add/', views.add_notification, name='add_notification'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/delete/<int:pk>/', views.delete_notification, name='delete_notification'),
    path('api/notifications/unread-count/', views.get_unread_notification_count, name='get_unread_notification_count'),
]

# Customer Portal URLs
urlpatterns += [
    path('portal/', views.customer_portal_login, name='customer_portal_login'),
    path('portal/logout/', views.customer_portal_logout, name='customer_portal_logout'),
    path('portal/home/', views.customer_portal_home, name='customer_portal_home'),
    path('portal/products/', views.customer_portal_products, name='customer_portal_products'),
    path('portal/products/<int:pk>/', views.customer_portal_product_detail, name='customer_portal_product_detail'),
    path('portal/cart/', views.customer_portal_cart, name='customer_portal_cart'),
    path('portal/add-to-cart/<int:pk>/', views.customer_portal_add_to_cart, name='customer_portal_add_to_cart'),
    path('portal/update-cart/', views.customer_portal_update_cart, name='customer_portal_update_cart'),
    path('portal/checkout/', views.customer_portal_checkout, name='customer_portal_checkout'),
    path('portal/order-confirmation/<int:order_id>/', views.customer_portal_order_confirmation, name='customer_portal_order_confirmation'),
    path('portal/orders/', views.customer_portal_orders, name='customer_portal_orders'),
    path('portal/orders/<int:order_id>/', views.customer_portal_order_detail, name='customer_portal_order_detail'),
]