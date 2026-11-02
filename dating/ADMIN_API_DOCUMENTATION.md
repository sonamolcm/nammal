# Nammal Admin Panel REST API Documentation

Complete reference for the Nammal Admin REST API (`/api/admin/...`). These endpoints allow any web dashboard, React/Vue/Angular frontend, or administrative mobile app to manage Nammal's users, agents, applications, coin adjustments, calls, withdrawals, offers, settings, and push notifications.

---

## 1. Authentication & Security

All `/api/admin/...` endpoints (except `/api/admin/login/`) require Token authentication and verify that the user is an authorized Administrator (`is_superuser=True`).

### Header format:
```http
Authorization: Token <admin_token>
Content-Type: application/json
```

---

## 2. API Endpoints Overview

| Group | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/admin/login/` | Admin login with username/phone/email & password |
| **Auth** | `POST` | `/api/admin/logout/` | Invalidate admin token |
| **Auth** | `GET` | `/api/admin/me/` | Current admin user details |
| **Dashboard** | `GET` | `/api/admin/dashboard/` | Full platform analytics, metrics, recent activity |
| **Users** | `GET` | `/api/admin/users/` | List regular clients (search, status filter, pagination) |
| **Users** | `GET` | `/api/admin/users/<id>/` | User details, wallet, call stats, transactions, calls |
| **Users** | `POST` | `/api/admin/users/<id>/coins/` | Credit/debit coins with ledger transaction log |
| **Users** | `PATCH` | `/api/admin/users/<id>/status/` | Ban/unban user (`is_active`) and verify profile |
| **Users** | `DELETE` | `/api/admin/users/<id>/delete/` | Permanently delete user |
| **Agents** | `GET` | `/api/admin/agents/` | List agents (status & performance tier filters) |
| **Agents** | `POST` | `/api/admin/agents/create/` | Create new agent account directly |
| **Agents** | `GET` | `/api/admin/agents/<id>/` | Agent profile, targets vs completion, wallet, calls |
| **Agents** | `POST` | `/api/admin/agents/<id>/status/` | Governance: `approve`, `suspend`, `reject`, `terminate` |
| **Agents** | `GET` | `/api/admin/agents/<id>/paysheet/` | Monthly paysheet JSON breakdown |
| **Agents** | `GET` | `/api/admin/agents/<id>/paysheet-pdf/` | Download ReportLab PDF paysheet |
| **Applications** | `GET` | `/api/admin/agent-applications/` | List agent applications (`all`, `pending`, `approved`, `rejected`) |
| **Applications** | `GET` | `/api/admin/agent-applications/<id>/` | Detailed application view |
| **Applications** | `POST` | `/api/admin/agent-applications/<id>/approve/` | Approve application -> converts user to active agent |
| **Applications** | `POST` | `/api/admin/agent-applications/<id>/reject/` | Reject application with admin notes |
| **Withdrawals** | `GET` | `/api/admin/withdrawals/` | List agent withdrawal requests |
| **Withdrawals** | `POST` | `/api/admin/withdrawals/<id>/approve/` | Approve withdrawal request |
| **Withdrawals** | `POST` | `/api/admin/withdrawals/<id>/reject/` | Reject withdrawal request & refund coins to agent |
| **Calls** | `GET` | `/api/admin/calls/` | List calls (audio/video, status, caller/receiver filters) |
| **Calls** | `GET` | `/api/admin/calls/<id>/` | Call log detail |
| **Transactions** | `GET` | `/api/admin/transactions/` | Platform transaction ledger |
| **Offers** | `GET` / `POST` | `/api/admin/offers/` | List all coin packages / create new offer package |
| **Offers** | `GET`/`PATCH`/`DELETE` | `/api/admin/offers/<id>/` | View, update, or delete offer |
| **Tasks** | `GET` / `POST` | `/api/admin/tasks/` | View or update daily/weekly/monthly call targets |
| **Settings** | `GET` / `POST` | `/api/admin/settings/` | View all global settings / create new setting |
| **Settings** | `GET`/`PATCH`/`DELETE` | `/api/admin/settings/<id>/` | View, update, or delete global setting |
| **Notifications** | `GET` | `/api/admin/notifications/` | View notification broadcast history |
| **Notifications** | `POST` | `/api/admin/notifications/broadcast/` | Broadcast FCM push notification (all, users, agents, specific) |
| **Notifications** | `DELETE` | `/api/admin/notifications/<id>/delete/` | Delete notification from history |
| **Notifications** | `GET` | `/api/admin/notifications/stats/` | FCM device token counts & stats |
| **Live** | `GET` | `/api/admin/live/online-users/` | List currently online clients |
| **Live** | `GET` | `/api/admin/live/online-agents/` | List currently online agents |
| **Live** | `GET` | `/api/admin/live/on-call/` | List currently active/ongoing calls |

---

## 3. Detailed Request & Response Examples

### A. Admin Authentication

#### 1. Admin Login
```http
POST /api/admin/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "SuperSecretPassword123!"
}
```
*Note: `username` can also be the administrator's registered 10-digit phone number or email.*

**Response (200 OK):**
```json
{
  "status": "success",
  "token": "7a8bc6d43e5f2a1b9c8d7e6f5a4b3c2d1e0f9a8b",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@nammal.com",
    "phone_number": "9999999999",
    "is_superuser": true,
    "is_staff": true,
    "date_joined": "2026-10-15T08:00:00Z",
    "last_login": "2026-11-02T09:30:00Z"
  },
  "message": "Admin login successful."
}
```

---

### B. Dashboard Analytics (`GET /api/admin/dashboard/`)

```http
GET /api/admin/dashboard/
Authorization: Token <admin_token>
```

**Response (200 OK):**
```json
{
  "status": "success",
  "metrics": {
    "users": {
      "total": 1250,
      "online": 84,
      "new_today": 18,
      "new_this_week": 112,
      "new_this_month": 430
    },
    "agents": {
      "total": 65,
      "online": 28,
      "approved": 52,
      "pending": 8,
      "suspended": 4,
      "terminated": 1
    },
    "agent_applications": {
      "total": 78,
      "pending": 8,
      "approved": 55,
      "rejected": 15
    },
    "withdrawals": {
      "total": 142,
      "pending": 6,
      "approved": 128,
      "rejected": 8,
      "pending_coins": 18500,
      "approved_coins": 492000
    },
    "calls": {
      "total": 3840,
      "completed": 3120,
      "missed": 420,
      "rejected": 300,
      "ongoing": 5,
      "today": 145,
      "total_duration_seconds": 936000,
      "total_coins_earned": 78000
    },
    "transactions": {
      "total_count": 4820,
      "total_coin_purchases": 850000,
      "total_withdrawals": 492000
    }
  },
  "recent_calls": [ ... ],
  "pending_applications": [ ... ],
  "pending_withdrawals": [ ... ]
}
```

---

### C. Users Management

#### 1. List Users
```http
GET /api/admin/users/?search=rahul&status=all&page=1&page_size=20
Authorization: Token <admin_token>
```

#### 2. User Detail
```http
GET /api/admin/users/15/
Authorization: Token <admin_token>
```

#### 3. Adjust User Coins (Add / Deduct)
```http
POST /api/admin/users/15/coins/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "action": "add",
  "coins": 250,
  "note": "Promotional bonus credit"
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Successfully credited 250 coins to @rahul_user.",
  "action": "add",
  "coins_adjusted": 250,
  "new_balance": 400,
  "transaction_id": 98
}
```

#### 4. Ban / Unban User & Verify Profile
```http
PATCH /api/admin/users/15/status/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "is_active": false,
  "is_verified": true
}
```

---

### D. Agents Management

#### 1. List Agents with Performance Tier Filters
```http
GET /api/admin/agents/?status=approved&period=month&performance=high
Authorization: Token <admin_token>
```
*Performance tiers:*
- `high`: $\ge 100\%$ of task target
- `average`: $50\% - 99\%$ of target
- `low`: $< 50\%$ of target

#### 2. Create Agent Directly
```http
POST /api/admin/agents/create/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "username": "ananya_host",
  "email": "ananya@gmail.com",
  "phone_number": "9876500099",
  "password": "SecurePassword123!",
  "name": "Ananya Roy",
  "age": 23,
  "gender": "female",
  "bio": "Certified host passionate about music and travel",
  "agent_status": "approved"
}
```

#### 3. Agent Governance (Approve / Suspend / Reject / Terminate)
```http
POST /api/admin/agents/16/status/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "action": "suspend",
  "admin_notes": "Policy violation under review"
}
```

#### 4. Download Agent Paysheet (PDF)
```http
GET /api/admin/agents/16/paysheet-pdf/?year=2026&month=10
Authorization: Token <admin_token>
```
*Returns a binary `application/pdf` attachment formatted by ReportLab.*

---

### E. Agent Applications

#### 1. Approve Application
```http
POST /api/admin/agent-applications/5/approve/
Authorization: Token <admin_token>
```
*Instantly upgrades the user to `is_staff=True`, `agent_status='approved'`, and initializes their agent Wallet.*

#### 2. Reject Application
```http
POST /api/admin/agent-applications/5/reject/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "admin_notes": "Candidate does not meet age or verification requirements."
}
```

---

### F. Withdrawals

#### 1. Approve Withdrawal
```http
POST /api/admin/withdrawals/12/approve/
Authorization: Token <admin_token>
```

#### 2. Reject Withdrawal & Auto-Refund
```http
POST /api/admin/withdrawals/12/reject/
Authorization: Token <admin_token>
```
*Automatically restores the coins back to the agent's wallet and creates a refund transaction log.*

---

### G. Push Notifications & Broadcast

#### 1. Broadcast Notification to All Users / Agents
```http
POST /api/admin/notifications/broadcast/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "title": "Weekend Live Fest! 🌟",
  "body": "Special 20% discount on video calls this weekend. Chat now!",
  "target_audience": "all",
  "image_url": "https://domain.com/banners/weekend.jpg",
  "notification_type": "promotion"
}
```
*Audience options: `all`, `users`, `agents`, `specific` (with `recipient_id`).*

---

### H. System Settings & Agent Task Targets

#### 1. Update Daily / Weekly / Monthly Call Targets
```http
POST /api/admin/tasks/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "daily_call_target": 60,
  "weekly_call_target": 300,
  "monthly_call_target": 1200
}
```

#### 2. Update Global Setting (Call Rates / Minimum Withdrawal)
```http
PATCH /api/admin/settings/1/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "value": "25"
}
```
