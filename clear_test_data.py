import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dating.settings')
django.setup()

from app.models import (
    User, Profile, CallHistory, Transaction, Wallet,
    WithdrawalRequest, AgentApplication, Notification, PhoneOTP, UserActivity
)
from rest_framework.authtoken.models import Token

print("Clearing test data while preserving superadmins...")
CallHistory.objects.all().delete()
Transaction.objects.all().delete()
WithdrawalRequest.objects.all().delete()
AgentApplication.objects.all().delete()
Notification.objects.all().delete()
PhoneOTP.objects.all().delete()
UserActivity.objects.all().delete()
Profile.objects.filter(user__is_superuser=False).delete()
Wallet.objects.filter(user__is_superuser=False).delete()
Token.objects.filter(user__is_superuser=False).delete()
deleted_users = User.objects.filter(is_superuser=False).delete()
Wallet.objects.all().update(balance=0)

print(f"✅ Data cleared! Superadmin accounts remaining: {list(User.objects.filter(is_superuser=True).values_list('username', flat=True))}")
