from django.urls import path
from . import admin_api_views as views

app_name = 'admin_api'

urlpatterns = [
    # 1. Admin Authentication
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('me/', views.admin_me, name='me'),

    # 2. Dashboard Analytics
    path('dashboard/', views.admin_dashboard_stats, name='dashboard'),

    # 3. Users Management (Clients)
    path('users/', views.admin_users_list, name='users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='user_detail'),
    path('users/<int:user_id>/coins/', views.admin_user_adjust_coins, name='user_adjust_coins'),
    path('users/<int:user_id>/status/', views.admin_user_toggle_status, name='user_status'),
    path('users/<int:user_id>/delete/', views.admin_user_delete, name='user_delete'),

    # 4. Agents Management
    path('agents/', views.admin_agents_list, name='agents'),
    path('agents/create/', views.admin_agent_create, name='agent_create'),
    path('agents/<int:agent_id>/', views.admin_agent_detail, name='agent_detail'),
    path('agents/<int:agent_id>/status/', views.admin_agent_status_action, name='agent_status_action'),
    path('agents/<int:agent_id>/paysheet/', views.admin_agent_paysheet_data, name='agent_paysheet_data'),
    path('agents/<int:agent_id>/paysheet-pdf/', views.admin_agent_paysheet_pdf, name='agent_paysheet_pdf'),

    # 5. Agent Applications
    path('agent-applications/', views.admin_applications_list, name='agent_applications'),
    path('agent-applications/<int:application_id>/', views.admin_application_detail, name='agent_application_detail'),
    path('agent-applications/<int:application_id>/approve/', views.admin_application_approve, name='agent_application_approve'),
    path('agent-applications/<int:application_id>/reject/', views.admin_application_reject, name='agent_application_reject'),

    # 6. Withdrawals
    path('withdrawals/', views.admin_withdrawals_list, name='withdrawals'),
    path('withdrawals/<int:request_id>/approve/', views.admin_withdrawal_approve, name='withdrawal_approve'),
    path('withdrawals/<int:request_id>/reject/', views.admin_withdrawal_reject, name='withdrawal_reject'),

    # 7. Calls
    path('calls/', views.admin_calls_list, name='calls'),
    path('calls/<int:call_id>/', views.admin_call_detail, name='call_detail'),

    # 8. Transactions
    path('transactions/', views.admin_transactions_list, name='transactions'),

    # 9. Offers
    path('offers/', views.admin_offers_list_create, name='offers'),
    path('offers/<int:offer_id>/', views.admin_offer_detail_update_delete, name='offer_detail'),

    # 10. Agent Tasks Configuration
    path('tasks/', views.admin_tasks_get_update, name='tasks'),

    # 11. Global Settings
    path('settings/', views.admin_settings_list_create, name='settings'),
    path('settings/<int:setting_id>/', views.admin_setting_detail_update_delete, name='setting_detail'),

    # 12. Push Notifications
    path('notifications/', views.admin_notifications_list, name='notifications'),
    path('notifications/broadcast/', views.admin_notification_broadcast, name='notification_broadcast'),
    path('notifications/<int:notification_id>/delete/', views.admin_notification_delete, name='notification_delete'),
    path('notifications/stats/', views.admin_notification_stats, name='notification_stats'),

    # 13. Live Monitoring
    path('live/online-users/', views.admin_live_online_users, name='live_online_users'),
    path('live/online-agents/', views.admin_live_online_agents, name='live_online_agents'),
    path('live/on-call/', views.admin_live_on_call, name='live_on_call'),
]
