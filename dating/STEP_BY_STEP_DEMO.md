# Dating App API - Step-by-Step Working Demo

## Prerequisites
Make sure you have:
- Python 3.8+
- Django installed
- Required packages from requirements.txt

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install requests
```

### 2. Run the Django Server
```bash
cd "c:\Users\user\Desktop\Dating app\dating"
python manage.py runserver
```

The server should start at: http://127.0.0.1:8000

### 3. Test API Endpoints

Here's a step-by-step guide to test all the API endpoints:

## Step 1: User Registration

**Endpoint:** `POST /api/register/`

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice123",
    "email": "alice@example.com",
    "phone_number": "+1234567890",
    "password": "securepassword123",
    "profile": {
      "name": "Alice Johnson",
      "age": 25,
      "gender": "female",
      "phone_number": "+1234567890",
      "bio": "Love to travel and meet new people!"
    }
  }'
```

**Expected Response:**
```json
{
  "token": "your_auth_token_here",
  "user": {
    "id": 1,
    "username": "alice123",
    "email": "alice@example.com",
    "phone_number": "+1234567890",
    "is_online": false,
    "is_on_call": false,
    "coins": 0,
    "created_at": "2026-02-05T10:30:00Z"
  },
  "message": "User registered successfully"
}
```

## Step 2: User Login

**Endpoint:** `POST /api/login/`

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice123",
    "password": "securepassword123"
  }'
```

## Step 3: Get User Profile

**Endpoint:** `GET /api/profile/`

**Request:**
```bash
curl -X GET http://127.0.0.1:8000/api/profile/ \
  -H "Authorization: Token your_token_here"
```

## Step 4: Update User Profile

**Endpoint:** `PUT /api/profile/`

**Request:**
```bash
curl -X PUT http://127.0.0.1:8000/api/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token_here" \
  -d '{
    "bio": "Updated bio - Love hiking and photography!",
    "age": 26
  }'
```

## Step 5: Get Menu Items

**Endpoint:** `GET /api/menu/`

**Request:**
```bash
curl -X GET http://127.0.0.1:8000/api/menu/ \
  -H "Authorization: Token your_token_here"
```

## Step 6: Get Legal Documents

**Terms & Conditions:**
```bash
curl -X GET http://127.0.0.1:8000/api/terms-conditions/
```

**Privacy Policy:**
```bash
curl -X GET http://127.0.0.1:8000/api/privacy-policy/
```

**Help Line:**
```bash
curl -X GET http://127.0.0.1:8000/api/help-line/
```

## Step 7: User Status Management

**Set User Online:**
```bash
curl -X POST http://127.0.0.1:8000/api/update-status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token_here" \
  -d '{
    "status_type": "online",
    "is_active": true
  }'
```

## Step 8: Get Online Users

**Endpoint:** `GET /api/online-users/`

**Request:**
```bash
curl -X GET http://127.0.0.1:8000/api/online-users/ \
  -H "Authorization: Token your_token_here"
```

## Step 9: Coin Management

**Get Coin Balance:**
```bash
curl -X GET http://127.0.0.1:8000/api/coins/ \
  -H "Authorization: Token your_token_here"
```

**Add Coins:**
```bash
curl -X POST http://127.0.0.1:8000/api/coins/add/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token_here" \
  -d '{
    "coins": 100
  }'
```

## Step 10: Offers System

**Get Active Offers:**
```bash
curl -X GET http://127.0.0.1:8000/api/offers/
```

**Redeem an Offer:**
```bash
curl -X POST http://127.0.0.1:8000/api/offers/1/redeem/ \
  -H "Authorization: Token your_token_here"
```

## Step 11: User Listings

**Get All Users (Paginated):**
```bash
curl -X GET "http://127.0.0.1:8000/api/users/?page=1&page_size=10" \
  -H "Authorization: Token your_token_here"
```

## Step 12: Google Authentication (Alternative Signup)

**Endpoint:** `POST /api/google-auth/`

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/google-auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "google_id": "google_user_id_123",
    "email": "user@gmail.com",
    "name": "John Smith"
  }'
```

## Step 13: Phone Authentication

**Endpoint:** `POST /api/phone-auth/`

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/phone-auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "otp": "123456"
  }'
```

## Step 14: Logout

**Endpoint:** `POST /api/logout/`

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/logout/ \
  -H "Authorization: Token your_token_here"
```

## Automated Demo Script

You can also run the automated demo script:

```bash
python demo_script.py
```

This script will automatically test all the endpoints in sequence and show you the responses.

---

## FCM & Push Notifications

### 1. Register / Update FCM Device Token
When the mobile app (Flutter / Android / iOS) receives an FCM token from Firebase, register it with the backend:

**Endpoint:** `POST /api/fcm-token/`  
**Headers:** `Authorization: Token <user_auth_token>`  
**Body:**
```json
{
  "fcm_token": "fAccTEwAQSiRcfcNq4i5Cp:APA91bE..."
}
```

*(Note: `fcm_token` can also be passed directly during `/api/register/`, `/api/login/`, `/api/phone-auth/`, or `/api/google-auth/`)*

### 2. Admin Panel Push Notification Control
Admins can send and broadcast push notifications from the Nammal Admin Panel:
- **URL:** `http://127.0.0.1:8000/admin-panel/notifications/`
- **Audience options:**
  - 📢 **All Users & Agents** (Broadcasts to every device)
  - 👥 **Regular Users Only**
  - 🎧 **Agents Only**
  - 🎯 **Specific User / Agent** (Targeted direct push)

### 3. Fetch In-App Notifications
Users and agents can fetch their notification inbox inside the app:

**Endpoint:** `GET /api/notifications/`  
**Headers:** `Authorization: Token <user_auth_token>`  
**Response:**
```json
{
  "count": 1,
  "unread_count": 1,
  "notifications": [
    {
      "id": 1,
      "title": "Special Offer! 🎉",
      "body": "Get 20% bonus coins today.",
      "image_url": null,
      "target_audience": "all",
      "is_read": false,
      "created_at": "2026-10-31T11:00:00Z"
    }
  ]
}
```

### 4. Mark Notification as Read
**Endpoint:** `POST /api/notifications/<notification_id>/read/`  
**Headers:** `Authorization: Token <user_auth_token>`

---

## Expected Features Working:


✅ **Welcome Screen & Authentication**
- Google signup/login
- Phone number signup/login
- Traditional username/password login

✅ **Profile Management**
- Create profile with name, age, gender, phone
- Update profile information
- View own and other users' profiles

✅ **Menu System**
- Profile access
- Terms & Conditions
- Privacy Policy
- Help Line
- Logout functionality

✅ **User Discovery**
- Online users list
- On-call users list
- User status management
- Pagination support

✅ **Coin System & Offers**
- Coin balance management
- Add/deduct coins
- Active offers listing
- Offer redemption
- Celebration wishes

## Troubleshooting

If you encounter migration errors:
1. Delete the db.sqlite3 file
2. Delete all migration files in app/migrations/ (except __init__.py)
3. Run: `python manage.py makemigrations`
4. Run: `python manage.py migrate`

If you get authentication errors:
- Make sure you're including the Authorization header with your token
- Tokens are returned when you register or login
- Tokens expire when you logout

The API is now ready for testing and integration with your frontend application!