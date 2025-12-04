import os
import django
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinTune.settings')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import Transaction

def populate():
    user_id = 6
    try:
        user = User.objects.get(id=user_id)
        print(f"Found user with ID {user_id}: {user.username}")
    except User.DoesNotExist:
        print(f"User with ID {user_id} does not exist.")
        # Check if any user exists to be helpful
        first_user = User.objects.first()
        if first_user:
            print(f"Using first available user instead: {first_user.username} (ID: {first_user.id})")
            user = first_user
        else:
            print("No users found in the database. Creating a dummy user.")
            user = User.objects.create_user(username='dummy_user', email='dummy@example.com', password='password123')
            print(f"Created dummy user: {user.username} (ID: {user.id})")

    transactions_data = [
        {
            'amount': Decimal('350.00'),
            'vendor_name': 'Starbucks',
            'category': 'FOOD',
            'transaction_type': 'EXPENSE',
            'date': timezone.now() - timedelta(days=2),
            'input_source': 'CAMERA',
            'is_recurring': False
        },
        {
            'amount': Decimal('450.50'),
            'vendor_name': 'Uber',
            'category': 'TRAVEL',
            'transaction_type': 'EXPENSE',
            'date': timezone.now() - timedelta(days=1),
            'input_source': 'VOICE',
            'is_recurring': False
        },
        {
            'amount': Decimal('15000.00'),
            'vendor_name': 'Landlord',
            'category': 'BILLS',
            'transaction_type': 'EXPENSE',
            'date': timezone.now() - timedelta(days=5),
            'input_source': 'MANUAL',
            'is_recurring': True
        },
        {
            'amount': Decimal('85000.00'),
            'vendor_name': 'Tech Solutions Ltd',
            'category': 'OTHER',
            'transaction_type': 'INCOME',
            'date': timezone.now() - timedelta(days=10),
            'input_source': 'MANUAL',
            'is_recurring': True
        },
        {
            'amount': Decimal('2100.00'),
            'vendor_name': 'D-Mart',
            'category': 'FOOD',
            'transaction_type': 'EXPENSE',
            'date': timezone.now() - timedelta(hours=3),
            'input_source': 'CAMERA',
            'is_recurring': False
        },
    ]

    for data in transactions_data:
        Transaction.objects.create(user=user, **data)
        print(f"Created transaction: {data['vendor_name']} - {data['amount']}")

if __name__ == '__main__':
    populate()
