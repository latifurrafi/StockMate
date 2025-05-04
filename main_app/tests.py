from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from main_app.models import Product, Category, StockTransaction, Supplier

class StockTransactionTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category'
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=100.00,
            stock=50,
            category=self.category
        )
        
        # Create test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            contact_info='Test Contact',
            address='Test Address',
            email='test@example.com',
            phone='123-456-7890'
        )
        
        # Login the test client
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
    
    def test_stock_transaction_page_load(self):
        """Test that stock transaction page loads properly"""
        response = self.client.get(reverse('stock_transaction'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stock.html')
    
    def test_stock_in_transaction(self):
        """Test that stock in transaction works properly"""
        initial_stock = self.product.stock
        
        # Create a stock in transaction
        response = self.client.post(reverse('stock_in'), {
            'transaction_type': 'IN',
            'product': self.product.id,
            'supplier': self.supplier.id,
            'quantity': 10,
            'unit_price': 90.00,
            'date': '2023-04-01',
            'reference': 'TEST-REF-001',
            'notes': 'Test stock in transaction'
        })
        
        # Check redirect
        self.assertRedirects(response, reverse('stock_transaction'))
        
        # Check stock has increased
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + 10)
        
        # Check transaction record was created
        transactions = StockTransaction.objects.filter(product=self.product)
        self.assertEqual(transactions.count(), 1)
        transaction = transactions.first()
        self.assertEqual(transaction.transaction_type, 'IN')
        self.assertEqual(transaction.quantity, 10)
        self.assertEqual(transaction.supplier, self.supplier)
    
    def test_stock_out_transaction(self):
        """Test that stock out transaction works properly"""
        initial_stock = self.product.stock
        
        # Create a stock out transaction
        response = self.client.post(reverse('stock_out'), {
            'transaction_type': 'OUT',
            'product': self.product.id,
            'quantity': 5,
            'reason': 'sale',
            'date': '2023-04-01',
            'reference': 'TEST-REF-002',
            'notes': 'Test stock out transaction'
        })
        
        # Check redirect
        self.assertRedirects(response, reverse('stock_transaction'))
        
        # Check stock has decreased
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 5)
        
        # Check transaction record was created
        transactions = StockTransaction.objects.filter(product=self.product)
        self.assertEqual(transactions.count(), 1)
        transaction = transactions.first()
        self.assertEqual(transaction.transaction_type, 'OUT')
        self.assertEqual(transaction.quantity, 5)
    
    def test_transaction_list_page_load(self):
        """Test that transaction list page loads properly"""
        response = self.client.get(reverse('transactions'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions.html')

class UserManagementTest(TestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpassword',
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='userpassword'
        )
        
        # Create test users
        for i in range(5):
            User.objects.create_user(
                username=f'testuser{i}',
                password='password123',
                email=f'test{i}@example.com'
            )
        
        # Client
        self.client = Client()
    
    def test_users_page_requires_login(self):
        """Test that the users page requires login"""
        response = self.client.get(reverse('users'))
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_users_page_requires_permission(self):
        """Test that the users page requires proper permissions"""
        # Login as regular user without permission
        self.client.login(username='regularuser', password='userpassword')
        response = self.client.get(reverse('users'))
        # Should redirect to login page with 'next' parameter
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_users_page_accessible_to_admin(self):
        """Test that admin can access the users page"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('users'))
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users.html')
    
    def test_users_page_contains_all_users(self):
        """Test that the users page shows all users"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('users'))
        
        # Check context
        self.assertEqual(response.context['total_count'], User.objects.count())
        
        # Check the page contains usernames of our test users
        for i in range(5):
            self.assertContains(response, f'testuser{i}')
    
    def test_users_search_functionality(self):
        """Test that the search functionality works"""
        self.client.login(username='admin', password='adminpassword')
        
        # Create a unique user for testing search
        User.objects.create_user(
            username='uniqueusername',
            password='password123',
            email='unique@example.com'
        )
        
        # Search for the unique user
        response = self.client.get(reverse('users') + '?search=uniqueusername')
        
        # Should only contain our unique user
        self.assertContains(response, 'uniqueusername')
        self.assertNotContains(response, 'testuser0')  # Shouldn't contain other test users
