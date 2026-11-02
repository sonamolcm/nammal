from django.urls import path, include
from . import views

urlpatterns = [
    # ==========================================
    # ADMIN PANEL REST APIS (/api/admin/...)
    # ==========================================
    path('api/admin/', include('app.admin_api_urls')),

    # ==========================================
    # USER APP DEDICATED AUTHENTICATION & SESSION
    # ==========================================
    path('api/user/send-otp/', views.send_otp, name='user_send_otp'),
    path('api/user/register/', views.user_register, name='user_register'),
    path('api/user/login/', views.user_app_login, name='user_app_login'),
    path('api/user/phone-auth/', views.user_app_phone_auth, name='user_app_phone_auth'),
    path('api/user/google-auth/', views.user_app_google_auth, name='user_app_google_auth'),
    path('api/user/profile/', views.user_profile, name='user_profile_alias'),
    path('api/user/me/', views.get_current_user, name='user_me'),
    path('api/user/coins/', views.get_user_coins, name='user_coins_app'),
    path('api/user/coins/add/', views.add_coins, name='user_add_coins_app'),
    path('api/user/calls/history/', views.get_call_history, name='user_call_history_app'),

    # ==========================================
    # AGENT APP DEDICATED AUTHENTICATION & OPERATIONS
    # ==========================================
    path('api/agent/send-otp/', views.send_otp, name='agent_send_otp'),
    path('api/agent/register/', views.agent_register, name='agent_register'),
    path('api/agent/login/', views.agent_login, name='agent_login'),
    path('api/agent/phone-auth/', views.agent_phone_auth, name='agent_phone_auth'),
    path('api/agent/me/', views.get_current_user, name='agent_me'),
    path('api/agent/toggle-status/', views.agent_toggle_status, name='agent_toggle_status'),
    path('api/agent/dashboard/', views.agent_dashboard, name='agent_dashboard'),
    path('api/agent/profile/', views.agent_profile, name='agent_profile'),
    path('api/agent/profile/avatar/', views.upload_avatar, name='agent_upload_avatar'),
    path('api/agent/wallet/', views.agent_wallet, name='agent_wallet'),
    path('api/agent/withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('api/agent/apply/', views.apply_for_agent, name='apply_for_agent'),
    path('api/agent/my-application/', views.get_my_agent_application, name='get_my_agent_application'),
    path('api/agents/', views.get_all_agents, name='all_agents'),
    path('api/agents/<int:user_id>/', views.get_user_profile, name='agent_detail'),
    path('api/agent/calls/history/', views.get_call_history, name='agent_call_history_app'),

    # ==========================================
    # SHARED PROFILE, AVATAR & ACCOUNT MANAGEMENT
    # ==========================================
    path('api/me/', views.get_current_user, name='me'),
    path('api/profile/', views.user_profile, name='user_profile'),
    path('api/profile/avatar/', views.upload_avatar, name='upload_avatar'),
    path('api/profile/<int:user_id>/', views.get_user_profile, name='get_user_profile'),
    path('api/update-status/', views.update_user_status, name='update_user_status'),
    path('api/change-password/', views.change_password, name='change_password'),
    path('api/reset-password/', views.reset_password, name='reset_password'),
    path('api/forgot-password/', views.reset_password, name='forgot_password'),
    path('api/delete-account/', views.delete_account, name='delete_account'),

    # ==========================================
    # GENERAL / SHARED AUTHENTICATION (BACKWARD COMPATIBLE)
    # ==========================================
    path('api/send-otp/', views.send_otp, name='send_otp'),
    path('api/register/', views.register_user, name='register'),
    path('api/google-auth/', views.google_auth, name='google_auth'),
    path('api/phone-auth/', views.phone_auth, name='phone_auth'),
    path('api/login/', views.user_login, name='login'),
    path('api/logout/', views.user_logout, name='logout'),

    # User & Agent Listing URLs
    path('api/online-users/', views.get_online_users, name='online_users'),
    path('api/on-call-users/', views.get_on_call_users, name='on_call_users'),
    path('api/users/', views.get_all_users, name='all_users'),

    # Coins, Wallets & Offers URLs
    path('api/coins/', views.get_user_coins, name='user_coins'),
    path('api/coins/add/', views.add_coins, name='add_coins'),
    path('api/coins/deduct/', views.deduct_coins, name='deduct_coins'),
    path('api/offers/', views.get_active_offers, name='active_offers'),
    path('api/offers/<int:offer_id>/', views.get_offer_detail, name='offer_detail'),
    path('api/offers/<int:offer_id>/redeem/', views.redeem_offer, name='redeem_offer'),

    # FCM Push Notification & Calling URLs
    path('api/fcm-token/', views.update_fcm_token, name='update_fcm_token'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('api/calls/initiate/', views.initiate_call, name='initiate_call'),
    path('api/calls/<int:call_id>/status/', views.update_call_status, name='update_call_status'),
    path('api/calls/history/', views.get_call_history, name='get_call_history'),

    # Legal & Support URLs
    path('api/menu/', views.menu_items, name='menu_items'),
    path('api/terms-conditions/', views.get_terms_conditions, name='terms_conditions'),
    path('api/privacy-policy/', views.get_privacy_policy, name='privacy_policy'),
    path('api/help-line/', views.get_help_line, name='help_line'),
]


