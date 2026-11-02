# Nammal Dual-App Integration Guide (User App & Agent App)

This document provides complete instructions and endpoint contracts for integrating your two separate frontend applications:
1. **Nammal User App** (Dating customers/clients)
2. **Nammal Agent App** (Female hosts/agents receiving calls and earning)

---

## 1. Architecture & Role Separation

The backend uses a strict role boundary:
- **`role: "user"`** (`is_staff: false`): Regular customer who recharges coins, searches for female agents, and makes audio/video calls.
- **`role: "agent"`** (`is_staff: true`): Verified agent who receives calls, earns coins, views daily/weekly/monthly targets, and requests withdrawals.

### Approval Status Lifecycle for Agents
Agents have an `agent_status` attribute:
- **`pending`**: Application submitted. Cannot log in to the Agent App until approved by admin.
- **`approved`**: Verified by admin. Full access to the Agent App, receives calls, earns coins.
- **`rejected`**: Application was not accepted by admin.
- **`suspended`**: Temporarily blocked from receiving calls or logging in.
- **`terminated`**: Permanently blocked.

---

## 2. Standard Authentication Response

Every authentication endpoint (`/api/user/login/`, `/api/agent/login/`, `/api/user/phone-auth/`, `/api/agent/phone-auth/`, `/api/user/register/`, `/api/agent/register/`) returns a standardized payload:

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "role": "user" | "agent",
  "is_agent": false | true,
  "agent_status": "approved" | "pending" | null,
  "user": {
    "id": 15,
    "username": "9876543210",
    "email": "user@gmail.com",
    "phone_number": "9876543210",
    "is_online": true,
    "is_on_call": false,
    "coins": 150,
    "is_agent": false,
    "role": "user",
    "agent_status": null
  },
  "message": "Login successful"
}
```

> **Header for Authenticated Requests:**
> ```http
> Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
> ```

---

## 3. Nammal User App (Client / Customer)

### A. Authentication (Phone Number + OTP Driven)
| Method | Endpoint | Description | Guard |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/user/send-otp/` | Request/Send OTP to 10-digit phone number | Public |
| `POST` | `/api/user/register/` | Register new customer with `phone_number`, `otp`, `name`, `age` | Sets `is_staff=False` (No password required) |
| `POST` | `/api/user/login/` | Customer login with `phone_number` and `otp` | Blocks agents (403) |
| `POST` | `/api/user/phone-auth/` | Alias for OTP login (`phone_number`, `otp`) | Blocks agents (403) |
| `POST` | `/api/logout/` | Invalidate token and set `is_online=false` | Authenticated |

#### 1. Request OTP (`POST /api/user/send-otp/`)
```json
POST /api/user/send-otp/
{
  "phone_number": "9876500001"
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "message": "OTP sent successfully to 9876500001",
  "phone_number": "9876500001",
  "otp": "1234"
}
```

> **Note:** OTP is currently set to **`1234`** for all phone numbers.

#### 2. User Signup Payload (NO password required, strictly dynamic):
```json
POST /api/user/register/
{
  "phone_number": "9876500001",
  "name": "Rahul Sharma",
  "age": 24,
  "gender": "male",
  "otp": "1234",
  "fcm_token": "optional_fcm_token_here"
}
```
**Response (201 Created):**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "role": "user",
  "is_agent": false,
  "phone_number": "9876500001",
  "name": "Rahul Sharma",
  "age": 24,
  "gender": "male",
  "user": {
    "id": 15,
    "phone_number": "9876500001",
    "name": "Rahul Sharma",
    "age": 24,
    "gender": "male",
    "username": "9876500001",
    "coins": 0,
    "role": "user",
    "profile": {
      "name": "Rahul Sharma",
      "age": 24,
      "gender": "male",
      "bio": ""
    }
  },
  "message": "User registered successfully"
}
```

#### 3. User Login Payload (Phone + OTP):
```json
POST /api/user/login/
{
  "phone_number": "9876500001",
  "otp": "1234",
  "fcm_token": "optional_fcm_token_here"
}
```
**Response (200 OK):** Returns token and user profile object.

### B. Session Bootstrap & Profile Management (User App)

#### 1. Instant Bootstrap (`/api/user/me/` or `/api/me/`)
Call this immediately upon app launch when a saved token exists to hydrate the app state (user info, profile, coin balance, unread notifications) in one roundtrip:
```http
GET /api/user/me/
Authorization: Token <user_token>
```
**Response (200 OK):**
```json
{
  "status": "success",
  "role": "user",
  "is_agent": false,
  "agent_status": null,
  "user": {
    "id": 15,
    "username": "9876500001",
    "phone_number": "9876500001",
    "email": "rahul@example.com",
    "coins": 120,
    "role": "user",
    "is_agent": false
  },
  "profile": {
    "id": 15,
    "name": "Rahul",
    "age": 24,
    "gender": "male",
    "bio": "Enjoys travel and movies",
    "profile_picture": "http://yourdomain.com/media/profile_pictures/avatar.jpg"
  },
  "coins": 120,
  "wallet_balance": 0,
  "unread_notifications": 2,
  "is_online": true,
  "is_on_call": false
}
```

#### 2. View Profile (`GET /api/user/profile/` or `GET /api/profile/`)
```http
GET /api/user/profile/
Authorization: Token <user_token>
```

#### 3. Edit Profile (`PUT` or `PATCH /api/user/profile/`)
Supports updating `name`, `age`, `gender`, `bio`, and `email`:
```http
PATCH /api/user/profile/
Authorization: Token <user_token>
Content-Type: application/json

{
  "name": "Rahul Sharma",
  "age": 25,
  "gender": "male",
  "bio": "Software engineer & travel lover",
  "email": "rahul.sharma@gmail.com"
}
```

#### 4. Upload Avatar Image (`POST /api/profile/avatar/`)
Multipart upload. Key can be `avatar`, `image`, or `profile_picture`:
```http
POST /api/profile/avatar/
Authorization: Token <user_token>
Content-Type: multipart/form-data

[Form Data: avatar=<binary_image_file>]
```
**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Avatar uploaded successfully",
  "avatar_url": "http://yourdomain.com/media/profile_pictures/avatar.jpg",
  "profile": { ... }
}
```

### C. Browsing & Connecting with Agents
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/agents/` | Get list of all approved female agents with profiles and online status |
| `GET` | `/api/online-users/` | Get list of currently online users/agents |
| `GET` | `/api/agents/<int:agent_id>/` | View detailed public profile and stats of a specific agent |
| `GET` | `/api/profile/<int:agent_id>/` | View profile by user ID |

### D. Coins & Wallet (Customer)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/coins/` (or `/api/user/coins/`) | Get current coin balance, wallet balance, and recent transaction history |
| `POST` | `/api/coins/add/` (or `/api/user/coins/add/`) | Add coins after in-app purchase or payment gateway (`coins` or `amount`, optional `reference_id`) |
| `POST` | `/api/coins/deduct/` | Deduct coins for spending (`{"coins": 50}`) |
| `GET` | `/api/offers/` | Get active coin discount packages/offers |
| `POST` | `/api/offers/<id>/redeem/` | Purchase/redeem coin offer package |

#### 1. Get Coin Balance (`GET /api/coins/` or `/api/user/coins/`)
```http
GET /api/user/coins/
Authorization: Token <user_token>
```
**Response (200 OK):**
```json
{
  "status": "success",
  "coins": 650,
  "wallet_balance": 0,
  "user_id": 15,
  "username": "9876500001",
  "role": "user",
  "is_agent": false,
  "transactions": [
    {
      "id": 19,
      "amount": 500,
      "transaction_type": "coin_purchase",
      "reference_id": "PAY_ORDER_987654",
      "created_at": "2026-10-31T12:04:12Z"
    }
  ]
}
```

#### 2. Add Coins (`POST /api/coins/add/` or `/api/user/coins/add/`)
Supports `coins` or `amount` (numbers or numeric strings) and optional payment reference ID:
```http
POST /api/user/coins/add/
Authorization: Token <user_token>
Content-Type: application/json

{
  "coins": 500,
  "reference_id": "PAY_ORDER_987654"
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "message": "500 coins added successfully",
  "coins_added": 500,
  "new_balance": 650,
  "transaction_id": 19,
  "reference_id": "PAY_ORDER_987654"
}
```

### E. Making Calls & Call History
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/calls/initiate/` | Call an agent (`receiver_id`, `call_type: 'video' | 'audio'`). Generates Agora token and triggers FCM push to agent. |
| `POST` | `/api/calls/<id>/status/` | End or cancel call (`status: 'completed' | 'cancelled'`) |
| `GET` | `/api/calls/history/` | View past call history (supports filters & pagination) |
| `GET` | `/api/user/calls/history/` | Dedicated alias for User App call history |
| `GET` | `/api/agent/calls/history/` | Dedicated alias for Agent App call history |

#### Call History Filters & Pagination Query Params:
- `?type=incoming` or `?type=outgoing` (default: all calls involving the user)
- `?call_type=video` or `?call_type=audio`
- `?status=completed` / `missed` / `rejected` / `accepted` / `cancelled`
- `?page=1` & `?page_size=20` (returns wrapped response with `total` and `page`)

#### Call History Item Schema (`GET /api/calls/history/`):
```json
[
  {
    "id": 211,
    "call_type": "video",
    "channel_name": "2f3d919f-...",
    "start_time": "2026-10-31T12:00:00Z",
    "end_time": "2026-10-31T12:04:30Z",
    "status": "completed",
    "call_duration_seconds": 270,
    "call_duration_formatted": "4m 30s",
    "coins_earned": 50,
    "caller": {
      "id": 15,
      "username": "9876500001",
      "role": "user",
      "profile": {
        "name": "Rahul Sharma",
        "gender": "male",
        "profile_picture": "http://domain.com/media/profile_pictures/rahul.jpg"
      }
    },
    "receiver": {
      "id": 16,
      "username": "9876500002",
      "role": "agent",
      "profile": {
        "name": "Priya Verma",
        "gender": "female",
        "profile_picture": "http://domain.com/media/profile_pictures/priya.jpg"
      }
    }
  }
]
```

### F. Becoming an Agent
Customers who want to become agents can submit an application from the User App:
- `POST /api/agent/apply/` (Submits agent application)
- `GET /api/agent/my-application/` (Checks review status: `pending`, `approved`, `rejected`)

---

## 4. Nammal Agent App (Female Host / Agent)

### A. Authentication & Onboarding (Phone Number + OTP Driven)
| Method | Endpoint | Description | Guard |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/agent/send-otp/` | Send OTP to agent phone number | Public |
| `POST` | `/api/agent/login/` | Agent login with `phone_number` and `otp` | Must be `is_staff=True` & `agent_status='approved'` |
| `POST` | `/api/agent/phone-auth/` | Alias for Agent OTP login | Must be `is_staff=True` & `agent_status='approved'` |
| `POST` | `/api/agent/register/` | Agent registration with `phone_number`, `otp`, `name`, `age` | Creates account with `agent_status='pending'` |
| `POST` | `/api/logout/` | Invalidate token, clear online & on-call flags | Authenticated |

#### Agent Registration Payload (Phone + OTP):
```json
POST /api/agent/register/
{
  "phone_number": "9876500002",
  "name": "Priya",
  "age": 22,
  "otp": "8551",
  "bio": "Friendly, love travel & late night talks!",
  "reason": "Looking to host live video calls",
  "experience": "6 months video chatting",
  "fcm_token": "fcm_agent_token_here"
}
```
*Response returns `agent_status: "pending"`. Once the admin approves the agent in the admin panel, the agent can log in.*

#### Agent Login Payload:
```json
POST /api/agent/login/
{
  "phone_number": "9876500002",
  "otp": "8551",
  "fcm_token": "optional_fcm_token_here"
}
```

### B. Availability, Dashboard & Profile Management (Agent App)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/agent/toggle-status/` | Toggle agent availability (`{"is_online": true | false}`) |
| `GET` | `/api/agent/me/` | Instant bootstrap: Profile, wallet balance, daily call targets, notifications |
| `GET` | `/api/agent/dashboard/` | Real-time stats: Today's earnings, total duration, daily/weekly/monthly targets vs completion |
| `GET` | `/api/agent/profile/` | Fetch agent's own profile and performance stats via Bearer Token |
| `PUT` / `PATCH` | `/api/agent/profile/` | Update agent display name, age, bio |
| `POST` | `/api/agent/profile/avatar/` | Dedicated multipart avatar image upload |

#### Agent Instant Bootstrap (`/api/agent/me/`)
```http
GET /api/agent/me/
Authorization: Token <agent_token>
```
**Response (200 OK):**
```json
{
  "status": "success",
  "role": "agent",
  "is_agent": true,
  "agent_status": "approved",
  "user": {
    "id": 16,
    "username": "9876500002",
    "phone_number": "9876500002",
    "email": "priya@example.com",
    "coins": 0,
    "role": "agent",
    "is_agent": true
  },
  "profile": {
    "id": 16,
    "name": "Priya",
    "age": 22,
    "gender": "female",
    "bio": "Friendly host ready for calls!",
    "profile_picture": "http://yourdomain.com/media/profile_pictures/priya.jpg"
  },
  "wallet_balance": 350,
  "unread_notifications": 1,
  "is_online": true,
  "is_on_call": false,
  "agent_stats": {
    "today_completed_calls": 8,
    "daily_call_target": 50,
    "rating": 4.9
  }
}
```

#### Edit Agent Profile (`PUT` or `PATCH /api/agent/profile/`)
```http
PATCH /api/agent/profile/
Authorization: Token <agent_token>
Content-Type: application/json

{
  "name": "Priya Queen",
  "age": 23,
  "bio": "Certified host & love casual conversations"
}
```

### C. Receiving Calls
When a user calls the agent:
1. Agent receives FCM push notification with:
   ```json
   {
     "type": "incoming_call",
     "call_id": "209",
     "channel_name": "6651e246-...",
     "caller_id": "15",
     "caller_name": "Rahul",
     "call_type": "video"
   }
   ```
2. Agent accepts the call:
   ```http
   POST /api/calls/209/status/
   Authorization: Token <agent_token>
   {
     "status": "accepted"
   }
   ```
   **Response contains receiver Agora token:**
   ```json
   {
     "message": "Call status updated to accepted",
     "token": "006...",
     "channel_name": "6651e246-...",
     "uid": 16
   }
   ```
3. Agent joins the Agora channel using `token` and `channel_name`.
4. When call ends:
   ```http
   POST /api/calls/209/status/
   Authorization: Token <agent_token>
   {
     "status": "completed"
   }
   ```
   *Backend automatically credits coins to the Agent's wallet and records the transaction.*

### D. Wallet & Withdrawals
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/agent/wallet/` | View current coin earnings balance & transaction history |
| `POST` | `/api/agent/withdraw/` | Submit withdrawal request (`{"amount": 500}`) |

---

## 5. End-to-End Call Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as User App (Client)
    participant Backend as Django REST Backend
    participant FCM as Firebase Cloud Messaging
    actor Agent as Agent App (Host)

    User->>Backend: POST /api/calls/initiate/ { receiver_id: 16, call_type: "video" }
    Backend->>Backend: Deduct/Verify coins, create CallHistory (status: initiated)
    Backend->>FCM: Push notification to Agent FCM Token
    Backend-->>User: Returns call_id, channel_name, caller Agora Token
    User->>User: Joins Agora Channel & plays ringing sound

    FCM-->>Agent: Shows incoming call screen with Caller Name
    alt Agent Accepts Call
        Agent->>Backend: POST /api/calls/<id>/status/ { status: "accepted" }
        Backend->>Backend: Sets is_on_call=True for both
        Backend->>FCM: Push 'call_accepted' notification to User
        Backend-->>Agent: Returns receiver Agora Token & channel_name
        Agent->>Agent: Joins Agora Channel (Call starts!)
        FCM-->>User: User receives notification, call connected!
    else Agent Rejects Call
        Agent->>Backend: POST /api/calls/<id>/status/ { status: "rejected" }
        Backend->>FCM: Push 'call_rejected' notification to User
        Backend-->>Agent: 200 OK
        FCM-->>User: Caller screen dismissed
    end

    Note over User,Agent: Audio / Video conversation in progress

    User->>Backend: POST /api/calls/<id>/status/ { status: "completed" }
    Backend->>Backend: Calculate duration, credit agent wallet, set is_on_call=False
    Backend-->>User: Returns call duration and remaining balance
```

---

## 6. Security & Account Management (Both Apps)

| Endpoint | Method | Auth Required | Purpose |
| :--- | :--- | :--- | :--- |
| `/api/change-password/` | `POST` | Yes (`Bearer Token`) | Change password for logged-in user or agent |
| `/api/reset-password/` | `POST` | No (`AllowAny`) | Forgot password reset via 10-digit number & OTP |
| `/api/delete-account/` | `POST` / `DELETE` | Yes (`Bearer Token`) | Account deletion compliance (App Store / Play Store) |

#### 1. Change Password (`POST /api/change-password/`)
```http
POST /api/change-password/
Authorization: Token <token>
Content-Type: application/json

{
  "old_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword456!"
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "token": "new_refreshed_auth_token_here",
  "message": "Password changed successfully."
}
```

#### 2. Forgot / Reset Password (`POST /api/reset-password/`)
```http
POST /api/reset-password/
Content-Type: application/json

{
  "phone_number": "9876500001",
  "otp": "123456",
  "new_password": "BrandNewPassword789!"
}
```
**Response (200 OK):**
```json
{
  "status": "success",
  "token": "auth_token_here",
  "role": "user",
  "message": "Password reset successfully. You are now logged in."
}
```

#### 3. Delete Account (`POST /api/delete-account/` or `DELETE /api/profile/`)
Mandatory compliance endpoint for Google Play Store and Apple App Store user account deletion:
```http
POST /api/delete-account/
Authorization: Token <token>
```
**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Your account has been deleted successfully."
}
```

---

## 7. Shared Notifications & Legal Endpoints

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/api/fcm-token/` | `POST` | Register/Update FCM device push token (`{"fcm_token": "..."}`) |
| `/api/notifications/` | `GET` | Retrieve in-app notifications (unread count & list) |
| `/api/notifications/<id>/read/` | `POST` | Mark specific notification as read |
| `/api/notifications/read-all/` | `POST` | Mark all notifications as read |
| `/api/terms-conditions/` | `GET` | Terms & Conditions |
| `/api/privacy-policy/` | `GET` | Privacy Policy |
| `/api/help-line/` | `GET` | Customer & Agent Support Helpline |

---

## 7. Error Handling Reference

| Error Case | HTTP Status | Response |
| :--- | :--- | :--- |
| Agent tries to log into User App | `403 Forbidden` | `{"error": "This account is registered as an Agent. Please use the Nammal Agent App to log in."}` |
| User tries to log into Agent App | `403 Forbidden` | `{"error": "Access denied. This account is not registered as an Agent. Please use the Nammal User App."}` |
| Pending agent tries to log in | `403 Forbidden` | `{"error": "Your agent application is pending admin review. You will be notified once approved."}` |
| Suspended agent tries to log in | `403 Forbidden` | `{"error": "Your agent account has been suspended by administration. Please contact support."}` |
| User tries to call with < 10 coins | `402 Payment Required` | `{"error": "Insufficient coin balance to initiate a call. Please recharge your coins."}` |
| Insufficient withdrawal balance | `400 Bad Request` | `{"error": "Insufficient balance. Minimum withdrawal is 500 coins."}` |

---

## 8. Nammal Admin Panel REST APIs

For administrative operations, web dashboards, and mobile admin tools, complete REST APIs are available under `/api/admin/...`. See the complete specification in [ADMIN_API_DOCUMENTATION.md](file:///c:/Users/SONA/OneDrive/Desktop/Empire/Nammal/Dating%20app/dating/ADMIN_API_DOCUMENTATION.md).

Key admin API endpoint groups:
- **Admin Auth**: `POST /api/admin/login/`, `POST /api/admin/logout/`, `GET /api/admin/me/`
- **Dashboard Stats**: `GET /api/admin/dashboard/`
- **Users Governance**: `GET /api/admin/users/`, `POST /api/admin/users/<id>/coins/`, `PATCH /api/admin/users/<id>/status/`
- **Agents Governance**: `GET /api/admin/agents/`, `POST /api/admin/agents/<id>/status/`, `GET /api/admin/agents/<id>/paysheet-pdf/`
- **Applications**: `GET /api/admin/agent-applications/`, `POST /api/admin/agent-applications/<id>/approve/`, `POST /api/admin/agent-applications/<id>/reject/`
- **Withdrawals**: `GET /api/admin/withdrawals/`, `POST /api/admin/withdrawals/<id>/approve/`, `POST /api/admin/withdrawals/<id>/reject/`
- **Calls & Transactions**: `GET /api/admin/calls/`, `GET /api/admin/transactions/`
- **Push Broadcasts**: `POST /api/admin/notifications/broadcast/`
- **Task Targets & Settings**: `GET /api/admin/tasks/`, `GET /api/admin/settings/`

