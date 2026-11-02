from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db.models import Q
from .models import User, Profile, Offer, TermsAndConditions, PrivacyPolicy, HelpLine, UserActivity, CallHistory, Wallet, Transaction, WithdrawalRequest, AgentApplication, PhoneOTP


def verify_phone_otp(phone_number, entered_otp):
    """
    Validates OTP for authentication.
    Currently set to 1234 for all phone numbers.
    Also checks against PhoneOTP record if present.
    """
    clean_phone = str(phone_number).strip()
    clean_otp = str(entered_otp).strip()

    if not clean_otp.isdigit() or len(clean_otp) != 4:
        return False, "OTP must be a 4-digit number."

    # Universal static OTP "1234" is always accepted for all phone numbers
    if clean_otp == '1234':
        record = PhoneOTP.objects.filter(phone_number=clean_phone, is_verified=False).order_by('-created_at').first()
        if record:
            record.is_verified = True
            record.save(update_fields=['is_verified'])
        return True, "Verified"

    record = PhoneOTP.objects.filter(phone_number=clean_phone, is_verified=False).order_by('-created_at').first()
    if record:
        if record.is_expired():
            return False, "OTP has expired. Please request a new one."
        if record.otp != clean_otp:
            return False, "Incorrect OTP code. Please enter the valid code."
        record.is_verified = True
        record.save(update_fields=['is_verified'])
        return True, "Verified"

    return True, "Verified"


def validate_10_digit_number(value, field_name="Phone number"):
    """
    Validates that a field is strictly a 10-digit number.
    Only digits are allowed. Texts/letters and symbols are strictly disallowed.
    """
    if value is None:
        raise serializers.ValidationError(f"{field_name} is required.")

    val_str = str(value).strip()
    if not val_str:
        raise serializers.ValidationError(f"{field_name} cannot be empty.")

    # Disallow any alphabet/text character
    if any(c.isalpha() for c in val_str):
        raise serializers.ValidationError("Only 10-digit number is allowed. Texts/letters are not allowed.")

    # Disallow any symbol, space, or non-digit character
    if not val_str.isdigit():
        raise serializers.ValidationError("Only 10-digit number is allowed. Symbols and spaces are not allowed.")

    # Enforce exactly 10 digits
    if len(val_str) != 10:
        raise serializers.ValidationError(f"{field_name} must be exactly 10 digits.")

    return val_str


class UserSerializer(serializers.ModelSerializer):
    is_agent = serializers.BooleanField(source='is_staff', read_only=True)
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'name', 'age', 'gender', 'is_online', 'is_on_call', 'coins', 'created_at', 'is_agent', 'role', 'agent_status', 'profile']
        read_only_fields = ['id', 'created_at', 'is_online', 'is_on_call', 'coins', 'is_agent', 'role', 'agent_status']

    def get_role(self, obj):
        return 'agent' if obj.is_staff else 'user'

    def get_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.name if profile and profile.name else (obj.username or '')

    def get_age(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.age if profile and profile.age else 18

    def get_gender(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.gender if profile and profile.gender else 'other'

    def get_profile(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            request = self.context.get('request')
            pic_url = None
            if profile.profile_picture:
                pic_url = request.build_absolute_uri(profile.profile_picture.url) if request else profile.profile_picture.url
            return {
                'id': profile.id,
                'name': profile.name,
                'age': profile.age,
                'gender': profile.gender,
                'bio': profile.bio,
                'profile_picture': pic_url,
                'phone_number': profile.phone_number
            }
        return None


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'user', 'name', 'age', 'gender', 'phone_number', 'bio', 'profile_picture', 'is_verified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified']

class ProfileCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, default='User')
    age = serializers.IntegerField(required=False, default=18)
    gender = serializers.ChoiceField(choices=Profile.GENDER_CHOICES, required=False, default='other')
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Profile
        fields = ['name', 'age', 'gender', 'phone_number', 'bio', 'profile_picture']

    def validate_phone_number(self, value):
        if value:
            return validate_10_digit_number(value, "Profile phone number")
        return value

def validate_gmail_address(value, field_name="Email"):
    """
    Validates that the email address strictly ends with @gmail.com.
    """
    if not value:
        return value
    val_str = str(value).strip().lower()
    if not val_str.endswith('@gmail.com'):
        raise serializers.ValidationError(f"{field_name} must end with @gmail.com.")
    prefix = val_str[:-len('@gmail.com')]
    if not prefix or '@' in prefix:
        raise serializers.ValidationError("Please provide a valid Gmail address.")
    return val_str

class UserRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True, error_messages={'required': '10-digit phone_number is required.'})
    name = serializers.CharField(required=False, allow_blank=True, default='')
    age = serializers.IntegerField(required=False, default=18)
    gender = serializers.CharField(required=False, allow_blank=True, default='other')
    otp = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    profile = serializers.DictField(write_only=True, required=False)

    def to_internal_value(self, data):
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                pass

        if hasattr(data, 'dict'):
            raw = data.dict()
        elif isinstance(data, dict):
            raw = dict(data)
        else:
            raw = {}

        # If data is wrapped inside a root key (user, data, payload, profile, body, params, input)
        for wrapper in ['user', 'data', 'payload', 'profile', 'body', 'params', 'input']:
            nested = raw.get(wrapper)
            if isinstance(nested, dict):
                for k, v in nested.items():
                    if k not in raw or not raw[k]:
                        raw[k] = v

        profile_data = raw.get('profile')
        if isinstance(profile_data, dict):
            for k in ['name', 'age', 'gender', 'bio', 'phone_number']:
                if k in profile_data and (k not in raw or not raw[k]):
                    raw[k] = profile_data[k]

        payload = {}
        for k, v in raw.items():
            k_clean = str(k).strip().lower().replace('_', '').replace('-', '').replace(' ', '')
            val = v.strip() if isinstance(v, str) else v

            # Phone matching
            if k_clean in ('phone', 'phonenumber', 'phoneno', 'mobile', 'mobilenumber', 'mobileno', 'contact', 'contactnumber', 'userphone', 'cell', 'cellphone', 'tel'):
                if 'phone_number' not in payload or not payload['phone_number']:
                    sval = str(val or '').strip().replace(' ', '').replace('-', '')
                    if sval.startswith('+91') and len(sval) == 13:
                        sval = sval[3:]
                    elif sval.startswith('91') and len(sval) == 12:
                        sval = sval[2:]
                    elif sval.startswith('0') and len(sval) == 11:
                        sval = sval[1:]
                    payload['phone_number'] = sval

            # Name matching
            elif k_clean in ('name', 'fullname', 'username', 'firstname', 'displayname'):
                if 'name' not in payload or not payload['name']:
                    payload['name'] = val

            # Age matching
            elif k_clean in ('age', 'userage'):
                if 'age' not in payload:
                    try:
                        payload['age'] = int(val)
                    except Exception:
                        payload['age'] = 18

            # Gender matching
            elif k_clean in ('gender', 'sex', 'usergender'):
                if 'gender' not in payload or not payload['gender']:
                    payload['gender'] = val

            # OTP matching
            elif k_clean in ('otp', 'otpcode', 'verificationcode', 'code'):
                if 'otp' not in payload or not payload['otp']:
                    payload['otp'] = str(val).strip()

            else:
                payload[str(k).strip()] = val

        # Retain standard keys if present in raw
        for std_k in ['phone_number', 'name', 'age', 'gender', 'otp', 'password', 'bio', 'profile_picture']:
            if std_k not in payload and std_k in raw:
                payload[std_k] = raw[std_k]

        # If phone_number is still missing, check username if numeric
        if not payload.get('phone_number') and raw.get('username') and str(raw['username']).strip().isdigit():
            payload['phone_number'] = str(raw['username']).strip()

        # Smart fallback for name if empty
        if not payload.get('name'):
            phone = str(payload.get('phone_number', '')).strip()
            payload['name'] = f"User_{phone[-4:]}" if len(phone) >= 4 else "User"

        # Fallback for age
        if 'age' not in payload or payload['age'] is None or str(payload['age']).strip() == '':
            payload['age'] = 18
        else:
            try:
                payload['age'] = int(str(payload['age']).strip())
            except Exception:
                payload['age'] = 18

        # Normalize gender
        if payload.get('gender'):
            payload['gender'] = str(payload['gender']).strip().lower()
        else:
            payload['gender'] = 'other'

        return super().to_internal_value(payload)

    def validate_phone_number(self, value):
        val = validate_10_digit_number(value, "Phone number")
        if User.objects.filter(Q(phone_number=val) | Q(username=val)).exists():
            raise serializers.ValidationError("This phone number is already registered. Please log in.")
        return val

    def validate_name(self, value):
        val = str(value or '').strip()
        return val if val else 'User'

    def validate_age(self, value):
        if value is None:
            return 18
        if value < 18 or value > 120:
            return 18
        return value

    def validate_gender(self, value):
        if value:
            val = str(value).strip().lower()
            if val in ('male', 'm', 'man', 'boy'):
                return 'male'
            elif val in ('female', 'f', 'woman', 'girl'):
                return 'female'
            return 'other'
        return 'other'

    def validate(self, attrs):
        phone = attrs.get('phone_number')
        otp = attrs.get('otp')
        if otp:
            is_valid, msg = verify_phone_otp(phone, otp)
            if not is_valid:
                raise serializers.ValidationError({'otp': [msg]})
        return attrs

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None) or {}
        name = validated_data.get('name') or profile_data.get('name')
        age = validated_data.get('age') or profile_data.get('age')
        phone_number = validated_data['phone_number']
        password = validated_data.get('password')
        gender = validated_data.get('gender') or profile_data.get('gender', '')
        bio = validated_data.get('bio') or profile_data.get('bio', '')
        profile_picture = validated_data.get('profile_picture') or profile_data.get('profile_picture', None)

        user = User.objects.create(
            username=phone_number,
            phone_number=phone_number,
            is_staff=False,
            coins=0
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        # Save profile strictly with user-provided data including gender
        Profile.objects.create(
            user=user,
            name=name,
            age=age,
            gender=gender or '',
            phone_number=phone_number,
            bio=bio or '',
            profile_picture=profile_picture
        )
        return user


class GoogleAuthSerializer(serializers.Serializer):
    google_id = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField()
    profile_picture = serializers.URLField(required=False)

    def validate_email(self, value):
        return validate_gmail_address(value, "Email")

class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)
    app_type = serializers.CharField(required=False, allow_blank=True)
    fcm_token = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            payload = data.dict()
        elif isinstance(data, dict):
            payload = dict(data)
        else:
            payload = {}
        for phone_key in ['phone', 'mobile', 'phone_no', 'phonenumber', 'contact', 'contact_number']:
            if phone_key in payload and not payload.get('phone_number'):
                payload['phone_number'] = payload[phone_key]
        return super().to_internal_value(payload)

    def validate_phone_number(self, value):
        return validate_10_digit_number(value, "Phone number")

    def validate(self, attrs):
        phone = attrs.get('phone_number')
        otp = attrs.get('otp')
        is_valid, msg = verify_phone_otp(phone, otp)
        if not is_valid:
            raise serializers.ValidationError({'otp': [msg]})
        return attrs

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    otp = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    app_type = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        raw_identifier = attrs.get('phone_number') or attrs.get('username')
        otp = attrs.get('otp')
        password = attrs.get('password')
        app_type = attrs.get('app_type')

        if not raw_identifier:
            raise serializers.ValidationError({
                'phone_number': ['10-digit phone number is required for login.']
            })

        val_str = validate_10_digit_number(raw_identifier, "Phone number")

        if not otp and not password:
            raise serializers.ValidationError({
                'otp': ['Please provide OTP (or password) to log in.']
            })

        # Match user by phone_number or username
        user = User.objects.filter(Q(phone_number=val_str) | Q(username=val_str)).first()

        if not user:
            raise serializers.ValidationError({
                'non_field_errors': ['Account not found with this 10-digit number. Please sign up first.']
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['This account is deactivated. Please contact support.']
            })

        # If OTP provided, verify OTP
        if otp:
            is_valid, msg = verify_phone_otp(val_str, otp)
            if not is_valid:
                raise serializers.ValidationError({'otp': [msg]})
        elif password:
            if not user.check_password(password):
                raise serializers.ValidationError({
                    'non_field_errors': ['Invalid 10-digit number or password.']
                })

        # Strict Role Enforcement by app_type
        if app_type == 'agent':
            if not user.is_staff:
                raise serializers.ValidationError({
                    'non_field_errors': ['Access denied. This account is not registered as an Agent. Please use the Nammal User App.']
                })
            if user.agent_status == 'pending':
                raise serializers.ValidationError({
                    'non_field_errors': ['Your agent application is pending admin review. You will be notified once approved.']
                })
            elif user.agent_status == 'rejected':
                raise serializers.ValidationError({
                    'non_field_errors': ['Your agent application was not approved. Please contact support.']
                })
            elif user.agent_status == 'suspended':
                raise serializers.ValidationError({
                    'non_field_errors': ['Your agent account has been suspended by administration. Please contact support.']
                })
            elif user.agent_status == 'terminated':
                raise serializers.ValidationError({
                    'non_field_errors': ['Your agent account has been terminated.']
                })
        elif app_type == 'user':
            if user.is_staff:
                raise serializers.ValidationError({
                    'non_field_errors': ['This account is registered as an Agent. Please use the Nammal Agent App to log in.']
                })

        attrs['user'] = user
        return attrs


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ['id', 'title', 'description', 'coin_value', 'is_active', 'start_date', 'end_date', 'created_at']

class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = ['id', 'title', 'content', 'is_active', 'created_at', 'updated_at']

class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ['id', 'title', 'content', 'is_active', 'created_at', 'updated_at']

class HelpLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpLine
        fields = ['id', 'title', 'phone_number', 'email', 'address', 'is_active', 'created_at', 'updated_at']

class UserActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'activity_type', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class OnlineUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'profile', 'is_online', 'coins']

class OnCallUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'profile', 'is_on_call', 'coins']

# class CallHistorySerializer(serializers.ModelSerializer):
#     caller = UserSerializer(read_only=True)
#     receiver = UserSerializer(read_only=True)

#     class Meta:
#         model = CallHistory
#         fields = ['id', 'caller', 'receiver', 'start_time', 'end_time', 'duration', 'status']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'transaction_type', 'reference_id', 'created_at']

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'amount', 'status', 'created_at', 'updated_at']




class CallHistorySerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    call_duration_seconds = serializers.SerializerMethodField()
    call_duration_formatted = serializers.SerializerMethodField()
    caller_balance = serializers.SerializerMethodField()
    receiver_balance = serializers.SerializerMethodField()
    coins_earned = serializers.SerializerMethodField()

    class Meta:
        model = CallHistory
        fields = [
            'id', 'caller', 'receiver', 'call_type', 'channel_name',
            'start_time', 'end_time', 'status',
            'call_duration_seconds', 'call_duration_formatted',
            'caller_balance', 'receiver_balance', 'coins_earned'
        ]

    def get_call_duration_seconds(self, obj):
        if obj.end_time and obj.start_time:
            return int((obj.end_time - obj.start_time).total_seconds())
        return 0

    def get_call_duration_formatted(self, obj):
        if obj.end_time and obj.start_time:
            duration_seconds = (obj.end_time - obj.start_time).total_seconds()
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        return "0m 0s"

    def get_caller_balance(self, obj):
        from .models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=obj.caller)
        return wallet.balance

    def get_receiver_balance(self, obj):
        from .models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=obj.receiver)
        return wallet.balance

    def get_coins_earned(self, obj):
        if obj.receiver.is_staff and obj.status == 'completed':
            from .models import GlobalSetting
            try:
                reward_setting = GlobalSetting.objects.get(key='call_reward_amount')
                return reward_setting.get_typed_value()
            except GlobalSetting.DoesNotExist:
                return 0
        return 0



class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'updated_at']




class AgentApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AgentApplication
        fields = ['id', 'user', 'reason', 'experience', 'availability', 'status', 'admin_notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'status', 'admin_notes', 'created_at', 'updated_at']


class AgentApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentApplication
        fields = ['reason', 'experience', 'availability']


class AgentRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    age = serializers.IntegerField(required=False, default=20)
    otp = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    gender = serializers.CharField(required=False, allow_blank=True, default='female')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='Applied directly via Nammal Agent App')
    experience = serializers.CharField(required=False, allow_blank=True, default='')
    availability = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_phone_number(self, value):
        val = validate_10_digit_number(value, "Phone number")
        if User.objects.filter(Q(phone_number=val) | Q(username=val)).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return val

    def validate(self, attrs):
        phone = attrs.get('phone_number')
        otp = attrs.get('otp')
        if otp:
            is_valid, msg = verify_phone_otp(phone, otp)
            if not is_valid:
                raise serializers.ValidationError({'otp': [msg]})
        return attrs

    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        password = validated_data.get('password')
        name = validated_data.get('name', '')
        age = validated_data.get('age', 20)
        gender = validated_data.get('gender', 'female')
        bio = validated_data.get('bio', '')
        profile_picture = validated_data.get('profile_picture', None)
        reason = validated_data.get('reason', 'Applied directly via Nammal Agent App')
        experience = validated_data.get('experience', '')
        availability = validated_data.get('availability', '')

        user = User.objects.create(
            username=phone_number,
            phone_number=phone_number,
            is_staff=True,
            agent_status='pending',
            coins=0
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        Profile.objects.create(
            user=user,
            name=name,
            age=age,
            gender=gender,
            phone_number=phone_number,
            bio=bio,
            profile_picture=profile_picture
        )

        Wallet.objects.create(user=user, balance=0)

        AgentApplication.objects.create(
            user=user,
            reason=reason,
            experience=experience,
            availability=availability,
            status='pending'
        )

        UserActivity.objects.create(user=user, activity_type='agent_registration')
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=4)


class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=4)

    def validate_phone_number(self, value):
        return validate_10_digit_number(value, "Phone number")


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=False)
    image = serializers.ImageField(required=False)
    profile_picture = serializers.ImageField(required=False)

    def validate(self, attrs):
        pic = attrs.get('avatar') or attrs.get('image') or attrs.get('profile_picture')
        if not pic:
            raise serializers.ValidationError("An image file is required under 'avatar', 'image', or 'profile_picture'.")
        attrs['file'] = pic
        return attrs