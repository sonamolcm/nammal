from django.urls import path
from . import panel_views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', panel_views.admin_login, name='login'),
    path('logout/', panel_views.admin_logout, name='logout'),
    path('', panel_views.dashboard, name='dashboard'),
    path('users/', panel_views.users_list, name='users'),
    path('users/<int:user_id>/', panel_views.user_detail, name='user_detail'),
    path('online-users/', panel_views.online_users_list, name='online_users'),
    path('online-agents/', panel_views.online_agents_list, name='online_agents'),
    path('agents/', panel_views.agents_list, name='agents'),
    path('agents/pending/', panel_views.agents_list, {'pending_only': True}, name='pending_agents'),
    path('agents/<int:agent_id>/paysheet-pdf/', panel_views.agent_paysheet_pdf, name='agent_paysheet_pdf'),
    path('agents/create/', panel_views.create_agent, name='create_agent'),
    path('calls/', panel_views.calls_list, name='calls'),
    path('calls/<int:call_id>/', panel_views.call_detail, name='call_detail'),
    path('offers/', panel_views.offers_list, name='offers'),
    path('tasks/', panel_views.task_config, name='tasks'),
    path('settings/', panel_views.settings_list, name='settings'),
    path('withdrawals/', panel_views.withdrawals_list, name='withdrawals'),
    path('withdrawals/<int:request_id>/<str:action>/', panel_views.handle_withdrawal, name='handle_withdrawal'),
    path('transactions/', panel_views.transactions_list, name='transactions'),
    path('agent-applications/', panel_views.agent_applications_list, name='agent_applications'),
    path('agent-applications/<int:application_id>/', panel_views.agent_application_detail, name='agent_application_detail'),
    path('notifications/', panel_views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/delete/', panel_views.delete_notification, name='delete_notification'),
]
