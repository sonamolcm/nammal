import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dating.settings')
django.setup()

from app.models import TermsAndConditions, PrivacyPolicy, HelpLine, Offer
from django.utils import timezone
from datetime import datetime, timedelta

def create_sample_data():
    print("Creating sample data...")
    
    # Create Terms and Conditions
    if not TermsAndConditions.objects.filter(is_active=True).exists():
        TermsAndConditions.objects.create(
            title="Terms and Conditions",
            content="""
            Welcome to our Dating App!
            
            1. You must be 18+ to use this service
            2. Be respectful to other users
            3. No harassment or abusive behavior
            4. Profile information must be accurate
            5. We reserve the right to suspend accounts for violations
            """,
            is_active=True
        )
        print("✓ Created Terms and Conditions")
    
    # Create Privacy Policy
    if not PrivacyPolicy.objects.filter(is_active=True).exists():
        PrivacyPolicy.objects.create(
            title="Privacy Policy",
            content="""
            Your privacy is important to us.
            
            1. We collect only necessary information
            2. Your data is securely stored
            3. We don't share personal information with third parties
            4. You can request data deletion at any time
            5. Cookies are used for authentication purposes
            """,
            is_active=True
        )
        print("✓ Created Privacy Policy")
    
    # Create Help Line
    if not HelpLine.objects.filter(is_active=True).exists():
        HelpLine.objects.create(
            title="Customer Support",
            phone_number="+1-800-555-0199",
            email="support@datingapp.com",
            address="123 Support Street, Tech City, TC 12345",
            is_active=True
        )
        print("✓ Created Help Line")
    
    # Create Sample Offers
    if not Offer.objects.filter(is_active=True).exists():
        # Active offer
        Offer.objects.create(
            title="Welcome Bonus!",
            description="Get 500 coins when you first join our app!",
            coin_value=500,
            is_active=True,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30)
        )
        
        # Another active offer
        Offer.objects.create(
            title="Valentine's Special",
            description="Limited time offer: 1000 coins for Valentine's Day!",
            coin_value=1000,
            is_active=True,
            start_date=timezone.now() - timedelta(days=7),
            end_date=timezone.now() + timedelta(days=7)
        )
        
        # Expired offer
        Offer.objects.create(
            title="New Year Offer",
            description="Happy New Year! This offer has expired.",
            coin_value=200,
            is_active=False,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=30)
        )
        
        print("✓ Created Sample Offers")
    
    print("\nSample data creation completed!")

if __name__ == "__main__":
    create_sample_data()