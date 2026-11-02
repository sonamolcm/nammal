# from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.utils import timezone

# # Create your models here.

# class User(AbstractUser):
#     # phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
#     phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
#     google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
#     is_online = models.BooleanField(default=False)
#     is_on_call = models.BooleanField(default=False)
#     coins = models.IntegerField(default=0)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)
#     fcm_token = models.CharField(max_length=255, blank=True, null=True)

#     USERNAME_FIELD = 'username'
#     REQUIRED_FIELDS = ['phone_number']

#     def __str__(self):
#         return self.username

# class Profile(models.Model):
#     GENDER_CHOICES = [
#         ('male', 'Male'),
#         ('female', 'Female'),
#         ('other', 'Other'),
#     ]

#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#     name = models.CharField(max_length=100)
#     age = models.PositiveIntegerField()
#     gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
#     phone_number = models.CharField(max_length=15)
#     bio = models.TextField(blank=True, null=True)
#     profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
#     is_verified = models.BooleanField(default=False)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name}'s Profile"

# class Offer(models.Model):
#     title = models.CharField(max_length=200)
#     description = models.TextField()
#     coin_value = models.IntegerField()
#     is_active = models.BooleanField(default=True)
#     start_date = models.DateTimeField()
#     end_date = models.DateTimeField()
#     created_at = models.DateTimeField(default=timezone.now)

#     def __str__(self):
#         return self.title

# class TermsAndConditions(models.Model):
#     title = models.CharField(max_length=200)
#     content = models.TextField()
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title

# class PrivacyPolicy(models.Model):
#     title = models.CharField(max_length=200)
#     content = models.TextField()
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title

# class HelpLine(models.Model):
#     title = models.CharField(max_length=200)
#     phone_number = models.CharField(max_length=15)
#     email = models.EmailField()
#     address = models.TextField(blank=True, null=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title

# class UserActivity(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
#     activity_type = models.CharField(max_length=50)  # 'login', 'logout', 'call_start', 'call_end'
#     timestamp = models.DateTimeField(default=timezone.now)

#     def __str__(self):
#         return f"{self.user.username} - {self.activity_type}"

# class CallHistory(models.Model):
#     CALL_TYPES = [
#         ('audio', 'Audio'),
#         ('video', 'Video'),
#     ]
#     STATUS_CHOICES = [
#         ('initiated', 'Initiated'),
#         ('accepted', 'Accepted'),
#         ('rejected', 'Rejected'),
#         ('missed', 'Missed'),
#         ('cancelled', 'Cancelled'),
#         ('completed', 'Completed'),
#     ]

#     caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
#     receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
#     channel_name = models.CharField(max_length=100, unique=True)
#     call_type = models.CharField(max_length=10, choices=CALL_TYPES)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
#     start_time = models.DateTimeField(default=timezone.now)
#     end_time = models.DateTimeField(blank=True, null=True)

#     def __str__(self):
#         return f"Call: {self.caller.username} -> {self.receiver.username} ({self.status})"

# class AgentTaskConfig(models.Model):
#     daily_call_target = models.PositiveIntegerField(default=50)
#     weekly_call_target = models.PositiveIntegerField(default=250)
#     monthly_call_target = models.PositiveIntegerField(default=1000)
#     updated_at = models.DateTimeField(auto_now=True)

#     def save(self, *args, **kwargs):
#         self.pk = 1 # Force it to be a singleton
#         super(AgentTaskConfig, self).save(*args, **kwargs)

#     @classmethod
#     def load(cls):
#         obj, created = cls.objects.get_or_create(pk=1)
#         return obj

# class GlobalSetting(models.Model):
#     TYPE_CHOICES = [
#         ('int', 'Integer'),
#         ('float', 'Float'),
#         ('bool', 'Boolean'),
#         ('str', 'String'),
#     ]
#     key = models.CharField(max_length=50, unique=True)
#     value = models.CharField(max_length=255)
#     data_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='str')
#     description = models.TextField(blank=True, null=True)

#     def get_typed_value(self):
#         if self.data_type == 'int':
#             return int(self.value)
#         elif self.data_type == 'float':
#             return float(self.value)
#         elif self.data_type == 'bool':
#             return str(self.value).lower() in ['true', '1', 't', 'y', 'yes']
#         return str(self.value)

#     def __str__(self):
#         return f"{self.key}: {self.value} ({self.data_type})"

# class Wallet(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
#     balance = models.IntegerField(default=0)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user.username}'s Wallet - Balance: {self.balance}"

# class WithdrawalRequest(models.Model):
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('approved', 'Approved'),
#         ('rejected', 'Rejected'),
#     ]
#     agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
#     amount = models.IntegerField()
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.agent.username} - {self.amount} ({self.status})"

# class Transaction(models.Model):
#     TYPE_CHOICES = [
#         ('earn_call', 'Earned from Call'),
#         ('withdrawal', 'Withdrawal'),
#         ('coin_purchase', 'Coin Purchase'),
#     ]
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
#     amount = models.IntegerField()
#     transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
#     reference_id = models.CharField(max_length=100, blank=True, null=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     def __str__(self):
#         return f"{self.user.username} - {self.amount} ({self.transaction_type})"



from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    AGENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]

    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    is_on_call = models.BooleanField(default=False)
    coins = models.IntegerField(default=0)
    agent_status = models.CharField(max_length=20, choices=AGENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    fcm_token = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone_number']

    def __str__(self):
        return self.username

class Profile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, default='')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}'s Profile"


class PhoneOTP(models.Model):
    phone_number = models.CharField(max_length=15, db_index=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 600

    def __str__(self):
        return f"{self.phone_number} - {self.otp}"

class Offer(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    coin_value = models.IntegerField()
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class TermsAndConditions(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class HelpLine(models.Model):
    title = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"

class CallHistory(models.Model):
    CALL_TYPES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
    channel_name = models.CharField(max_length=100, unique=True)
    call_type = models.CharField(max_length=10, choices=CALL_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(blank=True, null=True)
    coins_earned = models.IntegerField(default=0)

    def __str__(self):
        return f"Call: {self.caller.username} -> {self.receiver.username} ({self.status})"

    @property
    def duration(self):
        """Calculate call duration in seconds"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds())
        return 0

    @property
    def duration_formatted(self):
        """Return formatted duration string"""
        if self.duration > 0:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes}m {seconds}s"
        return "-"

class AgentTaskConfig(models.Model):
    daily_call_target = models.PositiveIntegerField(default=50)
    weekly_call_target = models.PositiveIntegerField(default=250)
    monthly_call_target = models.PositiveIntegerField(default=1000)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super(AgentTaskConfig, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class GlobalSetting(models.Model):
    TYPE_CHOICES = [
        ('int', 'Integer'),
        ('float', 'Float'),
        ('bool', 'Boolean'),
        ('str', 'String'),
    ]
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)
    data_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='str')
    description = models.TextField(blank=True, null=True)

    def get_typed_value(self):
        if self.data_type == 'int':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'bool':
            return str(self.value).lower() in ['true', '1', 't', 'y', 'yes']
        return str(self.value)

    def __str__(self):
        return f"{self.key}: {self.value} ({self.data_type})"

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - Balance: {self.balance}"

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent.username} - {self.amount} ({self.status})"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('earn_call', 'Earned from Call'),
        ('withdrawal', 'Withdrawal'),
        ('coin_purchase', 'Coin Purchase'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.transaction_type})"

class AgentApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_application')
    reason = models.TextField(help_text="Why do you want to become an agent?")
    experience = models.TextField(blank=True, help_text="Relevant experience")
    availability = models.TextField(blank=True, help_text="Availability details")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes on the application")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} Agent Application"


class Notification(models.Model):
    AUDIENCE_CHOICES = [
        ('all', 'All (Users & Agents)'),
        ('users', 'Regular Users Only'),
        ('agents', 'Agents Only'),
        ('specific', 'Specific User / Agent'),
    ]

    title = models.CharField(max_length=255)
    body = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    target_audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications', blank=True, null=True)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    read_by = models.ManyToManyField(User, related_name='read_notifications', blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.target_audience}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
