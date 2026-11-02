from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q
from .models import (
    User, Profile, Offer, CallHistory, Wallet, Transaction,
    WithdrawalRequest, AgentApplication, Notification, AgentTaskConfig, GlobalSetting
)
from .serializers import validate_10_digit_number


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Allow logging in with username or 10-digit phone number or email
        user = authenticate(username=username, password=password)
        if not user:
            # Try finding user by phone number or email
            lookup_user = User.objects.filter(
                Q(phone_number=username) | Q(email__iexact=username)
            ).first()
            if lookup_user and lookup_user.check_password(password):
                user = lookup_user

        if not user:
            raise serializers.ValidationError({"error": "Invalid username or password."})

        if not user.is_active:
            raise serializers.ValidationError({"error": "This administrator account is disabled."})

        # Ensure account is superuser / admin
        if not (user.is_superuser or user.is_staff):
            raise serializers.ValidationError({
                "error": "Access denied. Only administrators are allowed to log into the Admin API."
            })

        attrs['user'] = user
        return attrs


class AdminUserSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'name', 'avatar_url', 'is_staff', 'agent_status']

    def get_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.name if profile and profile.name else obj.username

    def get_avatar_url(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            return profile.profile_picture.url
        return None


class AdminProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'name', 'age', 'gender', 'phone_number',
            'bio', 'profile_picture_url', 'is_verified', 'created_at', 'updated_at'
        ]

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class AdminUserListSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    profile = AdminProfileSerializer(read_only=True)
    total_calls_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'coins',
            'wallet_balance', 'is_online', 'is_on_call', 'is_active',
            'is_staff', 'agent_status', 'date_joined', 'last_login',
            'profile', 'total_calls_count'
        ]

    def get_wallet_balance(self, obj):
        return obj.wallet.balance if hasattr(obj, 'wallet') else obj.coins

    def get_total_calls_count(self, obj):
        return getattr(obj, 'annotated_calls_count', 0)


class AdminUserDetailSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    profile = AdminProfileSerializer(read_only=True)
    total_calls_count = serializers.SerializerMethodField()
    completed_calls_count = serializers.SerializerMethodField()
    outgoing_calls_count = serializers.SerializerMethodField()
    incoming_calls_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'coins',
            'wallet_balance', 'is_online', 'is_on_call', 'is_active',
            'is_staff', 'agent_status', 'date_joined', 'last_login',
            'fcm_token', 'profile', 'total_calls_count', 'completed_calls_count',
            'outgoing_calls_count', 'incoming_calls_count'
        ]

    def get_wallet_balance(self, obj):
        return obj.wallet.balance if hasattr(obj, 'wallet') else obj.coins

    def get_total_calls_count(self, obj):
        return CallHistory.objects.filter(Q(caller=obj) | Q(receiver=obj)).count()

    def get_completed_calls_count(self, obj):
        return CallHistory.objects.filter(Q(caller=obj) | Q(receiver=obj), status='completed').count()

    def get_outgoing_calls_count(self, obj):
        return CallHistory.objects.filter(caller=obj).count()

    def get_incoming_calls_count(self, obj):
        return CallHistory.objects.filter(receiver=obj).count()


class AdminCoinAdjustmentSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['add', 'deduct'])
    coins = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class AdminUserStatusUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)


class AdminAgentCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, min_length=4)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    age = serializers.IntegerField(min_value=18, max_value=100, default=18)
    gender = serializers.ChoiceField(choices=['female', 'male', 'other'], default='female')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    agent_status = serializers.ChoiceField(
        choices=['pending', 'approved', 'suspended', 'rejected', 'terminated'],
        default='approved'
    )

    def validate_phone_number(self, value):
        val = validate_10_digit_number(value, "Phone number")
        if User.objects.filter(phone_number=val).exists():
            raise serializers.ValidationError("A user or agent with this phone number already exists.")
        return val

    def validate_username(self, value):
        val = value.strip()
        if User.objects.filter(username=val).exists():
            raise serializers.ValidationError("Username already exists.")
        return val

    def validate_email(self, value):
        if value:
            val = value.strip().lower()
            if not val.endswith('@gmail.com'):
                raise serializers.ValidationError("Email must end with @gmail.com")
            if User.objects.filter(email__iexact=val).exists():
                raise serializers.ValidationError("Email is already registered.")
            return val
        return ''


class AdminAgentStatusSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'suspend', 'reject', 'terminate'])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default='')


class AdminAgentApplicationSerializer(serializers.ModelSerializer):
    user = AdminUserSummarySerializer(read_only=True)

    class Meta:
        model = AgentApplication
        fields = [
            'id', 'user', 'reason', 'experience', 'availability',
            'status', 'admin_notes', 'created_at', 'updated_at'
        ]


class AdminApplicationReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default='')


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    agent = AdminUserSummarySerializer(read_only=True)
    agent_wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'agent', 'amount', 'status', 'created_at',
            'updated_at', 'agent_wallet_balance'
        ]

    def get_agent_wallet_balance(self, obj):
        if hasattr(obj.agent, 'wallet'):
            return obj.agent.wallet.balance
        return obj.agent.coins


class AdminWithdrawalReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])


class AdminCallHistorySerializer(serializers.ModelSerializer):
    caller = AdminUserSummarySerializer(read_only=True)
    receiver = AdminUserSummarySerializer(read_only=True)
    duration = serializers.IntegerField(read_only=True)
    duration_formatted = serializers.CharField(read_only=True)

    class Meta:
        model = CallHistory
        fields = [
            'id', 'caller', 'receiver', 'channel_name', 'call_type',
            'status', 'start_time', 'end_time', 'duration',
            'duration_formatted', 'coins_earned'
        ]


class AdminTransactionSerializer(serializers.ModelSerializer):
    user = AdminUserSummarySerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'amount', 'transaction_type',
            'reference_id', 'created_at'
        ]


class AdminOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = [
            'id', 'title', 'description', 'coin_value',
            'is_active', 'start_date', 'end_date', 'created_at'
        ]


class AdminAgentTaskConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTaskConfig
        fields = [
            'id', 'daily_call_target', 'weekly_call_target',
            'monthly_call_target', 'updated_at'
        ]


class AdminGlobalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSetting
        fields = ['id', 'key', 'value', 'data_type', 'description']


class AdminNotificationSerializer(serializers.ModelSerializer):
    recipient = AdminUserSummarySerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'image_url', 'target_audience',
            'recipient', 'sent_count', 'failed_count', 'created_at'
        ]


class AdminNotificationBroadcastSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    target_audience = serializers.ChoiceField(choices=['all', 'users', 'agents', 'specific'], default='all')
    recipient_id = serializers.IntegerField(required=False, allow_null=True)
    image_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default='')
    notification_type = serializers.CharField(max_length=50, default='general')

    def validate(self, attrs):
        if attrs.get('target_audience') == 'specific' and not attrs.get('recipient_id'):
            raise serializers.ValidationError({"recipient_id": "Recipient ID is required when target_audience is 'specific'."})
        return attrs
