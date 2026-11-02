# nammal

Nammal is a complete Django REST Framework backend designed to power two specialized mobile applications:
1. **Nammal User App** (Dating customers/clients: browsing hosts, recharging coins, initiating video & audio calls)
2. **Nammal Agent App** (Verified female hosts: receiving incoming calls, earning coins, tracking performance targets, requesting withdrawals)

---

## Features
- **Phone Number + OTP Authentication:** Seamless sign-up and login using 10-digit mobile numbers and dynamic OTP verification.
- **Strict Role-Based Security:** Custom middleware and role guards separating customers (`role: "user"`) and hosts (`role: "agent"`).
- **Agent Lifecycle Management:** Structured review workflow (`pending`, `approved`, `rejected`, `suspended`).
- **Live Video & Audio Calling:** Powered by Agora RTC SDK with token generation and real-time state tracking.
- **Push Notifications:** Firebase Cloud Messaging (FCM) integration for instant incoming call alerts.
- **In-App Coin Economy & Wallet:** Coin purchases, deduction, earnings tracking, and withdrawal requests.
- **Modern Superadmin Panel:** Dashboard, real-time user management, call logs, financial reports, and custom brand theme.

---

## Tech Stack
- **Framework:** Django 5.x & Django REST Framework
- **Database:** SQLite (default) / MySQL
- **Real-Time Communication:** Agora RTC SDK
- **Push Notifications:** Firebase Admin SDK (FCM)
- **Authentication:** Token Authentication (`Authorization: Token <token>`)

---

## Getting Started

### 1. Setup Environment
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
AGORA_APP_ID=your_agora_app_id
AGORA_APP_CERTIFICATE=your_agora_app_certificate
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=nammal
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Start Development Server
```bash
python manage.py runserver
```

---

## API Documentation
Complete endpoint specifications and mobile integration guides can be found in:
- [DUAL_APP_INTEGRATION_GUIDE.md](dating/DUAL_APP_INTEGRATION_GUIDE.md)
