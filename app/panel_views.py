from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Count, Q
from .models import User, CallHistory, Offer, AgentTaskConfig, GlobalSetting, WithdrawalRequest, Wallet, Transaction, AgentApplication, Notification
from .fcm_service import get_fcm_stats, send_fcm_notification
from .pdf_utils import generate_agent_paysheet_pdf

def is_superadmin(user):
    return user.is_authenticated and user.is_superuser

def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_panel:dashboard')

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.is_superuser:
                auth_login(request, user)
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, 'Only superadmins are allowed to access this panel.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'admin_panel/login.html')

def admin_logout(request):
    auth_logout(request)
    return redirect('admin_panel:login')

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def dashboard(request):
    # 1. Regular Users (non-staff, non-superuser)
    total_users = User.objects.filter(is_superuser=False, is_staff=False).count()
    active_users = User.objects.filter(is_superuser=False, is_staff=False, is_online=True).count()

    # 2. Agents (staff, non-superuser)
    agents_qs = User.objects.filter(is_superuser=False, is_staff=True)
    total_agents = agents_qs.count()
    active_agents = agents_qs.filter(is_online=True).count()
    approved_agents = agents_qs.filter(agent_status='approved').count()
    pending_agents = agents_qs.filter(agent_status='pending').count()
    suspended_agents = agents_qs.filter(agent_status='suspended').count()

    # 3. Agent Applications & Withdrawals
    pending_applications = AgentApplication.objects.filter(status='pending').count()
    total_applications = AgentApplication.objects.count()
    pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').count()

    # 4. Calls
    total_calls = CallHistory.objects.count()
    recent_calls = CallHistory.objects.select_related('caller', 'receiver').order_by('-start_time')[:6]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_agents': total_agents,
        'active_agents': active_agents,
        'approved_agents': approved_agents,
        'pending_agents': pending_agents,
        'suspended_agents': suspended_agents,
        'pending_applications': pending_applications,
        'total_applications': total_applications,
        'pending_withdrawals': pending_withdrawals,
        'total_calls': total_calls,
        'recent_calls': recent_calls,
    }
    return render(request, 'admin_panel/dashboard.html', context)

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def users_list(request):
    """List of regular users only (agents are listed on the Agents page)"""
    queryset = User.objects.filter(is_superuser=False, is_staff=False).select_related('wallet').order_by('-date_joined')
    return render(request, 'admin_panel/users.html', {'users': queryset})

# Performance thresholds (percentage of the Task Settings call target)
HIGH_PERFORMANCE_PCT = 100   # reached / exceeded target
LOW_PERFORMANCE_PCT = 50     # below half of target

PERFORMANCE_PERIODS = {
    'today': 'Today',
    'week': 'This Week',
    'month': 'This Month',
    'all': 'All Time',
}


def _months_active(joined_date, today):
    """Number of calendar months (inclusive) an agent has been on the platform."""
    months = (today.year - joined_date.year) * 12 + (today.month - joined_date.month) + 1
    return max(1, months)


@user_passes_test(is_superadmin, login_url='admin_panel:login')
def agents_list(request, pending_only=False):
    """List of agents, optionally filtered by agent status.

    When pending_only is True (Pending Agents sidebar page), only pending
    agents are listed and the status filter tabs are hidden.

    Agents are also classified by performance: completed calls (as receiver)
    in the selected period compared against the Task Settings target.
      High    -> >= HIGH_PERFORMANCE_PCT of target
      Low     -> <  LOW_PERFORMANCE_PCT of target
      Average -> in between
    """
    status = 'pending' if pending_only else request.GET.get('status', 'all')

    period = request.GET.get('period', 'month')
    if period not in PERFORMANCE_PERIODS:
        period = 'month'

    performance = request.GET.get('performance', 'all')
    if pending_only or performance not in ('high', 'average', 'low'):
        performance = 'all'

    agents = User.objects.filter(is_superuser=False, is_staff=True).select_related('wallet').order_by('-date_joined')

    counts = {
        'all': agents.count(),
        'approved': agents.filter(agent_status='approved').count(),
        'pending': agents.filter(agent_status='pending').count(),
        'suspended': agents.filter(agent_status='suspended').count(),
    }

    if status in ('approved', 'pending', 'suspended'):
        agents = agents.filter(agent_status=status)
    else:
        status = 'all'

    # --- Performance calculation ---
    config = AgentTaskConfig.load()
    today = timezone.localdate()

    call_filter = Q(incoming_calls__status='completed')
    if period == 'today':
        call_filter &= Q(incoming_calls__start_time__date=today)
    elif period == 'week':
        start_of_week = today - timedelta(days=today.weekday())  # week starts Monday
        call_filter &= Q(incoming_calls__start_time__date__gte=start_of_week)
    elif period == 'month':
        call_filter &= Q(incoming_calls__start_time__date__gte=today.replace(day=1))

    agents = agents.annotate(completed_calls=Count('incoming_calls', filter=call_filter, distinct=True))

    agent_rows = []
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
        agent.performance_bar = min(progress, 100)
        agent.performance_tier = tier

        performance_counts['all'] += 1
        performance_counts[tier] += 1

        if performance == 'all' or performance == tier:
            agent_rows.append(agent)

    # When filtering by performance, rank agents by progress
    if performance == 'low':
        agent_rows.sort(key=lambda a: a.performance_pct)
    elif performance in ('high', 'average'):
        agent_rows.sort(key=lambda a: a.performance_pct, reverse=True)

    return render(request, 'admin_panel/agents.html', {
        'agents': agent_rows,
        'active_status': status,
        'counts': counts,
        'pending_only': pending_only,
        'period': period,
        'periods': PERFORMANCE_PERIODS,
        'period_label': PERFORMANCE_PERIODS[period],
        'performance': performance,
        'performance_counts': performance_counts,
        'high_pct': HIGH_PERFORMANCE_PCT,
        'low_pct': LOW_PERFORMANCE_PCT,
    })

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def online_users_list(request):
    """List of online regular users only"""
    queryset = User.objects.filter(is_superuser=False, is_staff=False, is_online=True).select_related('wallet').order_by('-date_joined')
    return render(request, 'admin_panel/online_users.html', {'users': queryset})


@user_passes_test(is_superadmin, login_url='admin_panel:login')
def online_agents_list(request):
    """List of online agents only"""
    queryset = User.objects.filter(is_superuser=False, is_staff=True, is_online=True).select_related('wallet').order_by('-date_joined')
    return render(request, 'admin_panel/online_agents.html', {'users': queryset})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def user_detail(request, user_id):
    target_user = get_object_or_404(User.objects.select_related('wallet'), id=user_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_coins':
            # Prevent adding coins to agents
            if target_user.is_staff:
                messages.error(request, 'Cannot manually add coins to agents. Agents earn coins through calls.')
                return redirect('admin_panel:user_detail', user_id=user_id)
            coins_to_add = int(request.POST.get('coins', 0))
            if coins_to_add > 0:
                # Update user's coins field
                target_user.coins += coins_to_add
                target_user.save()

                # Update wallet balance if wallet exists
                if hasattr(target_user, 'wallet'):
                    target_user.wallet.balance += coins_to_add
                    target_user.wallet.save()

                # Log the transaction
                Transaction.objects.create(
                    user=target_user,
                    amount=coins_to_add,
                    transaction_type='coin_purchase',
                    reference_id=f"admin_add_{request.user.id}"
                )

                messages.success(request, f'Successfully added {coins_to_add} coins to {target_user.username}')
            else:
                messages.error(request, 'Please enter a valid coin amount')

        elif action == 'deduct_coins':
            # Prevent deducting coins from agents
            if target_user.is_staff:
                messages.error(request, 'Cannot manually deduct coins from agents. Agents earn coins through calls.')
                return redirect('admin_panel:user_detail', user_id=user_id)

            coins_to_deduct = int(request.POST.get('coins', 0))
            current_balance = target_user.wallet.balance if hasattr(target_user, 'wallet') else target_user.coins

            if coins_to_deduct > 0:
                if coins_to_deduct <= current_balance:
                    # Update user's coins field
                    target_user.coins -= coins_to_deduct
                    target_user.save()

                    # Update wallet balance if wallet exists
                    if hasattr(target_user, 'wallet'):
                        target_user.wallet.balance -= coins_to_deduct
                        target_user.wallet.save()

                    # Log the transaction
                    Transaction.objects.create(
                        user=target_user,
                        amount=-coins_to_deduct,
                        transaction_type='withdrawal',
                        reference_id=f"admin_deduct_{request.user.id}"
                    )

                    messages.success(request, f'Successfully deducted {coins_to_deduct} coins from {target_user.username}')
                else:
                    messages.error(request, f'Insufficient balance. Current balance: {current_balance}')
            else:
                messages.error(request, 'Please enter a valid coin amount')

        elif action == 'approve_agent':
            if target_user.is_staff:
                target_user.agent_status = 'approved'
                target_user.save()
                messages.success(request, f'Agent {target_user.username} has been approved')
            else:
                messages.error(request, 'This user is not an agent')

        elif action == 'reject_agent':
            if target_user.is_staff:
                target_user.agent_status = 'rejected'
                target_user.is_staff = False
                target_user.save()
                messages.success(request, f'Agent {target_user.username} has been rejected and removed from agent status')
            else:
                messages.error(request, 'This user is not an agent')

        elif action == 'suspend_agent':
            if target_user.is_staff:
                target_user.agent_status = 'suspended'
                target_user.save()
                messages.success(request, f'Agent {target_user.username} has been suspended')
            else:
                messages.error(request, 'This user is not an agent')

        elif action == 'terminate_agent':
            if target_user.is_staff:
                target_user.agent_status = 'terminated'
                target_user.is_staff = False
                target_user.save()
                messages.success(request, f'Agent {target_user.username} has been terminated and removed from agent status')
            else:
                messages.error(request, 'This user is not an agent')

        return redirect('admin_panel:user_detail', user_id=user_id)

    # Fetch stats and history for standard user view
    profile = getattr(target_user, 'profile', None)
    outgoing_calls_count = CallHistory.objects.filter(caller=target_user).count()
    incoming_calls_count = CallHistory.objects.filter(receiver=target_user).count()
    total_calls_count = outgoing_calls_count + incoming_calls_count
    completed_calls_count = CallHistory.objects.filter(
        Q(caller=target_user) | Q(receiver=target_user),
        status='completed'
    ).count()

    recent_transactions = Transaction.objects.filter(user=target_user).order_by('-created_at')[:8]
    recent_calls = CallHistory.objects.filter(
        Q(caller=target_user) | Q(receiver=target_user)
    ).select_related('caller', 'receiver').order_by('-start_time')[:6]

    agent_stats = None
    if target_user.is_staff:
        config = AgentTaskConfig.load()
        today = timezone.localdate()
        daily_completed = CallHistory.objects.filter(
            receiver=target_user,
            status='completed',
            start_time__date=today
        ).count()
        monthly_completed = CallHistory.objects.filter(
            receiver=target_user,
            status='completed',
            start_time__date__gte=today.replace(day=1)
        ).count()
        agent_stats = {
            'daily_completed': daily_completed,
            'daily_target': config.daily_call_target,
            'monthly_completed': monthly_completed,
            'monthly_target': config.monthly_call_target,
        }

        # Available months for paysheet download (last 6 months)
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
    else:
        paysheet_months = []

    return render(request, 'admin_panel/user_detail.html', {
        'target_user': target_user,
        'profile': profile,
        'total_calls_count': total_calls_count,
        'completed_calls_count': completed_calls_count,
        'outgoing_calls_count': outgoing_calls_count,
        'incoming_calls_count': incoming_calls_count,
        'recent_transactions': recent_transactions,
        'recent_calls': recent_calls,
        'agent_stats': agent_stats,
        'paysheet_months': paysheet_months,
    })

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def agent_paysheet_pdf(request, agent_id):
    """
    Generates and returns an agent paysheet as a PDF attachment for a specified month/year.
    """
    agent = get_object_or_404(User.objects.select_related('wallet'), id=agent_id)
    if not agent.is_staff:
        messages.error(request, f"User @{agent.username} is not registered as an agent.")
        return redirect('admin_panel:user_detail', user_id=agent_id)

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

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def calls_list(request):
    calls = CallHistory.objects.select_related('caller', 'receiver', 'caller__wallet', 'receiver__wallet').order_by('-start_time')
    return render(request, 'admin_panel/calls.html', {'calls': calls})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def call_detail(request, call_id):
    target_call = get_object_or_404(CallHistory.objects.select_related('caller', 'receiver'), id=call_id)
    return render(request, 'admin_panel/call_detail.html', {'target_call': target_call})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def offers_list(request):
    offers = Offer.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/offers.html', {'offers': offers})


# @user_passes_test(is_superadmin, login_url='admin_panel:login')
# def create_agent(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         phone = request.POST.get('phone_number')
#         password = request.POST.get('password')

#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists')
#         elif User.objects.filter(phone_number=phone).exists():
#             messages.error(request, 'Phone number already exists')
#         else:
#             from .models import Profile

#             user = User.objects.create_user(username=username, email=email, password=password)
#             user.phone_number = phone
#             user.is_staff = True
#             user.save()

#             # Create profile for the agent
#             Profile.objects.create(
#                 user=user,
#                 name=username,
#                 age=18,
#                 gender='other',
#                 phone_number=phone,
#                 bio=''
#             )

#             messages.success(request, 'Agent created successfully!')
#             return redirect('admin_panel:users')

#     return render(request, 'admin_panel/create_agent.html')

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def create_agent(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone_number')
        password = request.POST.get('password')
        age = request.POST.get('age', 18)
        gender = request.POST.get('gender', 'other')
        bio = request.POST.get('bio', '')

        if email and not email.strip().lower().endswith('@gmail.com'):
            messages.error(request, 'Email must end with @gmail.com')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(phone_number=phone).exists():
            messages.error(request, 'Phone number already exists')
        else:
            from .models import Profile
            user = User.objects.create_user(username=username, email=email, password=password)
            user.phone_number = phone
            user.is_staff = True
            user.agent_status = 'pending'
            user.save()

            # Create profile for the agent with provided details
            Profile.objects.create(
                user=user,
                name=username,
                age=int(age) if age else 18,
                gender=gender if gender else 'other',
                phone_number=phone,
                bio=bio if bio else ''
            )

            messages.success(request, 'Agent created successfully! Status: Pending Approval')
            return redirect('admin_panel:pending_agents')

    return render(request, 'admin_panel/create_agent.html')

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def task_config(request):
    config = AgentTaskConfig.load()
    if request.method == 'POST':
        config.daily_call_target = request.POST.get('daily_target', 50)
        config.weekly_call_target = request.POST.get('weekly_target', 250)
        config.monthly_call_target = request.POST.get('monthly_target', 1000)
        config.save()
        messages.success(request, 'Task configuration updated!')
        return redirect('admin_panel:tasks')

    return render(request, 'admin_panel/task_config.html', {'config': config})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def settings_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            key = request.POST.get('key')
            value = request.POST.get('value')
            data_type = request.POST.get('data_type')
            desc = request.POST.get('description')
            if not GlobalSetting.objects.filter(key=key).exists():
                GlobalSetting.objects.create(key=key, value=value, data_type=data_type, description=desc)
                messages.success(request, 'Setting created successfully!')
            else:
                messages.error(request, 'Setting with this key already exists.')
        elif action == 'update':
            setting_id = request.POST.get('setting_id')
            value = request.POST.get('value')
            setting = GlobalSetting.objects.get(id=setting_id)
            setting.value = value
            setting.save()
            messages.success(request, 'Setting updated successfully!')
        return redirect('admin_panel:settings')

    settings = GlobalSetting.objects.all().order_by('key')
    return render(request, 'admin_panel/settings.html', {'settings': settings})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def withdrawals_list(request):
    requests = WithdrawalRequest.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/withdrawals.html', {'requests': requests})

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def handle_withdrawal(request, request_id, action):
    try:
        withdrawal = WithdrawalRequest.objects.get(id=request_id)
        if withdrawal.status != 'pending':
            messages.error(request, 'This request has already been processed.')
            return redirect('admin_panel:withdrawals')

        if action == 'approve':
            withdrawal.status = 'approved'
            withdrawal.save()
            messages.success(request, f'Approved withdrawal for {withdrawal.agent.username}')

        elif action == 'reject':
            # Refund the wallet
            wallet = withdrawal.agent.wallet
            wallet.balance += withdrawal.amount
            wallet.save()

            # Log refund transaction
            Transaction.objects.create(
                user=withdrawal.agent,
                amount=withdrawal.amount,
                transaction_type='earn_call', # or 'refund'
                reference_id=f"refund_{withdrawal.id}"
            )

            withdrawal.status = 'rejected'
            withdrawal.save()
            messages.success(request, f'Rejected withdrawal for {withdrawal.agent.username} and refunded {withdrawal.amount} coins.')

    except WithdrawalRequest.DoesNotExist:
        messages.error(request, 'Request not found.')

    return redirect('admin_panel:withdrawals')

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def transactions_list(request):
    tab_type = request.GET.get('type', 'all')

    if tab_type == 'earn_call':
        transactions = Transaction.objects.filter(transaction_type='earn_call')
    elif tab_type == 'withdrawal':
        transactions = Transaction.objects.filter(transaction_type='withdrawal')
    elif tab_type == 'coin_purchase':
        transactions = Transaction.objects.filter(transaction_type='coin_purchase')
    else:
        transactions = Transaction.objects.all()
        tab_type = 'all'

    transactions = transactions.order_by('-created_at')

    return render(request, 'admin_panel/transactions.html', {
        'transactions': transactions,
        'current_tab': tab_type
    })

@user_passes_test(is_superadmin, login_url='admin_panel:login')
def agent_applications_list(request):
    """List all agent applications"""
    tab = request.GET.get('tab', 'all')

    queryset = AgentApplication.objects.select_related('user').order_by('-created_at')

    if tab == 'pending':
        queryset = queryset.filter(status='pending')
    elif tab == 'approved':
        queryset = queryset.filter(status='approved')
    elif tab == 'rejected':
        queryset = queryset.filter(status='rejected')

    return render(request, 'admin_panel/agent_applications.html', {
        'applications': queryset,
        'active_tab': tab
    })


@user_passes_test(is_superadmin, login_url='admin_panel:login')
def agent_application_detail(request, application_id):
    """View and manage agent application"""
    application = get_object_or_404(AgentApplication.objects.select_related('user'), id=application_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            if application.status == 'pending':
                # Convert user to agent
                application.user.is_staff = True
                application.user.agent_status = 'approved'
                application.user.save()

                # Create wallet if it doesn't exist
                Wallet.objects.get_or_create(user=application.user)

                # Update application status
                application.status = 'approved'
                application.save()

                messages.success(request, f'Application approved. {application.user.username} is now an agent.')
            else:
                messages.error(request, 'This application has already been processed.')

        elif action == 'reject':
            if application.status == 'pending':
                application.status = 'rejected'
                application.admin_notes = request.POST.get('admin_notes', '')
                application.save()

                messages.success(request, f'Application rejected for {application.user.username}.')
            else:
                messages.error(request, 'This application has already been processed.')

        return redirect('admin_panel:agent_applications')

    return render(request, 'admin_panel/agent_application_detail.html', {
        'application': application
    })


@user_passes_test(is_superadmin, login_url='admin_panel:login')
def notifications_list(request):
    """View and send push notifications to users/agents from the admin panel"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        target_audience = request.POST.get('target_audience', 'all')
        recipient_id = request.POST.get('recipient_id')
        image_url = request.POST.get('image_url', '').strip()
        notification_type = request.POST.get('notification_type', 'general')

        recipient = None
        if target_audience == 'specific':
            if not recipient_id:
                messages.error(request, 'Please select a specific user or agent.')
                return redirect('admin_panel:notifications')
            recipient = get_object_or_404(User, id=recipient_id)

        result = send_fcm_notification(
            title=title,
            body=body,
            target_audience=target_audience,
            recipient=recipient,
            image_url=image_url if image_url else None,
            extra_data={'type': notification_type}
        )

        if result['success']:
            if result['sent_count'] > 0:
                messages.success(request, f"✓ Push notification sent successfully to {result['sent_count']} device(s)!")
            else:
                messages.warning(request, f"Notification saved, but {result['message']}")
        else:
            messages.error(request, f"Failed to send notification: {result['message']}")

        return redirect('admin_panel:notifications')

    # GET request
    stats = get_fcm_stats()
    notifications = Notification.objects.select_related('recipient').order_by('-created_at')

    # Candidates for specific recipient dropdown
    candidate_users = User.objects.filter(is_superuser=False).values(
        'id', 'username', 'is_staff', 'fcm_token'
    ).order_by('username')

    context = {
        'stats': stats,
        'notifications': notifications,
        'candidate_users': candidate_users,
    }
    return render(request, 'admin_panel/notifications.html', context)


@user_passes_test(is_superadmin, login_url='admin_panel:login')
def delete_notification(request, notification_id):
    """Delete a notification from history"""
    notification = get_object_or_404(Notification, id=notification_id)
    notification.delete()
    messages.success(request, 'Notification deleted successfully.')
    return redirect('admin_panel:notifications')