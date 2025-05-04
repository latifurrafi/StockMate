# StockMate

A Django-based inventory management system designed for businesses to track products, monitor stock levels, generate reports, and manage transactions.

## Features

- **Product Management**: Track products across categories with detailed information
- **Inventory Tracking**: Real-time stock monitoring with low stock alerts
- **Transaction Management**: Record stock-ins and stock-outs with custom reasons
- **Order Processing**: Manage customer orders and order items
- **Supplier Management**: Track supplier information and performance
- **Advanced Reporting**: Generate reports with filterable data on inventory, sales, and suppliers 
- **Data Visualization**: Visual charts and graphs using Chart.js
- **PDF/CSV Export**: Export reports in multiple formats
- **Modern Admin Interface**: Enhanced with django-unfold for better UX
- **Mobile-Responsive Design**: Optimized sidebar for all device sizes

## Technology Stack

- **Backend**: Django 5.0+
- **Database**: MySQL 
- **Frontend**: HTML, CSS, JavaScript, Alpine.js
- **Admin Interface**: django-unfold
- **PDF Generation**: xhtml2pdf
- **Charts**: Chart.js
- **UI Framework**: Bootstrap

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/StockMate.git
cd StockMate
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure MySQL database:
   - Create a MySQL database:
   ```bash
   mysql -u root -p
   CREATE DATABASE stockmate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   exit;
   ```
   - Update database settings in main_project/settings.py if needed:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'stockmate_db',
           'USER': 'root',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '3306',
       }
   }
   ```

5. Apply migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Load sample data (optional):
```bash
python dummy_data.py
```

8. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin/` using your superuser credentials
2. Navigate to the main application at `http://localhost:8000/`
3. Use the sidebar to access different sections:
   - Dashboard
   - Products
   - Inventory
   - Transactions
   - Orders
   - Suppliers
   - Reports
   - Settings

## Project Structure

- **main_project/**: Django project settings
- **main_app/**: Main application code
  - **models.py**: Database models
  - **views.py**: View controllers
  - **admin.py**: Admin interface customization
  - **urls.py**: URL routing
  - **templates/**: HTML templates
  - **static/**: CSS, JS, and other static files

## Reports

StockMate provides multiple report types:
- Inventory Value
- Low Stock
- Product Movement
- Sales Analysis
- Supplier Performance

Reports can be filtered by date range and exported as PDF or CSV.

## Recent Improvements

- Enhanced reporting with tabbed interfaces and charts
- Fixed template syntax errors in report generation
- Implemented mobile-responsive sidebar with improved UX
- Integrated django-unfold for a modern admin interface
- Enhanced test data generation with more realistic sample data
- Implemented various report types and visualization options