import io
import calendar
from datetime import timedelta, date
# pyrefly: ignore[missing-import]
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import (
    User, Profile, Offer, CallHistory, Wallet, Transaction,
    WithdrawalRequest, AgentApplication, Notification, AgentTaskConfig, GlobalSetting
)
from .admin_api_serializers import (
    AdminLoginSerializer, AdminUserSummarySerializer, AdminProfileSerializer,
    AdminUserListSerializer, AdminUserDetailSerializer, AdminCoinAdjustmentSerializer,
    AdminUserStatusUpdateSerializer, AdminAgentCreateSerializer, AdminAgentStatusSerializer,
    AdminAgentApplicationSerializer, AdminApplicationReviewSerializer,
    AdminWithdrawalSerializer, AdminWithdrawalReviewSerializer,
    AdminCallHistorySerializer, AdminTransactionSerializer, AdminOfferSerializer,
    AdminAgentTaskConfigSerializer, AdminGlobalSettingSerializer,
    AdminNotificationSerializer, AdminNotificationBroadcastSerializer
)
from .fcm_service import get_fcm_stats, send_fcm_notification
from .pdf_utils import generate_agent_paysheet_pdf


class IsSuperAdminUser(permissions.BasePermission):
    """
    Allows access only to superusers and staff administrators.
    Regular female agents (is_staff=True with agent_status) are excluded.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        # Staff users who are not registered agents
        if user.is_staff and not hasattr(user, 'agent_application') and user.agent_status not in ('approved', 'pending'):
            return True
        return False


def _paginate(queryset, request, default_page_size=20, max_page_size=100):
    """Helper to paginate any queryset with standard structure."""
    try:
        page = int(request.GET.get('page', 1) or 1)
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(request.GET.get('page_size', default_page_size) or default_page_size)
    except (ValueError, TypeError):
        page_size = default_page_size

    page_size = min(max(1, page_size), max_page_size)
    paginator = Paginator(queryset, page_size)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
        page = 1
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages) if paginator.num_pages > 0 else []
        page = paginator.num_pages if paginator.num_pages > 0 else 1

    return {
        'page': page,
        'page_size': page_size,
        'total': paginator.count,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next() if hasattr(page_obj, 'has_next') else False,
        'has_previous': page_obj.has_previous() if hasattr(page_obj, 'has_previous') else False,
        'items': page_obj.object_list if hasattr(page_obj, 'object_list') else list(page_obj),
    }


def _months_active(joined_date, today):
    """Number of calendar months (inclusive) an agent has been on the platform."""
    months = (today.year - joined_date.year) * 12 + (today.month - joined_date.month) + 1
    return max(1, months)


# ==============================================================================
# 1. ADMIN AUTHENTICATION
# ==============================================================================

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def admin_login(request):
    """
    Authenticate superadmin/staff administrator.
    Returns Auth Token and administrator info.
    """
    serializer = AdminLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'status': 'success',
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
            },
            'message': 'Admin login successful.'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_logout(request):
    """Logout admin by invalidating token."""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({'status': 'success', 'message': 'Admin logged out successfully.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_me(request):
    """Get currently logged-in administrator's profile."""
    user = request.user
    return Response({
        'status': 'success',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 2. DASHBOARD & ANALYTICS
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_dashboard_stats(request):
    """
    Comprehensive dashboard statistics for the entire platform:
    - Users (clients) metrics
    - Agents metrics & status breakdown
    - Agent applications
    - Withdrawals
    - Calling statistics
    - Financial coin flows & transactions
    - Recent calls and pending queues
    """
    today = timezone.localdate()
    now = timezone.now()
    start_of_today = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    start_of_week = start_of_today - timedelta(days=today.weekday())
    start_of_month = timezone.make_aware(timezone.datetime(today.year, today.month, 1))

    # 1. Regular Users
    users_qs = User.objects.filter(is_superuser=False, is_staff=False)
    total_users = users_qs.count()
    online_users = users_qs.filter(is_online=True).count()
    users_new_today = users_qs.filter(date_joined__gte=start_of_today).count()
    users_new_this_week = users_qs.filter(date_joined__gte=start_of_week).count()
    users_new_this_month = users_qs.filter(date_joined__gte=start_of_month).count()

    # 2. Agents
    agents_qs = User.objects.filter(is_superuser=False, is_staff=True)
    total_agents = agents_qs.count()
    online_agents = agents_qs.filter(is_online=True).count()
    approved_agents = agents_qs.filter(agent_status='approved').count()
    pending_agents = agents_qs.filter(agent_status='pending').count()
    suspended_agents = agents_qs.filter(agent_status='suspended').count()
    terminated_agents = agents_qs.filter(agent_status='terminated').count()

    # 3. Agent Applications
    apps_qs = AgentApplication.objects.all()
    total_applications = apps_qs.count()
    pending_applications = apps_qs.filter(status='pending').count()
    approved_applications = apps_qs.filter(status='approved').count()
    rejected_applications = apps_qs.filter(status='rejected').count()

    # 4. Withdrawals
    with_qs = WithdrawalRequest.objects.all()
    total_withdrawals = with_qs.count()
    pending_withdrawals = with_qs.filter(status='pending').count()
    approved_withdrawals = with_qs.filter(status='approved').count()
    rejected_withdrawals = with_qs.filter(status='rejected').count()
    pending_coins = with_qs.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
    approved_coins = with_qs.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0

    # 5. Calls
    calls_qs = CallHistory.objects.all()
    total_calls = calls_qs.count()
    completed_calls = calls_qs.filter(status='completed').count()
    missed_calls = calls_qs.filter(status='missed').count()
    rejected_calls = calls_qs.filter(status='rejected').count()
    active_ongoing_calls = calls_qs.filter(status__in=['initiated', 'accepted']).count()
    calls_today = calls_qs.filter(start_time__gte=start_of_today).count()

    # Sum duration of completed calls
    completed_calls_qs = calls_qs.filter(status='completed', end_time__isnull=False)
    total_duration_seconds = sum(c.duration for c in completed_calls_qs)
    total_coins_earned_calls = calls_qs.aggregate(total=Sum('coins_earned'))['total'] or 0

    # 6. Transactions summary
    tx_qs = Transaction.objects.all()
    total_transactions = tx_qs.count()
    coin_purchases_amount = tx_qs.filter(transaction_type='coin_purchase').aggregate(total=Sum('amount'))['total'] or 0
    withdrawals_amount = tx_qs.filter(transaction_type='withdrawal').aggregate(total=Sum('amount'))['total'] or 0

    # 7. Recent Items
    recent_calls = CallHistory.objects.select_related('caller', 'receiver').order_by('-start_time')[:8]
    recent_applications = AgentApplication.objects.select_related('user').filter(status='pending').order_by('-created_at')[:5]
    recent_withdrawals = WithdrawalRequest.objects.select_related('agent').filter(status='pending').order_by('-created_at')[:5]

    return Response({
        'status': 'success',
        'metrics': {
            'users': {
                'total': total_users,
                'online': online_users,
                'new_today': users_new_today,
                'new_this_week': users_new_this_week,
                'new_this_month': users_new_this_month,
            },
            'agents': {
                'total': total_agents,
                'online': online_agents,
                'approved': approved_agents,
                'pending': pending_agents,
                'suspended': suspended_agents,
                'terminated': terminated_agents,
            },
            'agent_applications': {
                'total': total_applications,
                'pending': pending_applications,
                'approved': approved_applications,
                'rejected': rejected_applications,
            },
            'withdrawals': {
                'total': total_withdrawals,
                'pending': pending_withdrawals,
                'approved': approved_withdrawals,
                'rejected': rejected_withdrawals,
                'pending_coins': pending_coins,
                'approved_coins': approved_coins,
            },
            'calls': {
                'total': total_calls,
                'completed': completed_calls,
                'missed': missed_calls,
                'rejected': rejected_calls,
                'ongoing': active_ongoing_calls,
                'today': calls_today,
                'total_duration_seconds': total_duration_seconds,
                'total_coins_earned': total_coins_earned_calls,
            },
            'transactions': {
                'total_count': total_transactions,
                'total_coin_purchases': coin_purchases_amount,
                'total_withdrawals': abs(withdrawals_amount),
            }
        },
        'recent_calls': AdminCallHistorySerializer(recent_calls, many=True, context={'request': request}).data,
        'pending_applications': AdminAgentApplicationSerializer(recent_applications, many=True, context={'request': request}).data,
        'pending_withdrawals': AdminWithdrawalSerializer(recent_withdrawals, many=True, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 3. USERS MANAGEMENT (CUSTOMERS / CLIENTS)
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_users_list(request):
    """
    List regular users (clients) with search, status filters, and pagination.
    Query params:
    - search: search username, email, phone_number, profile.name
    - status: 'all', 'online', 'offline'
    - ordering: '-date_joined', 'date_joined', '-coins', 'coins'
    - page: page number (default 1)
    - page_size: items per page (default 20)
    """
    users = User.objects.filter(is_superuser=False, is_staff=False).select_related('profile', 'wallet')

    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(profile__name__icontains=search)
        )

    # Online status filter
    status_filter = request.GET.get('status', 'all').lower()
    if status_filter == 'online':
        users = users.filter(is_online=True)
    elif status_filter == 'offline':
        users = users.filter(is_online=False)

    # Ordering
    ordering = request.GET.get('ordering', '-date_joined')
    allowed_orderings = ['-date_joined', 'date_joined', '-coins', 'coins', 'username', '-username']
    if ordering in allowed_orderings:
        users = users.order_by(ordering)
    else:
        users = users.order_by('-date_joined')

    # Annotate total calls count
    users = users.annotate(
        annotated_calls_count=Count('outgoing_calls', distinct=True) + Count('incoming_calls', distinct=True)
    )

    page_data = _paginate(users, request)
    serializer = AdminUserListSerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'users': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_user_detail(request, user_id):
    """
    Get detailed user profile, wallet balance, call statistics,
    recent transactions, and call history.
    """
    try:
        target_user = User.objects.select_related('profile', 'wallet').get(id=user_id, is_superuser=False)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AdminUserDetailSerializer(target_user, context={'request': request})

    # Recent Transactions
    transactions = Transaction.objects.filter(user=target_user).order_by('-created_at')[:15]
    tx_serializer = AdminTransactionSerializer(transactions, many=True, context={'request': request})

    # Recent Calls
    calls = CallHistory.objects.filter(
        Q(caller=target_user) | Q(receiver=target_user)
    ).select_related('caller', 'receiver').order_by('-start_time')[:15]
    calls_serializer = AdminCallHistorySerializer(calls, many=True, context={'request': request})

    return Response({
        'status': 'success',
        'user': serializer.data,
        'recent_transactions': tx_serializer.data,
        'recent_calls': calls_serializer.data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_user_adjust_coins(request, user_id):
    """
    Add or deduct coins for a regular user.
    Agents cannot receive manual coin adjustments (they earn via calls).
    Payload:
    - action: "add" | "deduct"
    - coins: positive integer
    - note: optional reason/reference note
    """
    try:
        target_user = User.objects.select_related('wallet').get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    if target_user.is_staff:
        return Response({
            'error': 'Cannot manually adjust coins for agents. Agents earn coins through incoming calls.'
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = AdminCoinAdjustmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    action = serializer.validated_data['action']
    coins_amount = serializer.validated_data['coins']
    note = serializer.validated_data.get('note', '')

    wallet, _ = Wallet.objects.get_or_create(user=target_user)
    current_balance = wallet.balance

    if action == 'add':
        target_user.coins += coins_amount
        target_user.save(update_fields=['coins'])

        wallet.balance += coins_amount
        wallet.save(update_fields=['balance'])

        ref_id = f"admin_credit_{request.user.id}"
        if note:
            ref_id += f"_{note[:50]}"

        tx = Transaction.objects.create(
            user=target_user,
            amount=coins_amount,
            transaction_type='coin_purchase',
            reference_id=ref_id
        )

        return Response({
            'status': 'success',
            'message': f"Successfully credited {coins_amount} coins to @{target_user.username}.",
            'action': 'add',
            'coins_adjusted': coins_amount,
            'new_balance': wallet.balance,
            'transaction_id': tx.id,
        }, status=status.HTTP_200_OK)

    elif action == 'deduct':
        if coins_amount > current_balance:
            return Response({
                'error': f"Insufficient balance. Current balance is {current_balance} coins."
            }, status=status.HTTP_400_BAD_REQUEST)

        target_user.coins = max(0, target_user.coins - coins_amount)
        target_user.save(update_fields=['coins'])

        wallet.balance -= coins_amount
        wallet.save(update_fields=['balance'])

        ref_id = f"admin_debit_{request.user.id}"
        if note:
            ref_id += f"_{note[:50]}"

        tx = Transaction.objects.create(
            user=target_user,
            amount=-coins_amount,
            transaction_type='withdrawal',
            reference_id=ref_id
        )

        return Response({
            'status': 'success',
            'message': f"Successfully deducted {coins_amount} coins from @{target_user.username}.",
            'action': 'deduct',
            'coins_adjusted': coins_amount,
            'new_balance': wallet.balance,
            'transaction_id': tx.id,
        }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsSuperAdminUser])
def admin_user_toggle_status(request, user_id):
    """
    Update user active status (ban/unban) and profile verification.
    Payload:
    - is_active: bool (optional)
    - is_verified: bool (optional)
    """
    try:
        target_user = User.objects.select_related('profile').get(id=user_id, is_superuser=False)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AdminUserStatusUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if 'is_active' in serializer.validated_data:
        target_user.is_active = serializer.validated_data['is_active']
        target_user.save(update_fields=['is_active'])

    if 'is_verified' in serializer.validated_data and hasattr(target_user, 'profile'):
        target_user.profile.is_verified = serializer.validated_data['is_verified']
        target_user.profile.save(update_fields=['is_verified'])

    return Response({
        'status': 'success',
        'message': f"User @{target_user.username} status updated successfully.",
        'is_active': target_user.is_active,
        'is_verified': target_user.profile.is_verified if hasattr(target_user, 'profile') else False
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsSuperAdminUser])
def admin_user_delete(request, user_id):
    """Permanently delete user account."""
    try:
        target_user = User.objects.get(id=user_id, is_superuser=False)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    username = target_user.username
    target_user.delete()
    return Response({
        'status': 'success',
        'message': f"User @{username} has been permanently deleted."
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 4. AGENTS MANAGEMENT
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_agents_list(request):
    """
    List female agents with search, status filters, and performance tier analysis.
    Query params:
    - search: search username, email, phone, name
    - status: 'all', 'approved', 'pending', 'suspended', 'rejected', 'terminated'
    - period: 'today', 'week', 'month', 'all' (default: 'month')
    - performance: 'all', 'high', 'average', 'low'
    - page: page number
    - page_size: items per page
    """
    agents = User.objects.filter(is_superuser=False, is_staff=True).select_related('profile', 'wallet').order_by('-date_joined')

    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        agents = agents.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(profile__name__icontains=search)
        )

    # Status filter
    status_param = request.GET.get('status', 'all').lower()
    if status_param in ('approved', 'pending', 'suspended', 'rejected', 'terminated'):
        agents = agents.filter(agent_status=status_param)

    # Performance calculation
    period = request.GET.get('period', 'month').lower()
    if period not in ('today', 'week', 'month', 'all'):
        period = 'month'

    performance_filter = request.GET.get('performance', 'all').lower()
    if performance_filter not in ('high', 'average', 'low'):
        performance_filter = 'all'

    config = AgentTaskConfig.load()
    today = timezone.localdate()

    call_filter = Q(incoming_calls__status='completed')
    if period == 'today':
        call_filter &= Q(incoming_calls__start_time__date=today)
    elif period == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        call_filter &= Q(incoming_calls__start_time__date__gte=start_of_week)
    elif period == 'month':
        call_filter &= Q(incoming_calls__start_time__date__gte=today.replace(day=1))

    agents = agents.annotate(completed_calls=Count('incoming_calls', filter=call_filter, distinct=True))

    HIGH_PERFORMANCE_PCT = 100
    LOW_PERFORMANCE_PCT = 50

    enriched_agents = []
    performance_counts = {'all': 0, 'high': 0, 'average': 0, 'low': 0}

    for agent in agents:
        if period == 'today':
            target = config.daily_call_target
        elif period == 'week':
            target = config.weekly_call_target
        elif period == 'month':
            target = config.monthly_call_target
        else:
            joined = timezone.localtime(agent.date_joined).date() if agent.date_joined else today
            target = config.monthly_call_target * _months_active(joined, today)

        progress = round(agent.completed_calls * 100 / target) if target else 100

        if progress >= HIGH_PERFORMANCE_PCT:
            tier = 'high'
        elif progress < LOW_PERFORMANCE_PCT:
            tier = 'low'
        else:
            tier = 'average'

        agent.call_target = target
        agent.performance_pct = progress
        agent.performance_tier = tier

        performance_counts['all'] += 1
        performance_counts[tier] += 1

        if performance_filter == 'all' or performance_filter == tier:
            enriched_agents.append(agent)

    if performance_filter == 'low':
        enriched_agents.sort(key=lambda a: a.performance_pct)
    elif performance_filter in ('high', 'average'):
        enriched_agents.sort(key=lambda a: a.performance_pct, reverse=True)

    page_data = _paginate(enriched_agents, request)

    serialized_agents = []
    for ag in page_data['items']:
        data = AdminUserListSerializer(ag, context={'request': request}).data
        data['performance'] = {
            'period': period,
            'completed_calls': ag.completed_calls,
            'target': ag.call_target,
            'percentage': ag.performance_pct,
            'tier': ag.performance_tier
        }
        serialized_agents.append(data)

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'performance_counts': performance_counts,
        'agents': serialized_agents,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_agent_detail(request, agent_id):
    """
    Get complete details of an agent:
    - Profile & verification
    - Agent status
    - Daily/monthly completed calls vs targets
    - Wallet balance
    - Recent calls (incoming and completed)
    - Recent transactions
    - Withdrawal history
    - Available paysheet months
    """
    try:
        agent = User.objects.select_related('profile', 'wallet').get(id=agent_id, is_staff=True)
    except User.DoesNotExist:
        return Response({'error': 'Agent not found.'}, status=status.HTTP_404_NOT_FOUND)

    config = AgentTaskConfig.load()
    today = timezone.localdate()

    daily_completed = CallHistory.objects.filter(
        receiver=agent, status='completed', start_time__date=today
    ).count()

    monthly_completed = CallHistory.objects.filter(
        receiver=agent, status='completed', start_time__date__gte=today.replace(day=1)
    ).count()

    agent_stats = {
        'daily_completed': daily_completed,
        'daily_target': config.daily_call_target,
        'daily_progress_pct': round((daily_completed / config.daily_call_target) * 100) if config.daily_call_target else 100,
        'monthly_completed': monthly_completed,
        'monthly_target': config.monthly_call_target,
        'monthly_progress_pct': round((monthly_completed / config.monthly_call_target) * 100) if config.monthly_call_target else 100,
    }

    # Available paysheet months (last 6 months)
    paysheet_months = []
    for i in range(6):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        paysheet_months.append({
            'year': y,
            'month': m,
            'label': date(y, m, 1).strftime("%B %Y"),
            'is_current': (i == 0)
        })

    # Recent incoming calls
    recent_calls = CallHistory.objects.filter(receiver=agent).select_related('caller').order_by('-start_time')[:15]
    recent_transactions = Transaction.objects.filter(user=agent).order_by('-created_at')[:15]
    withdrawals = WithdrawalRequest.objects.filter(agent=agent).order_by('-created_at')[:10]

    return Response({
        'status': 'success',
        'agent': AdminUserDetailSerializer(agent, context={'request': request}).data,
        'agent_stats': agent_stats,
        'paysheet_months': paysheet_months,
        'recent_calls': AdminCallHistorySerializer(recent_calls, many=True, context={'request': request}).data,
        'recent_transactions': AdminTransactionSerializer(recent_transactions, many=True, context={'request': request}).data,
        'withdrawals': AdminWithdrawalSerializer(withdrawals, many=True, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_agent_create(request):
    """
    Directly create a new agent from the admin panel.
    Sets is_staff=True, creates Profile and Wallet records.
    """
    serializer = AdminAgentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user = User.objects.create_user(
        username=data['username'],
        email=data.get('email', ''),
        password=data['password']
    )
    user.phone_number = data['phone_number']
    user.is_staff = True
    user.agent_status = data.get('agent_status', 'approved')
    user.save()

    Profile.objects.create(
        user=user,
        name=data.get('name') or data['username'],
        age=data.get('age', 18),
        gender=data.get('gender', 'female'),
        phone_number=data['phone_number'],
        bio=data.get('bio', '')
    )

    Wallet.objects.get_or_create(user=user)

    return Response({
        'status': 'success',
        'message': f"Agent @{user.username} created successfully with status '{user.agent_status}'.",
        'agent': AdminUserDetailSerializer(user, context={'request': request}).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_agent_status_action(request, agent_id):
    """
    Governance actions on an agent:
    - approve: set agent_status='approved'
    - suspend: set agent_status='suspended' (blocks receiving calls)
    - reject: set agent_status='rejected', revoke is_staff
    - terminate: set agent_status='terminated', revoke is_staff
    """
    try:
        agent = User.objects.get(id=agent_id, is_staff=True)
    except User.DoesNotExist:
        return Response({'error': 'Agent not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AdminAgentStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    action = serializer.validated_data['action']
    admin_notes = serializer.validated_data.get('admin_notes', '')

    if action == 'approve':
        agent.agent_status = 'approved'
        agent.save(update_fields=['agent_status'])
        msg = f"Agent @{agent.username} has been approved."

    elif action == 'suspend':
        agent.agent_status = 'suspended'
        agent.is_online = False
        agent.save(update_fields=['agent_status', 'is_online'])
        msg = f"Agent @{agent.username} has been suspended."

    elif action == 'reject':
        agent.agent_status = 'rejected'
        agent.is_staff = False
        agent.is_online = False
        agent.save(update_fields=['agent_status', 'is_staff', 'is_online'])
        msg = f"Agent @{agent.username} has been rejected."

    elif action == 'terminate':
        agent.agent_status = 'terminated'
        agent.is_staff = False
        agent.is_online = False
        agent.save(update_fields=['agent_status', 'is_staff', 'is_online'])
        msg = f"Agent @{agent.username} has been permanently terminated."

    return Response({
        'status': 'success',
        'message': msg,
        'agent_status': agent.agent_status,
        'is_staff': agent.is_staff,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_agent_paysheet_data(request, agent_id):
    """
    Retrieve structured JSON data of an agent's monthly performance paysheet.
    Query params:
    - year: int (e.g. 2026)
    - month: int (1-12)
    """
    try:
        agent = User.objects.select_related('profile', 'wallet').get(id=agent_id, is_staff=True)
    except User.DoesNotExist:
        return Response({'error': 'Agent not found.'}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.localtime(timezone.now())
    try:
        year = int(request.GET.get('year', now.year))
        month = int(request.GET.get('month', now.month))
        if month < 1 or month > 12:
            month = now.month
    except (ValueError, TypeError):
        year, month = now.year, now.month

    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    completed_calls = CallHistory.objects.filter(
        receiver=agent, status='completed',
        start_time__date__gte=start_date, start_time__date__lte=end_date
    )

    audio_calls = completed_calls.filter(call_type='audio')
    video_calls = completed_calls.filter(call_type='video')
    total_audio_count = audio_calls.count()
    total_video_count = video_calls.count()
    total_calls_count = total_audio_count + total_video_count

    total_duration_sec = sum(c.duration for c in completed_calls)
    total_coins_earned = completed_calls.aggregate(total=Sum('coins_earned'))['total'] or 0

    # Withdrawals in this period
    withdrawals = WithdrawalRequest.objects.filter(
        agent=agent, created_at__date__gte=start_date, created_at__date__lte=end_date
    )
    approved_withdrawals_coins = withdrawals.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    pending_withdrawals_coins = withdrawals.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    return Response({
        'status': 'success',
        'paysheet_ref': f"HM-PAY-{year}{month:02d}-{agent.id:04d}",
        'period': {
            'year': year,
            'month': month,
            'label': date(year, month, 1).strftime("%B %Y"),
        },
        'agent': {
            'id': agent.id,
            'username': agent.username,
            'name': agent.profile.name if hasattr(agent, 'profile') else agent.username,
            'phone_number': agent.phone_number,
            'email': agent.email,
            'wallet_balance': agent.wallet.balance if hasattr(agent, 'wallet') else 0,
        },
        'calls_summary': {
            'total_calls': total_calls_count,
            'audio_calls': total_audio_count,
            'video_calls': total_video_count,
            'total_duration_seconds': total_duration_sec,
            'total_duration_formatted': f"{total_duration_sec // 60}m {total_duration_sec % 60}s",
            'coins_earned': total_coins_earned,
        },
        'withdrawals_summary': {
            'approved_coins': approved_withdrawals_coins,
            'pending_coins': pending_withdrawals_coins,
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_agent_paysheet_pdf(request, agent_id):
    """
    Download official branded PDF paysheet for an agent for the specified month/year.
    """
    try:
        agent = User.objects.select_related('profile', 'wallet').get(id=agent_id, is_staff=True)
    except User.DoesNotExist:
        return Response({'error': 'Agent not found.'}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.localtime(timezone.now())
    try:
        year = int(request.GET.get('year', now.year))
        month = int(request.GET.get('month', now.month))
        if month < 1 or month > 12 or year < 2020 or year > 2100:
            year, month = now.year, now.month
    except (ValueError, TypeError):
        year, month = now.year, now.month

    pdf_buffer = generate_agent_paysheet_pdf(agent, year=year, month=month)
    filename = f"paysheet_{agent.username}_{year}_{month:02d}.pdf"

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==============================================================================
# 5. AGENT APPLICATIONS MANAGEMENT
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_applications_list(request):
    """
    List user applications to become agents.
    Query params:
    - status: 'all', 'pending', 'approved', 'rejected'
    - search: search username, email, phone, reason
    - page, page_size
    """
    apps = AgentApplication.objects.select_related('user', 'user__profile').order_by('-created_at')

    status_param = request.GET.get('status', 'all').lower()
    if status_param in ('pending', 'approved', 'rejected'):
        apps = apps.filter(status=status_param)

    search = request.GET.get('search', '').strip()
    if search:
        apps = apps.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__phone_number__icontains=search) |
            Q(reason__icontains=search)
        )

    page_data = _paginate(apps, request)
    serializer = AdminAgentApplicationSerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'applications': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_application_detail(request, application_id):
    """Get single agent application detail."""
    try:
        app = AgentApplication.objects.select_related('user', 'user__profile', 'user__wallet').get(id=application_id)
    except AgentApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'status': 'success',
        'application': AdminAgentApplicationSerializer(app, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_application_approve(request, application_id):
    """
    Approve an agent application:
    - Sets application.status = 'approved'
    - Sets user.is_staff = True, user.agent_status = 'approved'
    - Ensures user has a Wallet initialized
    """
    try:
        app = AgentApplication.objects.select_related('user').get(id=application_id)
    except AgentApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    if app.status != 'pending':
        return Response({
            'error': f"This application has already been processed with status '{app.status}'."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = app.user
    user.is_staff = True
    user.agent_status = 'approved'
    user.save(update_fields=['is_staff', 'agent_status'])

    Wallet.objects.get_or_create(user=user)

    app.status = 'approved'
    app.save(update_fields=['status', 'updated_at'])

    return Response({
        'status': 'success',
        'message': f"Application approved! User @{user.username} is now an active agent.",
        'application': AdminAgentApplicationSerializer(app, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_application_reject(request, application_id):
    """
    Reject an agent application:
    - Sets application.status = 'rejected'
    - Sets user.agent_status = 'rejected'
    - Optionally saves admin_notes
    """
    try:
        app = AgentApplication.objects.select_related('user').get(id=application_id)
    except AgentApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    if app.status != 'pending':
        return Response({
            'error': f"This application has already been processed with status '{app.status}'."
        }, status=status.HTTP_400_BAD_REQUEST)

    admin_notes = request.data.get('admin_notes', '')

    user = app.user
    user.agent_status = 'rejected'
    user.save(update_fields=['agent_status'])

    app.status = 'rejected'
    app.admin_notes = admin_notes
    app.save(update_fields=['status', 'admin_notes', 'updated_at'])

    return Response({
        'status': 'success',
        'message': f"Application for @{user.username} was rejected.",
        'application': AdminAgentApplicationSerializer(app, context={'request': request}).data
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 6. WITHDRAWALS MANAGEMENT
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_withdrawals_list(request):
    """
    List agent withdrawal requests.
    Query params:
    - status: 'all', 'pending', 'approved', 'rejected'
    - search: search agent username, phone
    - page, page_size
    """
    withdrawals = WithdrawalRequest.objects.select_related('agent', 'agent__wallet', 'agent__profile').order_by('-created_at')

    status_param = request.GET.get('status', 'all').lower()
    if status_param in ('pending', 'approved', 'rejected'):
        withdrawals = withdrawals.filter(status=status_param)

    search = request.GET.get('search', '').strip()
    if search:
        withdrawals = withdrawals.filter(
            Q(agent__username__icontains=search) |
            Q(agent__phone_number__icontains=search)
        )

    page_data = _paginate(withdrawals, request)
    serializer = AdminWithdrawalSerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'withdrawals': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_withdrawal_approve(request, request_id):
    """
    Approve an agent withdrawal request.
    Marks status as 'approved'.
    """
    try:
        w_req = WithdrawalRequest.objects.select_related('agent').get(id=request_id)
    except WithdrawalRequest.DoesNotExist:
        return Response({'error': 'Withdrawal request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if w_req.status != 'pending':
        return Response({
            'error': f"This withdrawal has already been processed with status '{w_req.status}'."
        }, status=status.HTTP_400_BAD_REQUEST)

    w_req.status = 'approved'
    w_req.save(update_fields=['status', 'updated_at'])

    return Response({
        'status': 'success',
        'message': f"Approved withdrawal of {w_req.amount} coins for agent @{w_req.agent.username}.",
        'withdrawal': AdminWithdrawalSerializer(w_req, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_withdrawal_reject(request, request_id):
    """
    Reject an agent withdrawal request:
    - Marks status as 'rejected'
    - Refunds the coin amount back to the agent's wallet
    - Records refund transaction
    """
    try:
        w_req = WithdrawalRequest.objects.select_related('agent', 'agent__wallet').get(id=request_id)
    except WithdrawalRequest.DoesNotExist:
        return Response({'error': 'Withdrawal request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if w_req.status != 'pending':
        return Response({
            'error': f"This withdrawal has already been processed with status '{w_req.status}'."
        }, status=status.HTTP_400_BAD_REQUEST)

    agent = w_req.agent
    wallet, _ = Wallet.objects.get_or_create(user=agent)
    wallet.balance += w_req.amount
    wallet.save(update_fields=['balance'])

    Transaction.objects.create(
        user=agent,
        amount=w_req.amount,
        transaction_type='earn_call',
        reference_id=f"refund_withdrawal_{w_req.id}"
    )

    w_req.status = 'rejected'
    w_req.save(update_fields=['status', 'updated_at'])

    return Response({
        'status': 'success',
        'message': f"Rejected withdrawal request. Refunded {w_req.amount} coins to @{agent.username}'s wallet.",
        'new_wallet_balance': wallet.balance,
        'withdrawal': AdminWithdrawalSerializer(w_req, context={'request': request}).data
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 7. CALLS MONITORING & LOGS
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_calls_list(request):
    """
    List all calls across the platform with filters and pagination.
    Query params:
    - call_type: 'all', 'audio', 'video'
    - status: 'all', 'completed', 'missed', 'rejected', 'accepted', 'initiated', 'cancelled'
    - search: search caller or receiver username / phone
    - page, page_size
    """
    calls = CallHistory.objects.select_related('caller', 'receiver', 'caller__profile', 'receiver__profile').order_by('-start_time')

    call_type = request.GET.get('call_type', 'all').lower()
    if call_type in ('audio', 'video'):
        calls = calls.filter(call_type=call_type)

    status_param = request.GET.get('status', 'all').lower()
    if status_param in ('completed', 'missed', 'rejected', 'accepted', 'initiated', 'cancelled'):
        calls = calls.filter(status=status_param)

    search = request.GET.get('search', '').strip()
    if search:
        calls = calls.filter(
            Q(caller__username__icontains=search) |
            Q(caller__phone_number__icontains=search) |
            Q(receiver__username__icontains=search) |
            Q(receiver__phone_number__icontains=search)
        )

    page_data = _paginate(calls, request)
    serializer = AdminCallHistorySerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'calls': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_call_detail(request, call_id):
    """Get single call log detail."""
    try:
        call_obj = CallHistory.objects.select_related('caller', 'receiver', 'caller__profile', 'receiver__profile').get(id=call_id)
    except CallHistory.DoesNotExist:
        return Response({'error': 'Call log not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'status': 'success',
        'call': AdminCallHistorySerializer(call_obj, context={'request': request}).data
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 8. TRANSACTIONS & COIN LEDGER
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_transactions_list(request):
    """
    List all transactions across the platform.
    Query params:
    - type: 'all', 'coin_purchase', 'withdrawal', 'earn_call'
    - user_id: filter by specific user
    - search: search username or reference_id
    - page, page_size
    """
    txs = Transaction.objects.select_related('user', 'user__profile').order_by('-created_at')

    tx_type = request.GET.get('type', 'all').lower()
    if tx_type in ('coin_purchase', 'withdrawal', 'earn_call'):
        txs = txs.filter(transaction_type=tx_type)

    user_id = request.GET.get('user_id')
    if user_id:
        txs = txs.filter(user_id=user_id)

    search = request.GET.get('search', '').strip()
    if search:
        txs = txs.filter(
            Q(user__username__icontains=search) |
            Q(reference_id__icontains=search)
        )

    page_data = _paginate(txs, request)
    serializer = AdminTransactionSerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'transactions': serializer.data
    }, status=status.HTTP_200_OK)


# ==============================================================================
# 9. OFFERS MANAGEMENT (CRUD)
# ==============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdminUser])
def admin_offers_list_create(request):
    """
    GET: List all coin package offers.
    POST: Create a new coin offer package.
    """
    if request.method == 'GET':
        offers = Offer.objects.all().order_by('-created_at')
        serializer = AdminOfferSerializer(offers, many=True)
        return Response({'status': 'success', 'offers': serializer.data}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = AdminOfferSerializer(data=request.data)
        if serializer.is_valid():
            offer = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Offer created successfully.',
                'offer': AdminOfferSerializer(offer).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdminUser])
def admin_offer_detail_update_delete(request, offer_id):
    """
    GET: Retrieve offer details.
    PUT/PATCH: Update offer.
    DELETE: Delete offer.
    """
    try:
        offer = Offer.objects.get(id=offer_id)
    except Offer.DoesNotExist:
        return Response({'error': 'Offer not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'status': 'success', 'offer': AdminOfferSerializer(offer).data}, status=status.HTTP_200_OK)

    elif request.method in ('PUT', 'PATCH'):
        partial = (request.method == 'PATCH')
        serializer = AdminOfferSerializer(offer, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Offer updated successfully.',
                'offer': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        offer.delete()
        return Response({'status': 'success', 'message': 'Offer deleted successfully.'}, status=status.HTTP_200_OK)


# ==============================================================================
# 10. AGENT TASK TARGETS CONFIGURATION
# ==============================================================================

@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsSuperAdminUser])
def admin_tasks_get_update(request):
    """
    GET: Retrieve current daily, weekly, and monthly call targets.
    POST / PUT: Update task target thresholds.
    """
    config = AgentTaskConfig.load()

    if request.method == 'GET':
        return Response({
            'status': 'success',
            'config': AdminAgentTaskConfigSerializer(config).data
        }, status=status.HTTP_200_OK)

    serializer = AdminAgentTaskConfigSerializer(config, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'status': 'success',
            'message': 'Agent task configuration updated successfully.',
            'config': serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# 11. GLOBAL SETTINGS (CRUD)
# ==============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdminUser])
def admin_settings_list_create(request):
    """
    GET: List all system global settings.
    POST: Create a new system setting.
    """
    if request.method == 'GET':
        settings_qs = GlobalSetting.objects.all().order_by('key')
        serializer = AdminGlobalSettingSerializer(settings_qs, many=True)
        return Response({'status': 'success', 'settings': serializer.data}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = AdminGlobalSettingSerializer(data=request.data)
        if serializer.is_valid():
            setting = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Setting created successfully.',
                'setting': AdminGlobalSettingSerializer(setting).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdminUser])
def admin_setting_detail_update_delete(request, setting_id):
    """
    GET: Retrieve setting.
    PUT/PATCH: Update setting value or description.
    DELETE: Delete setting.
    """
    try:
        setting = GlobalSetting.objects.get(id=setting_id)
    except GlobalSetting.DoesNotExist:
        return Response({'error': 'Setting not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'status': 'success', 'setting': AdminGlobalSettingSerializer(setting).data}, status=status.HTTP_200_OK)

    elif request.method in ('PUT', 'PATCH'):
        partial = (request.method == 'PATCH')
        serializer = AdminGlobalSettingSerializer(setting, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Setting updated successfully.',
                'setting': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        setting.delete()
        return Response({'status': 'success', 'message': 'Setting deleted successfully.'}, status=status.HTTP_200_OK)


# ==============================================================================
# 12. PUSH NOTIFICATIONS & BROADCASTS
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_notifications_list(request):
    """
    List past push notifications sent via admin panel with delivery stats.
    Query params: page, page_size
    """
    notifications = Notification.objects.select_related('recipient').order_by('-created_at')
    page_data = _paginate(notifications, request)
    serializer = AdminNotificationSerializer(page_data['items'], many=True, context={'request': request})

    return Response({
        'status': 'success',
        'page': page_data['page'],
        'page_size': page_data['page_size'],
        'total': page_data['total'],
        'total_pages': page_data['total_pages'],
        'has_next': page_data['has_next'],
        'has_previous': page_data['has_previous'],
        'notifications': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperAdminUser])
def admin_notification_broadcast(request):
    """
    Send push notification via Firebase Cloud Messaging (FCM).
    Payload:
    - title: Notification title
    - body: Notification body text
    - target_audience: 'all' | 'users' | 'agents' | 'specific'
    - recipient_id: int (required if target_audience is 'specific')
    - image_url: optional URL of image
    - notification_type: optional type (default 'general')
    """
    serializer = AdminNotificationBroadcastSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    recipient = None
    if data['target_audience'] == 'specific':
        try:
            recipient = User.objects.get(id=data['recipient_id'])
        except User.DoesNotExist:
            return Response({'error': 'Recipient user not found.'}, status=status.HTTP_404_NOT_FOUND)

    result = send_fcm_notification(
        title=data['title'],
        body=data['body'],
        target_audience=data['target_audience'],
        recipient=recipient,
        image_url=data.get('image_url') or None,
        extra_data={'type': data.get('notification_type', 'general')}
    )

    if result['success']:
        return Response({
            'status': 'success',
            'message': result['message'],
            'sent_count': result['sent_count'],
            'failed_count': result['failed_count'],
            'total_targets': result['total_targets'],
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'status': 'failed',
            'error': result['message'],
            'sent_count': result['sent_count'],
            'failed_count': result['failed_count']
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsSuperAdminUser])
def admin_notification_delete(request, notification_id):
    """Delete a notification from history."""
    try:
        notif = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)

    notif.delete()
    return Response({'status': 'success', 'message': 'Notification deleted successfully.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_notification_stats(request):
    """Get FCM statistics (total registered tokens, users with tokens, agents with tokens)."""
    stats_data = get_fcm_stats()
    return Response({'status': 'success', 'fcm_stats': stats_data}, status=status.HTTP_200_OK)


# ==============================================================================
# 13. LIVE MONITORING
# ==============================================================================

@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_live_online_users(request):
    """List currently online regular clients."""
    users = User.objects.filter(is_superuser=False, is_staff=False, is_online=True).select_related('profile', 'wallet').order_by('-last_login')
    page_data = _paginate(users, request)
    serializer = AdminUserListSerializer(page_data['items'], many=True, context={'request': request})
    return Response({
        'status': 'success',
        'count': page_data['total'],
        'users': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_live_online_agents(request):
    """List currently online agents."""
    agents = User.objects.filter(is_superuser=False, is_staff=True, is_online=True).select_related('profile', 'wallet').order_by('-last_login')
    page_data = _paginate(agents, request)
    serializer = AdminUserListSerializer(page_data['items'], many=True, context={'request': request})
    return Response({
        'status': 'success',
        'count': page_data['total'],
        'agents': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperAdminUser])
def admin_live_on_call(request):
    """List currently active / ongoing calls."""
    calls = CallHistory.objects.filter(status__in=['initiated', 'accepted']).select_related('caller', 'receiver').order_by('-start_time')
    serializer = AdminCallHistorySerializer(calls, many=True, context={'request': request})
    return Response({
        'status': 'success',
        'count': len(serializer.data),
        'active_calls': serializer.data
    }, status=status.HTTP_200_OK)
