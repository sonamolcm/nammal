
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta
import uuid
from django.conf import settings

from .models import (
    User, Profile, Offer, TermsAndConditions, PrivacyPolicy,
    HelpLine, UserActivity, CallHistory, AgentTaskConfig,
    GlobalSetting, Wallet, Transaction, WithdrawalRequest, Notification,
    PhoneOTP
)
from .serializers import (
    UserSerializer, ProfileSerializer, UserRegistrationSerializer,
    GoogleAuthSerializer, PhoneAuthSerializer, LoginSerializer,
    OfferSerializer, TermsAndConditionsSerializer, PrivacyPolicySerializer,
    HelpLineSerializer, OnlineUserSerializer, OnCallUserSerializer,
    CallHistorySerializer, WalletSerializer,
    ProfileCreateSerializer, TransactionSerializer, WithdrawalRequestSerializer,
    AgentRegistrationSerializer, ChangePasswordSerializer, ResetPasswordSerializer,
    AvatarUploadSerializer, validate_10_digit_number
)

try:
    from firebase_admin import messaging
except ImportError:
    pass
try:
    from agora_token_builder import RtcTokenBuilder
except ImportError:
    pass

import json

def _format_error_response(errors):
    """Ensure error response has both field breakdown and a clear top-level 'error' message."""
    msg = None
    if isinstance(errors, dict):
        if 'non_field_errors' in errors and errors['non_field_errors']:
            val = errors['non_field_errors']
            msg = str(val[0]) if isinstance(val, (list, tuple)) else str(val)
        else:
            for key, val in errors.items():
                if isinstance(val, (list, tuple)) and val:
                    first_err = str(val[0])
                    msg = f"{key}: {first_err}" if not first_err.lower().startswith(key.lower()) else first_err
                    break
                elif isinstance(val, dict):
                    nested = _format_error_response(val).data
                    msg = nested.get('error')
                    break
                elif val:
                    first_err = str(val)
                    msg = f"{key}: {first_err}" if not first_err.lower().startswith(key.lower()) else first_err
                    break
    elif isinstance(errors, (list, tuple)) and errors:
        msg = str(errors[0])

    if not msg:
        msg = "Invalid data provided."

    response_data = dict(errors) if isinstance(errors, dict) else {'details': errors}
    response_data['error'] = msg
    response_data['message'] = msg
    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

def _extract_request_data(request):
    """
    Robustly extract data dictionary from:
    1. request.data (parsed json, form-data, multipart)
    2. request.POST (standard Django post dict)
    3. request.body (raw json string fallback if Content-Type missing or text/plain)
    4. request.query_params / request.GET (URL query parameters)
    """
    data = {}
    if hasattr(request, 'data'):
        if isinstance(request.data, dict) and request.data:
            data.update(request.data)
        elif hasattr(request.data, 'dict') and request.data:
            data.update(request.data.dict())

    if hasattr(request, 'POST') and request.POST:
        post_dict = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
        for k, v in post_dict.items():
            if k not in data or not data[k]:
                data[k] = v

    if not data:
        try:
            if hasattr(request, 'body') and request.body:
                body_text = request.body.decode('utf-8')
                parsed = json.loads(body_text)
                if isinstance(parsed, dict):
                    data.update(parsed)
        except Exception:
            pass

    # Merge query parameters
    params = getattr(request, 'query_params', None) or getattr(request, 'GET', None)
    if params:
        for k, v in params.items():
            if k not in data or data[k] is None or data[k] == '':
                data[k] = v

    return data

def _build_auth_response(user, token_key, message, extra=None):
    """Standardized response payload for all authentication endpoints across User and Agent apps."""
    profile = getattr(user, 'profile', None)
    name = profile.name if profile and profile.name else (user.username or '')
    age = profile.age if profile and profile.age else 18
    gender = profile.gender if profile and profile.gender else 'other'
    phone_number = user.phone_number or (profile.phone_number if profile else '')

    payload = {
        'token': token_key,
        'role': 'agent' if user.is_staff else 'user',
        'is_agent': bool(user.is_staff),
        'agent_status': user.agent_status if user.is_staff else None,
        'phone_number': phone_number,
        'name': name,
        'age': age,
        'gender': gender,
        'user': UserSerializer(user).data,
        'message': message,
    }
    if extra:
        payload.update(extra)
    return payload

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send / Generate OTP for a 10-digit phone number.
    Returns 4-digit OTP code and records it with 10-minute validity.
    """
    data = _extract_request_data(request)
    raw_phone = data.get('phone_number') or data.get('phone') or data.get('mobile') or data.get('contact')
    if not raw_phone:
        return Response({
            'error': '10-digit phone_number is required.',
            'message': '10-digit phone_number is required.',
            'example': {'phone_number': '9876543210'}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        phone_number = validate_10_digit_number(raw_phone, "Phone number")
    except Exception as e:
        msg = str(e)
        if hasattr(e, 'detail') and isinstance(e.detail, list) and e.detail:
            msg = str(e.detail[0])
        return Response({'error': msg, 'message': msg}, status=status.HTTP_400_BAD_REQUEST)

    otp_code = "1234"
    PhoneOTP.objects.create(phone_number=phone_number, otp=otp_code)

    return Response({
        'status': 'success',
        'message': f'OTP sent successfully to {phone_number}',
        'phone_number': phone_number,
        'otp': otp_code
    })

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new customer for Nammal User App using phone_number, name, age, gender"""
    if request.method == 'GET':
        return Response({
            'status': 'Nammal User Registration Endpoint',
            'method': 'POST',
            'fields': {
                'phone_number': '10-digit mobile number (required, e.g. 9876543210)',
                'name': 'User full name (e.g. Rahul Sharma)',
                'age': 'User age (e.g. 24)',
                'gender': 'Gender: male / female / other'
            },
            'example_json_body': {
                'phone_number': '9876543210',
                'name': 'Rahul Sharma',
                'age': 24,
                'gender': 'male'
            }
        }, status=status.HTTP_200_OK)

    payload = _extract_request_data(request)
    serializer = UserRegistrationSerializer(data=payload)
    if serializer.is_valid():
        user = serializer.save()
        user.is_staff = False  # Ensure regular customer role
        user.save(update_fields=['is_staff'])

        token, created = Token.objects.get_or_create(user=user)

        fcm_token = payload.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token
            user.save(update_fields=['fcm_token'])

        UserActivity.objects.create(user=user, activity_type='registration')
        return Response(_build_auth_response(user, token.key, 'User registered successfully'), status=status.HTTP_201_CREATED)

    resp = _format_error_response(serializer.errors)
    resp.data['received_keys'] = list(payload.keys())
    if not payload:
        resp.data['hint'] = "The request body was empty. In Postman, go to 'Body' tab -> select 'raw' -> choose 'JSON', and send: {\"phone_number\": \"9876543210\", \"gender\": \"male\"}"
    return resp

# Dedicated alias for /api/user/register/
user_register = register_user

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """Authenticate user with Google"""
    serializer = GoogleAuthSerializer(data=request.data)
    if serializer.is_valid():
        google_id = serializer.validated_data['google_id']
        email = serializer.validated_data['email']
        name = serializer.validated_data['name']

        try:
            user = User.objects.get(google_id=google_id)
        except User.DoesNotExist:
            user = User.objects.create(
                username=email.split('@')[0],
                email=email,
                google_id=google_id,
                phone_number=None,
                is_staff=False
            )
            Profile.objects.create(
                user=user,
                name=name,
                age=18,
                gender='other',
                phone_number=None
            )
            UserActivity.objects.create(user=user, activity_type='google_registration')

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        UserActivity.objects.create(user=user, activity_type='login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'Google authentication successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_app_google_auth(request):
    """Dedicated Google Auth endpoint for User App with role guard against agents"""
    serializer = GoogleAuthSerializer(data=request.data)
    if serializer.is_valid():
        google_id = serializer.validated_data['google_id']
        email = serializer.validated_data['email']
        name = serializer.validated_data['name']

        try:
            user = User.objects.get(google_id=google_id)
            if user.is_staff:
                return Response({
                    'error': 'This account is registered as an Agent. Please use the Nammal Agent App.'
                }, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            user = User.objects.create(
                username=email.split('@')[0],
                email=email,
                google_id=google_id,
                phone_number=None,
                is_staff=False
            )
            Profile.objects.create(user=user, name=name, age=18, gender='other', phone_number=None)
            UserActivity.objects.create(user=user, activity_type='google_registration')

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        UserActivity.objects.create(user=user, activity_type='user_google_login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'Google authentication successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def phone_auth(request):
    """Authenticate user with 10-digit phone number and OTP"""
    payload = _extract_request_data(request)
    serializer = PhoneAuthSerializer(data=payload)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']

        user = User.objects.filter(Q(phone_number=phone_number) | Q(username=phone_number)).first()
        if not user:
            return Response({
                'error': 'User not found with this 10-digit number. Please register first.',
                'message': 'User not found with this 10-digit number. Please register first.'
            }, status=status.HTTP_404_NOT_FOUND)

        app_type = payload.get('app_type')
        if app_type == 'agent':
            if not user.is_staff:
                return Response({'error': 'Access denied. This account is not registered as an Agent. Please use the Nammal User App.'}, status=status.HTTP_403_FORBIDDEN)
            if user.agent_status == 'pending':
                return Response({'error': 'Your agent application is pending admin review. You will be notified once approved.'}, status=status.HTTP_403_FORBIDDEN)
            elif user.agent_status == 'rejected':
                return Response({'error': 'Your agent application was not approved. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
            elif user.agent_status == 'suspended':
                return Response({'error': 'Your agent account has been suspended by administration. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
            elif user.agent_status == 'terminated':
                return Response({'error': 'Your agent account has been terminated.'}, status=status.HTTP_403_FORBIDDEN)
        elif app_type == 'user':
            if user.is_staff:
                return Response({'error': 'This account is registered as an Agent. Please use the Nammal Agent App.'}, status=status.HTTP_403_FORBIDDEN)

        fcm_token = payload.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        UserActivity.objects.create(user=user, activity_type='login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'Phone authentication successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_app_phone_auth(request):
    """Dedicated phone OTP authentication endpoint for Nammal User App (strictly regular users)"""
    data = _extract_request_data(request)
    data['app_type'] = 'user'
    serializer = PhoneAuthSerializer(data=data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        user = User.objects.filter(Q(phone_number=phone_number) | Q(username=phone_number)).first()
        if not user:
            return Response({'error': 'User not found with this 10-digit number. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_staff:
            return Response({
                'error': 'This account is registered as an Agent. Please use the Nammal Agent App to log in.'
            }, status=status.HTTP_403_FORBIDDEN)

        fcm_token = data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        UserActivity.objects.create(user=user, activity_type='user_phone_login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'Phone authentication successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """General Login with 10-digit number and password (supports optional app_type)"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        UserActivity.objects.create(user=user, activity_type='login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'Login successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_app_login(request):
    """Dedicated login endpoint for Nammal User App (strictly non-agents)"""
    data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
    data['app_type'] = 'user'
    serializer = LoginSerializer(data=data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        UserActivity.objects.create(user=user, activity_type='user_login')
        user.is_online = True
        user.save()

        return Response(_build_auth_response(user, token.key, 'User login successful'))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def agent_login(request):
    """Dedicated login endpoint for Nammal Agent App (agents with agent_status='approved')"""
    data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
    data['app_type'] = 'agent'
    serializer = LoginSerializer(data=data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        UserActivity.objects.create(user=user, activity_type='agent_login')
        user.is_online = True
        user.save()

        # Gather agent initial state for seamless dashboard rendering
        wallet, _ = Wallet.objects.get_or_create(user=user)
        config = AgentTaskConfig.load()
        today = timezone.localdate()
        daily_completed = CallHistory.objects.filter(receiver=user, status='completed', start_time__date=today).count()

        extra = {
            'wallet_balance': wallet.balance,
            'today_completed_calls': daily_completed,
            'daily_call_target': config.daily_call_target,
        }
        return Response(_build_auth_response(user, token.key, 'Agent login successful', extra=extra))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def agent_phone_auth(request):
    """Dedicated phone OTP authentication endpoint for Nammal Agent App"""
    serializer = PhoneAuthSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        user = User.objects.filter(Q(phone_number=phone_number) | Q(username=phone_number)).first()
        if not user:
            return Response({'error': 'Agent account not found with this 10-digit number. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_staff:
            return Response({'error': 'Access denied. This account is not registered as an Agent. Please use the Nammal User App.'}, status=status.HTTP_403_FORBIDDEN)

        if user.agent_status == 'pending':
            return Response({'error': 'Your agent application is pending admin review. You will be notified once approved.'}, status=status.HTTP_403_FORBIDDEN)
        elif user.agent_status == 'rejected':
            return Response({'error': 'Your agent application was not approved. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
        elif user.agent_status == 'suspended':
            return Response({'error': 'Your agent account has been suspended by administration. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
        elif user.agent_status == 'terminated':
            return Response({'error': 'Your agent account has been terminated.'}, status=status.HTTP_403_FORBIDDEN)

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token

        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        UserActivity.objects.create(user=user, activity_type='agent_phone_login')
        user.is_online = True
        user.save()

        wallet, _ = Wallet.objects.get_or_create(user=user)
        config = AgentTaskConfig.load()
        today = timezone.localdate()
        daily_completed = CallHistory.objects.filter(receiver=user, status='completed', start_time__date=today).count()
        extra = {
            'wallet_balance': wallet.balance,
            'today_completed_calls': daily_completed,
            'daily_call_target': config.daily_call_target,
        }
        return Response(_build_auth_response(user, token.key, 'Agent authentication successful', extra=extra))
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([AllowAny])
def agent_register(request):
    """Direct agent application / registration from Nammal Agent App"""
    serializer = AgentRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.fcm_token = fcm_token
            user.save(update_fields=['fcm_token'])

        return Response({
            'status': 'success',
            'agent_status': 'pending',
            'role': 'agent',
            'is_agent': True,
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Agent registration submitted successfully! Your application is under review by admin. You will be able to log in once approved.'
        }, status=status.HTTP_201_CREATED)
    return _format_error_response(serializer.errors)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_toggle_status(request):
    """Toggle agent online availability for incoming calls in Nammal Agent App"""
    if not request.user.is_staff:
        return Response({'error': 'Unauthorized. Agent access only.'}, status=status.HTTP_403_FORBIDDEN)

    is_online = request.data.get('is_online')
    if is_online is None:
        request.user.is_online = not request.user.is_online
    else:
        request.user.is_online = bool(is_online)

    if not request.user.is_online:
        request.user.is_on_call = False

    request.user.save(update_fields=['is_online', 'is_on_call'])
    UserActivity.objects.create(
        user=request.user,
        activity_type='agent_online' if request.user.is_online else 'agent_offline'
    )

    return Response({
        'status': 'success',
        'is_online': request.user.is_online,
        'is_on_call': request.user.is_on_call,
        'message': f"Agent availability set to {'Online' if request.user.is_online else 'Offline'}"
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """Logout user and invalidate token"""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass

    UserActivity.objects.create(user=request.user, activity_type='logout')
    request.user.is_online = False
    request.user.is_on_call = False
    request.user.save(update_fields=['is_online', 'is_on_call'])

    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current logged in user/agent state.
    Essential for mobile app bootstrap: returns user, profile, role, coins, wallet, and unread notifications in 1 call.
    """
    user = request.user
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'name': user.username,
            'age': 20 if user.is_staff else 18,
            'gender': 'female' if user.is_staff else 'other',
            'phone_number': user.phone_number or '',
            'bio': ''
        }
    )

    wallet, _ = Wallet.objects.get_or_create(user=user)

    audiences = ['all', 'agents' if user.is_staff else 'users']
    unread_notifications = Notification.objects.filter(
        Q(recipient=user) | Q(target_audience__in=audiences)
    ).exclude(read_by=user).count()

    response_data = {
        'status': 'success',
        'role': 'agent' if user.is_staff else 'user',
        'is_agent': bool(user.is_staff),
        'agent_status': user.agent_status if user.is_staff else None,
        'user': UserSerializer(user).data,
        'profile': ProfileSerializer(profile, context={'request': request}).data,
        'coins': user.coins,
        'wallet_balance': wallet.balance,
        'unread_notifications': unread_notifications,
        'is_online': user.is_online,
        'is_on_call': user.is_on_call
    }

    if user.is_staff:
        today = timezone.localdate()
        daily_completed = CallHistory.objects.filter(receiver=user, status='completed', start_time__date=today).count()
        config = AgentTaskConfig.load()
        response_data['agent_stats'] = {
            'today_completed_calls': daily_completed,
            'daily_call_target': config.daily_call_target,
            'rating': 4.9
        }

    return Response(response_data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def user_profile(request):
    """
    Get, update, or delete user profile.
    Prioritizes authenticated request.user, falls back to ?username=.
    Supports JSON and multipart/form-data with image upload.
    """
    user = None
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    elif request.user and request.user.is_authenticated:
        user = request.user
    else:
        return Response({"error": "Authentication credentials were not provided, or username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'name': user.username,
            'age': 18,
            'gender': 'other',
            'phone_number': user.phone_number or '',
            'bio': ''
        }
    )

    if request.method == 'GET':
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response({
            'status': 'success',
            'profile': serializer.data,
            'coins': user.coins,
            'is_online': user.is_online,
            'is_on_call': user.is_on_call,
            'role': 'agent' if user.is_staff else 'user'
        })

    # Ensure write operations are strictly authenticated and authorized
    if not (request.user and request.user.is_authenticated and (request.user == user or request.user.is_superuser)):
        return Response({'error': 'Unauthorized to modify this profile'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        # App Store / Play Store account deletion compliance
        user.is_active = False
        user.is_online = False
        user.is_on_call = False
        user.save(update_fields=['is_active', 'is_online', 'is_on_call'])
        try:
            user.auth_token.delete()
        except Exception:
            pass
        UserActivity.objects.create(user=user, activity_type='account_deletion')
        return Response({
            'status': 'success',
            'message': 'Account has been deactivated successfully.'
        })

    elif request.method in ['PUT', 'PATCH']:
        new_email = request.data.get('email')
        if new_email:
            new_email = str(new_email).strip().lower()
            if new_email.endswith('@gmail.com'):
                user.email = new_email
                user.save(update_fields=['email'])

        serializer = ProfileCreateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully',
                'profile': ProfileSerializer(profile, context={'request': request}).data,
                'user': UserSerializer(user).data
            })
        return _format_error_response(serializer.errors)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """
    Dedicated avatar upload endpoint for both User App and Agent App.
    Accepts multipart/form-data under 'avatar', 'image', or 'profile_picture'.
    """
    serializer = AvatarUploadSerializer(data=request.FILES)
    if not serializer.is_valid():
        serializer = AvatarUploadSerializer(data=request.data)

    if serializer.is_valid():
        file_obj = serializer.validated_data['file']
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.profile_picture = file_obj
        profile.save()

        avatar_url = request.build_absolute_uri(profile.profile_picture.url)
        return Response({
            'status': 'success',
            'message': 'Avatar uploaded successfully',
            'avatar_url': avatar_url,
            'profile': ProfileSerializer(profile, context={'request': request}).data
        })
    return _format_error_response(serializer.errors)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated user or agent.
    Requires 'old_password' and 'new_password'.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if request.user.has_usable_password() and not request.user.check_password(old_password):
            return Response({'error': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()

        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        token, _ = Token.objects.get_or_create(user=request.user)

        UserActivity.objects.create(user=request.user, activity_type='password_change')
        return Response({
            'status': 'success',
            'token': token.key,
            'message': 'Password changed successfully.'
        })
    return _format_error_response(serializer.errors)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password with 10-digit phone number and OTP (Forgot Password).
    Requires 'phone_number', 'otp', and 'new_password'.
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        new_password = serializer.validated_data['new_password']

        user = User.objects.filter(Q(phone_number=phone_number) | Q(username=phone_number)).first()
        if not user:
            return Response({'error': 'No account found with this 10-digit number.'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()

        try:
            user.auth_token.delete()
        except Exception:
            pass
        token, _ = Token.objects.get_or_create(user=user)

        UserActivity.objects.create(user=user, activity_type='password_reset')
        return Response({
            'status': 'success',
            'token': token.key,
            'role': 'agent' if user.is_staff else 'user',
            'message': 'Password reset successfully. You are now logged in.'
        })
    return _format_error_response(serializer.errors)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Delete or deactivate current user's account.
    Fulfills Apple & Google Play Store account deletion requirements.
    """
    user = request.user
    user.is_active = False
    user.is_online = False
    user.is_on_call = False
    user.save(update_fields=['is_active', 'is_online', 'is_on_call'])

    try:
        user.auth_token.delete()
    except Exception:
        pass

    UserActivity.objects.create(user=user, activity_type='account_deletion')
    return Response({
        'status': 'success',
        'message': 'Your account has been deleted successfully.'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_profile(request, user_id):
    """Get another user or agent's public profile details"""
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        profile = getattr(user, 'profile', None)
        if not profile:
            profile, _ = Profile.objects.get_or_create(user=user, defaults={'name': user.username, 'age': 18, 'gender': 'other'})

        profile_data = ProfileSerializer(profile, context={'request': request}).data
        response_data = {
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_online': user.is_online,
                'is_on_call': user.is_on_call,
                'role': 'agent' if user.is_staff else 'user',
                'is_agent': user.is_staff,
                'profile': profile_data
            }
        }

        if user.is_staff:
            completed_calls = CallHistory.objects.filter(receiver=user, status='completed').count()
            response_data['agent_info'] = {
                'calls_completed': completed_calls,
                'rating': 4.9,
                'agent_status': user.agent_status
            }

        return Response(response_data)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

get_agent_detail = get_user_profile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_status(request):
    """Update user online/on-call status"""
    status_type = request.data.get('status_type')
    is_active = request.data.get('is_active', True)

    if status_type == 'online':
        request.user.is_online = is_active
    elif status_type == 'on_call':
        request.user.is_on_call = is_active
        activity_type = 'call_start' if is_active else 'call_end'
        UserActivity.objects.create(user=request.user, activity_type=activity_type)
    else:
        return Response({'error': 'Invalid status type. Use "online" or "on_call"'}, status=status.HTTP_400_BAD_REQUEST)

    request.user.save()
    return Response({
        'message': f'Status updated: {status_type} = {is_active}',
        'user': UserSerializer(request.user).data
    })

# Menu Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def menu_items(request):
    return Response({
        'profile': {'title': 'My Profile', 'endpoint': '/api/profile/'},
        'terms_conditions': {'title': 'Terms & Conditions', 'endpoint': '/api/terms-conditions/'},
        'privacy_policy': {'title': 'Privacy Policy', 'endpoint': '/api/privacy-policy/'},
        'help_line': {'title': 'Help Line', 'endpoint': '/api/help-line/'},
        'logout': {'title': 'Logout', 'endpoint': '/api/logout/'}
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_terms_conditions(request):
    terms = TermsAndConditions.objects.filter(is_active=True).order_by('-created_at')
    if terms.exists():
        return Response(TermsAndConditionsSerializer(terms.first()).data)
    return Response({'error': 'No active terms found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_privacy_policy(request):
    policies = PrivacyPolicy.objects.filter(is_active=True).order_by('-created_at')
    if policies.exists():
        return Response(PrivacyPolicySerializer(policies.first()).data)
    return Response({'error': 'No active privacy policy found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_help_line(request):
    help_lines = HelpLine.objects.filter(is_active=True).order_by('-created_at')
    if help_lines.exists():
        return Response(HelpLineSerializer(help_lines.first()).data)
    return Response({'error': 'No active help line found'}, status=status.HTTP_404_NOT_FOUND)

# User Listing Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_online_users(request):
    online_users = User.objects.filter(is_online=True).exclude(id=request.user.id)
    return Response(OnlineUserSerializer(online_users, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_on_call_users(request):
    on_call_users = User.objects.filter(is_on_call=True).exclude(id=request.user.id)
    return Response(OnCallUserSerializer(on_call_users, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size

    paginated_users = users[start:end]
    return Response({
        'users': OnlineUserSerializer(paginated_users, many=True).data,
        'total': users.count(),
        'page': page,
        'page_size': page_size
    })

# Coins, Offers, & Calling APIs
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_coins(request):
    """
    Get coin balance for user or agent.
    Prioritizes authenticated request.user, falls back to ?username=.
    Returns coins, wallet balance, and recent coin transactions.
    """
    user = None
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    elif request.user and request.user.is_authenticated:
        user = request.user
    else:
        return Response({"error": "Authentication credentials were not provided, or username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    wallet, _ = Wallet.objects.get_or_create(user=user)
    recent_transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:20]

    return Response({
        'status': 'success',
        'coins': user.coins,
        'wallet_balance': wallet.balance,
        'user_id': user.id,
        'username': user.username,
        'role': 'agent' if user.is_staff else 'user',
        'is_agent': bool(user.is_staff),
        'transactions': TransactionSerializer(recent_transactions, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_coins(request):
    """
    Add coins to user account (e.g. from in-app purchase, payment gateway webhook, or top-up).
    Accepts 'coins' or 'amount' (int or numeric str), plus optional 'reference_id' or 'transaction_id'.
    """
    raw_coins = request.data.get('coins')
    if raw_coins is None:
        raw_coins = request.data.get('amount')

    try:
        coins_to_add = int(raw_coins)
    except (TypeError, ValueError):
        return Response({'error': 'Please provide a valid positive number of coins'}, status=status.HTTP_400_BAD_REQUEST)

    if coins_to_add <= 0:
        return Response({'error': 'Please provide a valid positive number of coins'}, status=status.HTTP_400_BAD_REQUEST)

    reference_id = request.data.get('reference_id') or request.data.get('transaction_id') or request.data.get('payment_id')

    request.user.coins += coins_to_add
    request.user.save(update_fields=['coins'])

    # Record financial transaction
    transaction = Transaction.objects.create(
        user=request.user,
        amount=coins_to_add,
        transaction_type='coin_purchase',
        reference_id=str(reference_id) if reference_id else None
    )

    UserActivity.objects.create(user=request.user, activity_type=f'coins_added_{coins_to_add}')

    return Response({
        'status': 'success',
        'message': f'{coins_to_add} coins added successfully',
        'coins_added': coins_to_add,
        'new_balance': request.user.coins,
        'transaction_id': transaction.id,
        'reference_id': transaction.reference_id
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deduct_coins(request):
    """
    Deduct coins from user account.
    Accepts 'coins' or 'amount' (int or numeric str).
    """
    raw_coins = request.data.get('coins')
    if raw_coins is None:
        raw_coins = request.data.get('amount')

    try:
        coins_to_deduct = int(raw_coins)
    except (TypeError, ValueError):
        return Response({'error': 'Please provide a valid positive number of coins'}, status=status.HTTP_400_BAD_REQUEST)

    if coins_to_deduct <= 0:
        return Response({'error': 'Please provide a valid positive number of coins'}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.coins < coins_to_deduct:
        return Response({
            'error': 'Insufficient coins balance',
            'current_balance': request.user.coins,
            'required': coins_to_deduct
        }, status=status.HTTP_400_BAD_REQUEST)

    request.user.coins -= coins_to_deduct
    request.user.save(update_fields=['coins'])

    UserActivity.objects.create(user=request.user, activity_type=f'coins_deducted_{coins_to_deduct}')
    return Response({
        'status': 'success',
        'message': f'{coins_to_deduct} coins deducted successfully',
        'coins_deducted': coins_to_deduct,
        'new_balance': request.user.coins
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_offers(request):
    active_offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).order_by('-created_at')
    return Response(OfferSerializer(active_offers, many=True).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_offer_detail(request, offer_id):
    try:
        offer = Offer.objects.get(id=offer_id, is_active=True)
        return Response(OfferSerializer(offer).data)
    except Offer.DoesNotExist:
        return Response({'error': 'Offer not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_offer(request, offer_id):
    try:
        offer = Offer.objects.get(id=offer_id, is_active=True)
        now = timezone.now()
        if now < offer.start_date or now > offer.end_date:
            return Response({'error': 'Offer is not currently active'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.coins += offer.coin_value
        request.user.save()
        UserActivity.objects.create(user=request.user, activity_type=f'offer_redeemed_{offer.id}')

        return Response({
            'message': f'Offer redeemed successfully! {offer.coin_value} coins added',
            'new_balance': request.user.coins,
            'offer': OfferSerializer(offer).data
        })
    except Offer.DoesNotExist:
        return Response({'error': 'Offer not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    """Update or register device FCM token for push notifications"""
    fcm_token = request.data.get('fcm_token') or request.data.get('token')
    if not fcm_token:
        return Response({'error': 'fcm_token is required'}, status=status.HTTP_400_BAD_REQUEST)

    fcm_token = str(fcm_token).strip()
    # Disassociate this token from any other user to prevent cross-account delivery
    User.objects.filter(fcm_token=fcm_token).exclude(id=request.user.id).update(fcm_token=None)

    request.user.fcm_token = fcm_token
    request.user.save(update_fields=['fcm_token'])
    return Response({
        'status': 'success',
        'message': 'FCM token updated successfully',
        'fcm_token': fcm_token
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Fetch notifications for current user/agent (both specific and broadcast)"""
    user = request.user
    if user.is_staff:
        audiences = ['all', 'agents']
    else:
        audiences = ['all', 'users']

    notifications = Notification.objects.filter(
        Q(recipient=user) | Q(target_audience__in=audiences)
    ).prefetch_related('read_by').order_by('-created_at')[:50]

    data = []
    unread_count = 0
    for n in notifications:
        is_read = n.read_by.filter(id=user.id).exists()
        if not is_read:
            unread_count += 1
        data.append({
            'id': n.id,
            'title': n.title,
            'body': n.body,
            'image_url': n.image_url,
            'target_audience': n.target_audience,
            'is_read': is_read,
            'created_at': n.created_at.isoformat(),
        })

    return Response({
        'count': len(data),
        'unread_count': unread_count,
        'notifications': data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    notification.read_by.add(request.user)
    return Response({'status': 'success', 'message': 'Notification marked as read'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read(request):
    """Mark all eligible notifications as read for current user/agent"""
    user = request.user
    if user.is_staff:
        audiences = ['all', 'agents']
    else:
        audiences = ['all', 'users']

    notifications = Notification.objects.filter(
        Q(recipient=user) | Q(target_audience__in=audiences)
    )
    for n in notifications:
        n.read_by.add(user)

    return Response({'status': 'success', 'message': 'All notifications marked as read'})


@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_call(request):
    """
    Initiate an audio/video call.
    Caller: Authenticated user preferred, fallback to username in payload.
    Receiver: receiver_id or receiver_username.
    """
    username = request.data.get('username')
    receiver_id = request.data.get('receiver_id')
    receiver_username = request.data.get('receiver_username')
    call_type = request.data.get('call_type', 'video')

    if request.user and request.user.is_authenticated:
        caller = request.user
    elif username:
        try:
            caller = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Caller not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'Authentication or caller username is required'}, status=status.HTTP_400_BAD_REQUEST)

    if receiver_id:
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response({'error': 'Receiver not found'}, status=status.HTTP_404_NOT_FOUND)
    elif receiver_username:
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return Response({'error': 'Receiver not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'receiver_id or receiver_username is required'}, status=status.HTTP_400_BAD_REQUEST)

    if caller.id == receiver.id:
        return Response({'error': 'Cannot initiate a call with yourself'}, status=status.HTTP_400_BAD_REQUEST)

    # Balance check for customer calling an agent
    if not caller.is_staff and caller.coins < 10:
        return Response({
            'error': 'Insufficient coin balance to initiate a call. Please recharge your coins.',
            'coins': caller.coins
        }, status=status.HTTP_402_PAYMENT_REQUIRED)

    channel_name = str(uuid.uuid4())
    call = CallHistory.objects.create(
        caller=caller,
        receiver=receiver,
        channel_name=channel_name,
        call_type=call_type,
        status='initiated'
    )

    app_id = getattr(settings, 'AGORA_APP_ID', '')
    app_certificate = getattr(settings, 'AGORA_APP_CERTIFICATE', '')
    role = 1
    expiration_time_in_seconds = 3600 * 24
    current_timestamp = int(timezone.now().timestamp())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds

    token = ""
    try:
        if 'RtcTokenBuilder' in globals():
            token = RtcTokenBuilder.buildTokenWithUid(
                app_id, app_certificate, channel_name, caller.id, role, privilege_expired_ts
            )
    except Exception as e:
        return Response({'error': f'Failed to generate Agora token: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Send incoming call push notification to agent/receiver
    if receiver.fcm_token and 'messaging' in globals():
        try:
            caller_name = getattr(caller, 'profile', None) and caller.profile.name or caller.username
            message = messaging.Message(
                data={
                    'type': 'incoming_call',
                    'call_id': str(call.id),
                    'channel_name': channel_name,
                    'caller_id': str(caller.id),
                    'caller_name': str(caller_name),
                    'call_type': str(call_type)
                },
                token=receiver.fcm_token
            )
            messaging.send(message)
        except Exception as e:
            print(f"Failed to send incoming call FCM: {e}")

    return Response({
        'call_id': call.id,
        'channel_name': channel_name,
        'token': token,
        'uid': caller.id,
        'caller': {
            'id': caller.id,
            'username': caller.username,
            'coins': caller.coins
        },
        'receiver': {
            'id': receiver.id,
            'username': receiver.username,
            'is_online': receiver.is_online,
            'is_on_call': receiver.is_on_call
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def update_call_status(request, call_id):
    """
    Update call status (accepted, completed, rejected, cancelled, missed).
    Caller or receiver can update. Prioritizes authenticated request.user.
    """
    username = request.data.get('username')
    new_status = request.data.get('status')

    valid_statuses = [c[0] for c in CallHistory.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response({'error': f'Invalid status. Allowed: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        call = CallHistory.objects.select_related('caller', 'receiver').get(id=call_id)
    except CallHistory.DoesNotExist:
        return Response({'error': 'Call not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user and request.user.is_authenticated:
        user = request.user
    elif username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'Authentication or username is required'}, status=status.HTTP_400_BAD_REQUEST)

    if user.id != call.caller.id and user.id != call.receiver.id:
        return Response({'error': 'Unauthorized to update this call'}, status=status.HTTP_403_FORBIDDEN)

    call.status = new_status

    # Toggle on-call states
    if new_status == 'accepted':
        call.receiver.is_on_call = True
        call.caller.is_on_call = True
        call.receiver.save(update_fields=['is_on_call'])
        call.caller.save(update_fields=['is_on_call'])

        # Notify caller that agent accepted the call
        if call.caller.fcm_token and 'messaging' in globals():
            try:
                messaging.send(messaging.Message(
                    data={
                        'type': 'call_accepted',
                        'call_id': str(call.id),
                        'channel_name': call.channel_name,
                    },
                    token=call.caller.fcm_token
                ))
            except Exception:
                pass

    elif new_status in ['completed', 'rejected', 'cancelled', 'missed']:
        call.receiver.is_on_call = False
        call.caller.is_on_call = False
        call.receiver.save(update_fields=['is_on_call'])
        call.caller.save(update_fields=['is_on_call'])

        target_notify = call.caller if user.id == call.receiver.id else call.receiver
        if target_notify.fcm_token and 'messaging' in globals():
            try:
                messaging.send(messaging.Message(
                    data={
                        'type': f'call_{new_status}',
                        'call_id': str(call.id),
                        'status': new_status,
                    },
                    token=target_notify.fcm_token
                ))
            except Exception:
                pass

    if new_status == 'completed' and not call.end_time:
        call.end_time = timezone.now()

        # Reward the agent
        if call.receiver.is_staff:
            try:
                reward_setting = GlobalSetting.objects.get(key='call_reward_amount')
                reward_amount = reward_setting.get_typed_value()
            except GlobalSetting.DoesNotExist:
                reward_amount = 0

            if reward_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=call.receiver)
                wallet.balance += reward_amount
                wallet.save()

                Transaction.objects.create(
                    user=call.receiver,
                    amount=reward_amount,
                    transaction_type='earn_call',
                    reference_id=str(call.id)
                )
                call.coins_earned = reward_amount

    call.save()
    response_data = {'message': f'Call status updated to {new_status}'}

    if new_status == 'completed' and call.end_time:
        duration_seconds = (call.end_time - call.start_time).total_seconds()
        duration_minutes = int(duration_seconds // 60)
        duration_seconds_remainder = int(duration_seconds % 60)

        caller_wallet, _ = Wallet.objects.get_or_create(user=call.caller)
        receiver_wallet, _ = Wallet.objects.get_or_create(user=call.receiver)

        response_data.update({
            'call_duration': {
                'seconds': int(duration_seconds),
                'formatted': f"{duration_minutes}m {duration_seconds_remainder}s"
            },
            'caller_balance': caller_wallet.balance,
            'receiver_balance': receiver_wallet.balance,
            'coins_earned': call.coins_earned
        })

    # If accepted, generate receiver token to join Agora channel
    if new_status == 'accepted':
        app_id = getattr(settings, 'AGORA_APP_ID', '')
        app_certificate = getattr(settings, 'AGORA_APP_CERTIFICATE', '')
        role = 1
        expiration_time_in_seconds = 3600 * 24
        privilege_expired_ts = int(timezone.now().timestamp()) + expiration_time_in_seconds

        try:
            if 'RtcTokenBuilder' in globals():
                token = RtcTokenBuilder.buildTokenWithUid(
                    app_id, app_certificate, call.channel_name, user.id, role, privilege_expired_ts
                )
                response_data['token'] = token
                response_data['channel_name'] = call.channel_name
                response_data['uid'] = user.id
        except Exception as e:
            print(f"Failed to generate receiver token: {e}")

    return Response(response_data)




@api_view(['GET'])
@permission_classes([AllowAny])
def get_call_history(request):
    """
    Get call history for current user or agent.
    Prioritizes authenticated request.user, falls back to ?username=.
    Supports filters:
      - ?type=incoming | outgoing (default: all)
      - ?call_type=video | audio
      - ?status=completed | missed | rejected | accepted | cancelled
      - ?page=1 & ?page_size=20 (optional pagination)
    """
    user = None
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    elif request.user and request.user.is_authenticated:
        user = request.user
    else:
        return Response({"error": "Authentication credentials were not provided, or username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Filter by incoming vs outgoing vs all
    call_filter = request.GET.get('type')
    if call_filter == 'incoming':
        calls = CallHistory.objects.filter(receiver=user)
    elif call_filter == 'outgoing':
        calls = CallHistory.objects.filter(caller=user)
    else:
        calls = CallHistory.objects.filter(Q(caller=user) | Q(receiver=user))

    # Optional status filter (e.g. ?status=completed or ?status=missed)
    call_status = request.GET.get('status')
    if call_status:
        calls = calls.filter(status=call_status)

    # Optional call_type filter (e.g. ?call_type=video or ?call_type=audio)
    call_type = request.GET.get('call_type')
    if call_type:
        calls = calls.filter(call_type=call_type)

    calls = calls.select_related(
        'caller', 'receiver', 'caller__profile', 'receiver__profile'
    ).order_by('-start_time')

    # Optional pagination
    page = request.GET.get('page')
    page_size = request.GET.get('page_size') or request.GET.get('limit')
    if page or page_size:
        try:
            page = int(page or 1)
            page_size = int(page_size or 20)
            start = (page - 1) * page_size
            end = start + page_size
            total = calls.count()
            paginated = calls[start:end]
            serializer = CallHistorySerializer(paginated, many=True, context={'request': request})
            return Response({
                'status': 'success',
                'total': total,
                'page': page,
                'page_size': page_size,
                'calls': serializer.data
            })
        except ValueError:
            pass

    serializer = CallHistorySerializer(calls, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def agent_dashboard(request):
    """
    Returns Agent specific dashboard data including task targets vs completion.
    Accessible via Token authentication or ?username= query parameter.
    """
    user = None
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username, is_staff=True)
        except User.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
    elif request.user and request.user.is_authenticated:
        if not request.user.is_staff:
            return Response({"error": "Unauthorized. Agent access only."}, status=status.HTTP_403_FORBIDDEN)
        user = request.user
    else:
        return Response({"error": "Authentication credentials were not provided, or username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    config = AgentTaskConfig.load()

    # Get all completed calls where this agent was the receiver
    # (assuming agents are the ones receiving calls on the platform)
    completed_calls = CallHistory.objects.filter(
        receiver=user,
        status='completed'
    )

    # Today's stats
    today = timezone.now().date()
    daily_completed = completed_calls.filter(start_time__date=today).count()

    # Week's stats (assuming week starts on Monday)
    start_of_week = today - timedelta(days=today.weekday())
    weekly_completed = completed_calls.filter(start_time__date__gte=start_of_week).count()

    # Month's stats
    start_of_month = today.replace(day=1)
    monthly_completed = completed_calls.filter(start_time__date__gte=start_of_month).count()

    # Calculate durations from start_time and end_time
    total_duration = sum((call.end_time - call.start_time).total_seconds() for call in completed_calls if call.end_time) or 0
    today_duration = sum((call.end_time - call.start_time).total_seconds() for call in completed_calls.filter(start_time__date=today) if call.end_time) or 0

    # Get wallet balance
    wallet, _ = Wallet.objects.get_or_create(user=user)

    # Get total earnings from transactions
    total_earnings = Transaction.objects.filter(
        user=user,
        transaction_type='earn_call'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get today's earnings
    today_earnings = Transaction.objects.filter(
        user=user,
        transaction_type='earn_call',
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate success rate (completed calls vs total calls received)
    total_calls_received = CallHistory.objects.filter(receiver=user).count()
    success_rate = int((daily_completed / total_calls_received * 100)) if total_calls_received > 0 else 0

    # Format duration to hours and minutes
    def format_duration(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    return Response({
        "status": "success",
        "agent": {
            "username": user.username,
            "coins_earned": user.coins,
            "wallet_balance": wallet.balance,
            "total_earnings": total_earnings,
            "today_earnings": today_earnings,
            "total_duration_seconds": total_duration,
            "today_duration_seconds": today_duration,
            "total_duration_formatted": format_duration(total_duration),
            "today_duration_formatted": format_duration(today_duration),
            "calls_completed": daily_completed,
            "success_rate": success_rate,
            "agent_rating": 4.9  # Default rating - can be enhanced with rating system
        },
        "tasks": {
            "daily": {
                "completed": daily_completed,
                "target": config.daily_call_target,
                "progress_percentage": min(100, int((daily_completed / config.daily_call_target) * 100)) if config.daily_call_target else 0
            },
            "weekly": {
                "completed": weekly_completed,
                "target": config.weekly_call_target,
                "progress_percentage": min(100, int((weekly_completed / config.weekly_call_target) * 100)) if config.weekly_call_target else 0
            },
            "monthly": {
                "completed": monthly_completed,
                "target": config.monthly_call_target,
                "progress_percentage": min(100, int((monthly_completed / config.monthly_call_target) * 100)) if config.monthly_call_target else 0
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_wallet(request):
    user = request.user
    if not user.is_staff:
        return Response({"error": "Unauthorized. Agent access only."}, status=status.HTTP_403_FORBIDDEN)

    wallet, _ = Wallet.objects.get_or_create(user=user)
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')

    return Response({
        "status": "success",
        "wallet": WalletSerializer(wallet).data,
        "history": TransactionSerializer(transactions, many=True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_withdrawal(request):
    user = request.user
    if not user.is_staff:
        return Response({"error": "Unauthorized. Agent access only."}, status=status.HTTP_403_FORBIDDEN)

    amount = request.data.get('amount')
    if not amount:
        return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = int(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    wallet, _ = Wallet.objects.get_or_create(user=user)

    try:
        min_amount_setting = GlobalSetting.objects.get(key='withdrawal_min_amount')
        min_amount = min_amount_setting.get_typed_value()
    except GlobalSetting.DoesNotExist:
        min_amount = 500

    if wallet.balance < min_amount:
        return Response({
            "error": f"Insufficient balance. Minimum withdrawal is {min_amount} coins.",
            "min_amount": min_amount,
            "current_balance": wallet.balance
        }, status=status.HTTP_400_BAD_REQUEST)

    if amount > wallet.balance:
        return Response({"error": "Requested amount exceeds balance"}, status=status.HTTP_400_BAD_REQUEST)

    wallet.balance -= amount
    wallet.save()

    request_obj = WithdrawalRequest.objects.create(
        agent=user,
        amount=amount,
        status='pending'
    )

    Transaction.objects.create(
        user=user,
        amount=-amount,
        transaction_type='withdrawal',
        reference_id=str(request_obj.id)
    )

    return Response({
        "status": "success",
        "message": "Withdrawal request submitted successfully",
        "remaining_balance": wallet.balance
    })





@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([AllowAny])
def agent_profile(request):
    """
    Get or update agent profile.
    Prioritizes authenticated request.user (must be is_staff=True), falls back to ?username=.
    Supports PUT/PATCH to update name, age, bio, profile_picture.
    """
    user = None
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username, is_staff=True)
        except User.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
    elif request.user and request.user.is_authenticated:
        if not request.user.is_staff:
            return Response({"error": "Unauthorized. Agent access only."}, status=status.HTTP_403_FORBIDDEN)
        user = request.user
    else:
        return Response({"error": "Authentication credentials were not provided, or username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Get or create profile
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'name': user.username,
            'age': 20,
            'gender': 'female',
            'phone_number': user.phone_number or '',
            'bio': ''
        }
    )

    if request.method in ['PUT', 'PATCH']:
        if not (request.user and request.user.is_authenticated and (request.user == user or request.user.is_superuser)):
            return Response({'error': 'Unauthorized to update this profile'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProfileCreateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Agent profile updated successfully',
                'profile': ProfileSerializer(profile).data
            })
        return _format_error_response(serializer.errors)

    serializer = ProfileSerializer(profile)
    wallet, _ = Wallet.objects.get_or_create(user=user)

    completed_calls = CallHistory.objects.filter(receiver=user, status='completed').count()
    total_earnings = Transaction.objects.filter(
        user=user,
        transaction_type='earn_call'
    ).aggregate(total=Sum('amount'))['total'] or 0

    return Response({
        'status': 'success',
        'profile': serializer.data,
        'wallet_balance': wallet.balance,
        'total_earnings': total_earnings,
        'calls_completed': completed_calls,
        'is_online': user.is_online,
        'is_on_call': user.is_on_call,
        'agent_status': user.agent_status
    })




@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_agents(request):
    """Get list of all approved agents with full profile info for User App"""
    agents = User.objects.filter(is_staff=True, agent_status='approved').select_related('profile')

    serializer_data = []
    for agent in agents:
        agent_data = {
            'id': agent.id,
            'username': agent.username,
            'email': agent.email,
            'phone_number': agent.phone_number,
            'is_online': agent.is_online,
            'is_on_call': agent.is_on_call,
            'coins': agent.coins,
            'profile': None
        }
        if hasattr(agent, 'profile') and agent.profile:
            pic_url = request.build_absolute_uri(agent.profile.profile_picture.url) if agent.profile.profile_picture else None
            agent_data['profile'] = {
                'name': agent.profile.name,
                'age': agent.profile.age,
                'gender': agent.profile.gender,
                'bio': agent.profile.bio,
                'profile_picture': pic_url,
                'is_verified': agent.profile.is_verified
            }
        serializer_data.append(agent_data)

    return Response({
        'status': 'success',
        'agents': serializer_data,
        'count': len(serializer_data)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_agent(request):
    """Submit an application to become an agent"""
    from .models import AgentApplication
    from .serializers import AgentApplicationCreateSerializer

    # Check if user already has an application
    if AgentApplication.objects.filter(user=request.user).exists():
        return Response({
            'error': 'You already have an agent application submitted'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if user is already an agent
    if request.user.is_staff:
        return Response({
            'error': 'You are already an agent'
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = AgentApplicationCreateSerializer(data=request.data)
    if serializer.is_valid():
        application = AgentApplication.objects.create(
            user=request.user,
            **serializer.validated_data
        )

        # Log the application
        UserActivity.objects.create(
            user=request.user,
            activity_type='agent_application'
        )

        return Response({
            'message': 'Agent application submitted successfully',
            'application_id': application.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_agent_application(request):
    """Get current user's agent application status"""
    from .models import AgentApplication
    from .serializers import AgentApplicationSerializer

    try:
        application = AgentApplication.objects.get(user=request.user)
        serializer = AgentApplicationSerializer(application)
        return Response(serializer.data)
    except AgentApplication.DoesNotExist:
        return Response({
            'message': 'No agent application found'
        }, status=status.HTTP_404_NOT_FOUND)










