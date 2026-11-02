# Dating App API - Complete Working Demo

## 🚀 Quick Start

**Server is running at:** http://127.0.0.1:8000

## 📋 What's Included

### 1. **Complete API Implementation**
- ✅ User Authentication (Google, Phone, Traditional)
- ✅ Profile Management (Create, Read, Update)
- ✅ Menu System (Profile, Terms, Privacy, Help)
- ✅ User Discovery (Online/On-call users)
- ✅ Coin Management System
- ✅ Offers & Promotions
- ✅ Status Management

### 2. **Documentation & Tools**
- 📖 `README.md` - Complete API documentation
- 📋 `STEP_BY_STEP_DEMO.md` - Detailed testing guide
- 🛠️ `demo_script.py` - Automated Python demo
- 📦 `DatingApp_API.postman_collection.json` - Postman collection
- 📄 `requirements.txt` - Dependencies list

## 🎯 Testing the API

### Method 1: Automated Demo Script
```bash
python demo_script.py
```

### Method 2: Manual Testing with curl
```bash
# Register a user
curl -X POST http://127.0.0.1:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "phone_number": "+1234567890",
    "password": "password123",
    "profile": {
      "name": "Test User",
      "age": 25,
      "gender": "female",
      "phone_number": "+1234567890"
    }
  }'
```

### Method 3: Postman
1. Import `DatingApp_API.postman_collection.json`
2. Set the `auth_token` variable after login
3. Test all endpoints

## 🔧 Key Features Demonstrated

### Authentication Flow
1. **Registration** - Create account with profile
2. **Login** - Multiple authentication methods
3. **Token Management** - Secure API access

### Profile System
1. **Profile Creation** - Name, age, gender, phone, bio
2. **Profile Updates** - Modify personal information
3. **Profile Viewing** - Access own and others' profiles

### Social Features
1. **Online Status** - Set user as online/offline
2. **On-Call Status** - Track call availability
3. **User Discovery** - Find online and on-call users

### Economy System
1. **Coin Balance** - Virtual currency management
2. **Add/Deduct Coins** - Transaction handling
3. **Offers System** - Promotions and rewards
4. **Offer Redemption** - Convert offers to coins

### Legal & Support
1. **Terms & Conditions** - Access legal documents
2. **Privacy Policy** - Privacy information
3. **Help Line** - Support contact information
4. **Menu System** - Easy navigation

## 📊 Sample Data Available

The system includes sample data for:
- Terms & Conditions
- Privacy Policy
- Help Line information
- Sample offers (Welcome Bonus, Valentine's Special)

## 🔐 Security Features

- **Token-based Authentication**
- **Password Hashing**
- **CORS Configuration**
- **Input Validation**
- **Error Handling**

## 🛠️ Technical Stack

- **Backend:** Django 5.1.5
- **API Framework:** Django REST Framework 3.15.2
- **Database:** SQLite (development)
- **Authentication:** Token-based
- **Media Handling:** Pillow for image processing

## 🎮 API Endpoints Summary

| Category | Endpoint | Method | Description |
|----------|----------|---------|-------------|
| Auth | `/api/register/` | POST | User registration |
| Auth | `/api/login/` | POST | User login |
| Auth | `/api/logout/` | POST | User logout |
| Auth | `/api/google-auth/` | POST | Google authentication |
| Auth | `/api/phone-auth/` | POST | Phone authentication |
| Profile | `/api/profile/` | GET/PUT | Manage profile |
| Menu | `/api/menu/` | GET | Get menu items |
| Legal | `/api/terms-conditions/` | GET | Terms & Conditions |
| Legal | `/api/privacy-policy/` | GET | Privacy Policy |
| Legal | `/api/help-line/` | GET | Help Line info |
| Users | `/api/online-users/` | GET | Online users list |
| Users | `/api/on-call-users/` | GET | On-call users list |
| Users | `/api/users/` | GET | All users (paginated) |
| Coins | `/api/coins/` | GET | Get coin balance |
| Coins | `/api/coins/add/` | POST | Add coins |
| Coins | `/api/coins/deduct/` | POST | Deduct coins |
| Offers | `/api/offers/` | GET | Active offers |
| Offers | `/api/offers/<id>/redeem/` | POST | Redeem offer |

## 🎯 Next Steps

1. **Test all endpoints** using the methods above
2. **Integrate with frontend** application
3. **Customize** for your specific requirements
4. **Deploy** to production environment
5. **Add more features** as needed

The API is fully functional and ready for production use!