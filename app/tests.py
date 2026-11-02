from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from .models import (
    User, Profile, Offer, CallHistory, Wallet, Transaction,
    WithdrawalRequest, AgentApplication, Notification, AgentTaskConfig, GlobalSetting
)


class AdminRestAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Superadmin user
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@nammal.com',
            password='AdminPassword123!',
            phone_number='9999999999'
        )

        # 2. Regular User (client)
        self.user = User.objects.create_user(
            username='rahul_user',
            email='rahul@gmail.com',
            password='UserPass123!',
            phone_number='9876543210',
            coins=100
        )
        self.user_profile = Profile.objects.create(
            user=self.user,
            name='Rahul Sharma',
            age=24,
            gender='male',
            phone_number='9876543210',
            bio='Hello Nammal'
        )
        self.user_wallet = Wallet.objects.create(user=self.user, balance=100)

        # 3. Agent User
        self.agent = User.objects.create_user(
            username='priya_agent',
            email='priya@gmail.com',
            password='AgentPass123!',
            phone_number='9876543211',
            is_staff=True,
            agent_status='approved'
        )
        self.agent_profile = Profile.objects.create(
            user=self.agent,
            name='Priya Verma',
            age=22,
            gender='female',
            phone_number='9876543211'
        )
        self.agent_wallet = Wallet.objects.create(user=self.agent, balance=500)

    def _auth_admin(self):
        """Helper to log in as admin and set Authorization Token header."""
        res = self.client.post('/api/admin/login/', {
            'username': 'admin_boss',
            'password': 'AdminPassword123!'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        token = res.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        return token

    # --------------------------------------------------------------------------
    # 1. Admin Authentication Tests
    # --------------------------------------------------------------------------
    def test_admin_login_success(self):
        res = self.client.post('/api/admin/login/', {
            'username': 'admin_boss',
            'password': 'AdminPassword123!'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('token', res.data)
        self.assertEqual(res.data['user']['username'], 'admin_boss')

    def test_admin_login_denies_regular_user(self):
        res = self.client.post('/api/admin/login/', {
            'username': 'rahul_user',
            'password': 'UserPass123!'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', str(res.data))

    def test_admin_me_endpoint(self):
        self._auth_admin()
        res = self.client.get('/api/admin/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['user']['username'], 'admin_boss')

    def test_admin_logout(self):
        self._auth_admin()
        res = self.client.post('/api/admin/logout/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Check that token is no longer authorized
        res2 = self.client.get('/api/admin/me/')
        self.assertEqual(res2.status_code, status.HTTP_401_UNAUTHORIZED)

    # --------------------------------------------------------------------------
    # 2. Dashboard Analytics Tests
    # --------------------------------------------------------------------------
    def test_admin_dashboard_stats(self):
        self._auth_admin()
        res = self.client.get('/api/admin/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', res.data)
        self.assertIn('users', res.data['metrics'])
        self.assertIn('agents', res.data['metrics'])
        self.assertIn('calls', res.data['metrics'])
        self.assertIn('withdrawals', res.data['metrics'])
        self.assertEqual(res.data['metrics']['users']['total'], 1)
        self.assertEqual(res.data['metrics']['agents']['total'], 1)

    # --------------------------------------------------------------------------
    # 3. Users Management Tests
    # --------------------------------------------------------------------------
    def test_admin_users_list(self):
        self._auth_admin()
        res = self.client.get('/api/admin/users/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 1)
        self.assertEqual(res.data['users'][0]['username'], 'rahul_user')

    def test_admin_user_detail(self):
        self._auth_admin()
        res = self.client.get(f'/api/admin/users/{self.user.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['user']['username'], 'rahul_user')
        self.assertEqual(res.data['user']['coins'], 100)

    def test_admin_user_adjust_coins_add_and_deduct(self):
        self._auth_admin()
        # Add 50 coins
        res_add = self.client.post(f'/api/admin/users/{self.user.id}/coins/', {
            'action': 'add',
            'coins': 50,
            'note': 'Test bonus'
        })
        self.assertEqual(res_add.status_code, status.HTTP_200_OK)
        self.assertEqual(res_add.data['new_balance'], 150)

        # Deduct 30 coins
        res_deduct = self.client.post(f'/api/admin/users/{self.user.id}/coins/', {
            'action': 'deduct',
            'coins': 30,
            'note': 'Correction'
        })
        self.assertEqual(res_deduct.status_code, status.HTTP_200_OK)
        self.assertEqual(res_deduct.data['new_balance'], 120)

    def test_admin_user_toggle_status(self):
        self._auth_admin()
        res = self.client.patch(f'/api/admin/users/{self.user.id}/status/', {
            'is_active': False,
            'is_verified': True
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.profile.is_verified)

    # --------------------------------------------------------------------------
    # 4. Agents Management Tests
    # --------------------------------------------------------------------------
    def test_admin_agents_list(self):
        self._auth_admin()
        res = self.client.get('/api/admin/agents/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 1)
        self.assertEqual(res.data['agents'][0]['username'], 'priya_agent')

    def test_admin_agent_create(self):
        self._auth_admin()
        res = self.client.post('/api/admin/agents/create/', {
            'username': 'new_host',
            'email': 'new_host@gmail.com',
            'phone_number': '9876543299',
            'password': 'SecureHostPass123!',
            'name': 'Sneha',
            'age': 21,
            'gender': 'female',
            'bio': 'Friendly host ready to chat!',
            'agent_status': 'approved'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='new_host', is_staff=True).exists())

    def test_admin_agent_status_action(self):
        self._auth_admin()
        # Suspend agent
        res = self.client.post(f'/api/admin/agents/{self.agent.id}/status/', {
            'action': 'suspend'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.agent_status, 'suspended')

        # Approve agent
        res2 = self.client.post(f'/api/admin/agents/{self.agent.id}/status/', {
            'action': 'approve'
        })
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.agent_status, 'approved')

    def test_admin_agent_paysheet_data(self):
        self._auth_admin()
        res = self.client.get(f'/api/admin/agents/{self.agent.id}/paysheet/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('calls_summary', res.data)
        self.assertIn('withdrawals_summary', res.data)

    def test_admin_agent_paysheet_pdf(self):
        self._auth_admin()
        res = self.client.get(f'/api/admin/agents/{self.agent.id}/paysheet-pdf/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.get('Content-Type'), 'application/pdf')

    # --------------------------------------------------------------------------
    # 5. Agent Applications Tests
    # --------------------------------------------------------------------------
    def test_admin_agent_applications_workflow(self):
        self._auth_admin()
        # Create applicant user and application
        applicant = User.objects.create_user(
            username='applicant_ria',
            email='ria@gmail.com',
            password='Pass123!',
            phone_number='9876543255'
        )
        app = AgentApplication.objects.create(
            user=applicant,
            reason='Love talking to people',
            experience='1 year customer host',
            status='pending'
        )

        # List applications
        res_list = self.client.get('/api/admin/agent-applications/?status=pending')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['total'], 1)

        # Approve application
        res_approve = self.client.post(f'/api/admin/agent-applications/{app.id}/approve/')
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        applicant.refresh_from_db()
        self.assertTrue(applicant.is_staff)
        self.assertEqual(applicant.agent_status, 'approved')

    # --------------------------------------------------------------------------
    # 6. Withdrawals Tests
    # --------------------------------------------------------------------------
    def test_admin_withdrawals_workflow(self):
        self._auth_admin()
        w_req = WithdrawalRequest.objects.create(
            agent=self.agent,
            amount=200,
            status='pending'
        )

        # List withdrawals
        res_list = self.client.get('/api/admin/withdrawals/?status=pending')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['total'], 1)

        # Approve withdrawal
        res_approve = self.client.post(f'/api/admin/withdrawals/{w_req.id}/approve/')
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        w_req.refresh_from_db()
        self.assertEqual(w_req.status, 'approved')

    # --------------------------------------------------------------------------
    # 7. Calls Monitoring Tests
    # --------------------------------------------------------------------------
    def test_admin_calls_list_and_detail(self):
        self._auth_admin()
        call = CallHistory.objects.create(
            caller=self.user,
            receiver=self.agent,
            channel_name='test-channel-xyz',
            call_type='video',
            status='completed',
            coins_earned=50,
            start_time=timezone.now() - timedelta(minutes=5),
            end_time=timezone.now()
        )

        res_list = self.client.get('/api/admin/calls/?status=completed')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['total'], 1)

        res_detail = self.client.get(f'/api/admin/calls/{call.id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['call']['channel_name'], 'test-channel-xyz')

    # --------------------------------------------------------------------------
    # 8. Transactions Tests
    # --------------------------------------------------------------------------
    def test_admin_transactions_list(self):
        self._auth_admin()
        Transaction.objects.create(
            user=self.user,
            amount=100,
            transaction_type='coin_purchase',
            reference_id='PAY_TEST_123'
        )

        res = self.client.get('/api/admin/transactions/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 1)

    # --------------------------------------------------------------------------
    # 9. Offers CRUD Tests
    # --------------------------------------------------------------------------
    def test_admin_offers_crud(self):
        self._auth_admin()
        # Create offer
        now = timezone.now()
        res_create = self.client.post('/api/admin/offers/', {
            'title': 'Diwali Super Saver',
            'description': 'Get 500 coins + 50 bonus',
            'coin_value': 550,
            'is_active': True,
            'start_date': now.isoformat(),
            'end_date': (now + timedelta(days=7)).isoformat()
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        offer_id = res_create.data['offer']['id']

        # Update offer
        res_update = self.client.patch(f'/api/admin/offers/{offer_id}/', {
            'title': 'Diwali Mega Saver'
        })
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data['offer']['title'], 'Diwali Mega Saver')

        # Delete offer
        res_del = self.client.delete(f'/api/admin/offers/{offer_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)
        self.assertFalse(Offer.objects.filter(id=offer_id).exists())

    # --------------------------------------------------------------------------
    # 10. Agent Task Targets Configuration Tests
    # --------------------------------------------------------------------------
    def test_admin_tasks_config(self):
        self._auth_admin()
        res_get = self.client.get('/api/admin/tasks/')
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        res_update = self.client.post('/api/admin/tasks/', {
            'daily_call_target': 60,
            'weekly_call_target': 300,
            'monthly_call_target': 1200
        })
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        config = AgentTaskConfig.load()
        self.assertEqual(config.daily_call_target, 60)

    # --------------------------------------------------------------------------
    # 11. Global Settings CRUD Tests
    # --------------------------------------------------------------------------
    def test_admin_global_settings_crud(self):
        self._auth_admin()
        res_create = self.client.post('/api/admin/settings/', {
            'key': 'video_call_rate',
            'value': '25',
            'data_type': 'int',
            'description': 'Coins deducted per minute for video calls'
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        setting_id = res_create.data['setting']['id']

        res_update = self.client.patch(f'/api/admin/settings/{setting_id}/', {
            'value': '30'
        })
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data['setting']['value'], '30')

    # --------------------------------------------------------------------------
    # 12. Push Notifications & FCM Stats Tests
    # --------------------------------------------------------------------------
    def test_admin_notification_stats_and_history(self):
        self._auth_admin()
        res_stats = self.client.get('/api/admin/notifications/stats/')
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        self.assertIn('fcm_stats', res_stats.data)

        # Create dummy notification record
        Notification.objects.create(
            title='Weekend Special',
            body='Connect with top hosts today!',
            target_audience='all',
            sent_count=10
        )

        res_list = self.client.get('/api/admin/notifications/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['total'], 1)

    # --------------------------------------------------------------------------
    # 13. Live Monitoring Tests
    # --------------------------------------------------------------------------
    def test_admin_live_monitoring(self):
        self._auth_admin()
        self.user.is_online = True
        self.user.save()

        res_users = self.client.get('/api/admin/live/online-users/')
        self.assertEqual(res_users.status_code, status.HTTP_200_OK)
        self.assertEqual(res_users.data['count'], 1)

        res_agents = self.client.get('/api/admin/live/online-agents/')
        self.assertEqual(res_agents.status_code, status.HTTP_200_OK)


class UserRegistrationAndAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_send_otp_4_digits(self):
        res = self.client.post('/api/user/send-otp/', {'phone_number': '9876500001'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('otp', res.data)
        self.assertEqual(res.data['otp'], '1234')

    def test_user_register_with_minimal_fields_and_gender(self):
        # Register user with only phone_number and gender
        res = self.client.post('/api/user/register/', {
            'phone_number': '9876500002',
            'gender': 'female'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', res.data)
        self.assertEqual(res.data['role'], 'user')
        self.assertEqual(res.data['user']['profile']['gender'], 'female')
        self.assertEqual(res.data['user']['profile']['age'], 18)
        self.assertTrue(res.data['user']['profile']['name'].startswith('User_'))

    def test_user_register_with_phone_alias_and_custom_name(self):
        # Register user with 'phone' alias instead of 'phone_number'
        res = self.client.post('/api/user/register/', {
            'phone': '9876500003',
            'name': 'Ananya',
            'age': '22',
            'gender': 'female'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user']['profile']['name'], 'Ananya')
        self.assertEqual(res.data['user']['profile']['age'], 22)
        self.assertEqual(res.data['user']['profile']['gender'], 'female')

    def test_user_register_empty_body_clear_error(self):
        res = self.client.post('/api/user/register/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', res.data)
        self.assertIn('error', res.data)
        # Verify the error tells the user specifically what is required
        self.assertIn('phone_number', res.data['error'])

    def test_user_register_camelcase_and_country_code(self):
        res = self.client.post('/api/user/register/', {
            'phoneNumber': '+919876500004',
            'fullName': 'Vikram',
            'gender': 'male'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user']['phone_number'], '9876500004')
        self.assertEqual(res.data['user']['profile']['name'], 'Vikram')

    def test_user_register_get_helper(self):
        res = self.client.get('/api/user/register/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('example_json_body', res.data)


