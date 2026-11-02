# Nammal - PythonAnywhere Live API Directory

This document lists all live API endpoints for the **Nammal Backend** deployed on **PythonAnywhere**.

- **Live Base URL:** `https://nammalapi.pythonanywhere.com`
- **Admin Panel Web Dashboard:** `https://nammalapi.pythonanywhere.com/admin-panel/`
- **Standard Auth Header:**
  ```http
  Authorization: Token <your_auth_token>
  Content-Type: application/json
  ```

---

## 1. Nammal User App APIs (Clients / Customers)

Base URL: `https://nammalapi.pythonanywhere.com`

### A. Authentication (OTP Driven - No Password Required)
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/send-otp/` | Request 6-digit OTP to 10-digit phone | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/register/` | Register new customer (`phone_number`, `otp`, `name`, `age`) | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/login/` | Customer login (`phone_number`, `otp`) | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/phone-auth/` | Alias for OTP login | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/google-auth/` | Google OAuth sign-in | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/logout/` | Invalidate token and set user offline | Yes (`Token`) |

#### Sample User Registration (`POST /api/user/register/`):
```json
{
  "phone_number": "9876500001",
  "name": "Rahul Sharma",
  "age": 24,
  "otp": "1234",
  "fcm_token": "optional_fcm_token"
}
```

---

### B. Session Bootstrap & Profile Management
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/user/me/` | Hydrate app state (coins, profile, user info) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/user/profile/` | Fetch user profile | Yes (`Token`) |
| `PATCH` | `https://nammalapi.pythonanywhere.com/api/user/profile/` | Update name, age, gender, bio | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/profile/avatar/` | Upload profile image (`multipart/form-data`) | Yes (`Token`) |

---

### C. Female Hosts Discovery
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agents/` | List all verified female agents | Public |
| `GET` | `https://nammalapi.pythonanywhere.com/api/online-users/` | List currently online users & agents | Public |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agents/<agent_id>/` | View public profile of a host | Public |

---

### D. Coin Recharge & Wallet
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/user/coins/` | Get current coin balance & transactions | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/user/coins/add/` | Add coins (`{"coins": 500, "reference_id": "PAY_123"}`) | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/coins/deduct/` | Deduct coins for spending (`{"coins": 50}`) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/offers/` | List available coin recharge offers | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/offers/<id>/redeem/` | Purchase/redeem coin offer | Yes (`Token`) |

---

### E. Calling & Call History
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/calls/initiate/` | Call host (`receiver_id`, `call_type: 'video'|'audio'`). Returns Agora token | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/calls/<id>/status/` | End or cancel call (`status: 'completed'|'cancelled'`) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/user/calls/history/` | View user call history (`?call_type=`, `?page=`) | Yes (`Token`) |

---

### F. Becoming an Agent (Apply to Host)
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/apply/` | Submit host application (`reason`, `experience`) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/my-application/` | Check application review status | Yes (`Token`) |

---

## 2. Nammal Agent App APIs (Female Hosts / Agents)

Base URL: `https://nammalapi.pythonanywhere.com`

### A. Authentication & Onboarding
| Method | Full Live URL | Description | Guard |
| :--- | :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/send-otp/` | Send OTP to agent phone number | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/register/` | Agent signup with experience & bio (sets status: pending) | Public |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/login/` | Agent login with OTP (blocks non-agents & pending agents) | Approved Agents |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/phone-auth/` | Alias for agent login | Approved Agents |
| `POST` | `https://nammalapi.pythonanywhere.com/api/logout/` | Invalidate token, clear online/on-call flags | Yes (`Token`) |

---

### B. Dashboard, Availability & Performance
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/me/` | Instant bootstrap: Profile, wallet balance, daily call targets | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/toggle-status/` | Toggle availability (`{"is_online": true|false}`) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/dashboard/` | Real-time earnings, daily/weekly/monthly target progress | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/profile/` | Fetch agent's profile and stats | Yes (`Token`) |
| `PATCH` | `https://nammalapi.pythonanywhere.com/api/agent/profile/` | Update agent display name, age, bio | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/profile/avatar/` | Upload host avatar picture | Yes (`Token`) |

---

### C. Receiving Calls & Earning
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/calls/<id>/status/` | Accept call (`status: "accepted"`, returns Agora token) or reject (`status: "rejected"`) or end (`status: "completed"`) | Yes (`Token`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/calls/history/` | View received call history & duration | Yes (`Token`) |

---

### D. Earnings Wallet & Withdrawals
| Method | Full Live URL | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/agent/wallet/` | Current coin earnings balance & transaction history | Yes (`Token`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/agent/withdraw/` | Request cash withdrawal (`{"amount": 500}`) | Yes (`Token`) |

---

## 3. Nammal Admin Panel REST APIs

Base URL: `https://nammalapi.pythonanywhere.com`

All Admin REST endpoints require superadmin credentials (`is_superuser=True`).

### A. Admin Authentication
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/login/` | Admin login (`username`, `password`). Returns token. |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/logout/` | Invalidate admin token |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/me/` | Current admin user details |

---

### B. Dashboard Analytics
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/dashboard/` | Full platform metrics (users, agents, calls, coins, queues) |

---

### C. Client Users Governance
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/users/` | List users (`?search=`, `?status=online|offline`, `?page=`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/users/<id>/` | User details, profile, call stats, transactions, calls |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/users/<id>/coins/` | Credit/debit coins (`{"action": "add"|"deduct", "coins": 100}`) |
| `PATCH` | `https://nammalapi.pythonanywhere.com/api/admin/users/<id>/status/` | Ban/unban user (`is_active`) and verify profile |
| `DELETE` | `https://nammalapi.pythonanywhere.com/api/admin/users/<id>/delete/` | Delete user account |

---

### D. Agents Management
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agents/` | List agents with performance tier filters (`high`, `average`, `low`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/agents/create/` | Create agent directly with profile and wallet |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agents/<id>/` | Full agent performance stats, targets, calls, wallet |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/agents/<id>/status/` | Governance: `approve`, `suspend`, `reject`, `terminate` |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agents/<id>/paysheet/` | Monthly paysheet JSON breakdown (`?year=2026&month=10`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agents/<id>/paysheet-pdf/` | Download ReportLab PDF paysheet |

---

### E. Agent Applications Management
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agent-applications/` | List applications (`?status=all|pending|approved|rejected`) |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/agent-applications/<id>/` | Detailed application view |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/agent-applications/<id>/approve/` | Approve -> upgrades user to agent (`agent_status='approved'`) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/agent-applications/<id>/reject/` | Reject application with admin notes |

---

### F. Withdrawals Management
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/withdrawals/` | List agent withdrawal requests |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/withdrawals/<id>/approve/` | Approve withdrawal |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/withdrawals/<id>/reject/` | Reject withdrawal & auto-refund coins to agent wallet |

---

### G. Calls & Ledger
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/calls/` | List calls with audio/video, status, caller/receiver filters |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/calls/<id>/` | Detailed call record |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/transactions/` | Platform transactions history (`coin_purchase`, `earn_call`, `withdrawal`) |

---

### H. Offers, Tasks, Settings & Push Notifications
| Method | Full Live URL | Description |
| :--- | :--- | :--- |
| `GET` / `POST` | `https://nammalapi.pythonanywhere.com/api/admin/offers/` | List all coin packages / create new offer package |
| `PATCH` / `DELETE` | `https://nammalapi.pythonanywhere.com/api/admin/offers/<id>/` | Update or delete offer |
| `GET` / `POST` | `https://nammalapi.pythonanywhere.com/api/admin/tasks/` | View or update daily/weekly/monthly agent call targets |
| `GET` / `POST` | `https://nammalapi.pythonanywhere.com/api/admin/settings/` | View or update system rates (call coins/min, min withdrawal) |
| `POST` | `https://nammalapi.pythonanywhere.com/api/admin/notifications/broadcast/` | Send FCM push to all, clients, agents, or specific user |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/notifications/stats/` | FCM device token registration statistics |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/live/online-users/` | Currently online clients |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/live/online-agents/` | Currently online agents |
| `GET` | `https://nammalapi.pythonanywhere.com/api/admin/live/on-call/` | Active, in-progress calls |

---

## 4. How to Deploy to PythonAnywhere (1-Step Update)

To make these new APIs live on your PythonAnywhere server:

### Step 1: Push your local code to GitHub
Run in your local terminal:
```bash
git add .
git commit -m "Add Nammal Admin REST APIs, serializers, routing and PythonAnywhere docs"
git push origin main
```

### Step 2: Run the update script on PythonAnywhere
Open a **Bash Console** in your [PythonAnywhere Dashboard](https://www.pythonanywhere.com/user/nammalapi/consoles/) and run:
```bash
cd ~/"Dating app"
bash deploy_pythonanywhere.sh
```

The script will automatically:
1. Pull the latest commits from `https://github.com/sonamolcm/nammal.git`
2. Install any new dependencies (`pip install -r requirements.txt`)
3. Apply database migrations (`python manage.py migrate`)
4. Collect static files (`python manage.py collectstatic --noinput`)
5. Reload your PythonAnywhere web app instance (`touch /var/www/*_wsgi.py`)

All endpoints will be live immediately!
