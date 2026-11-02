# Dating App API

A comprehensive Django REST API for a dating application with user authentication, profile management, and social features.

## Features

- 🔐 **User Authentication**: Google signup, phone signup, traditional login
- 👤 **Profile Management**: Create and update user profiles
- 💰 **Coin System**: Virtual currency for premium features
- 🎁 **Offers & Promotions**: Special offers and coin redemption
- 👥 **User Discovery**: Online users and on-call users listing
- 📋 **Legal Pages**: Terms & Conditions, Privacy Policy, Help Line
- 🎮 **Status Management**: Online/On-call status tracking

## API Endpoints

### Authentication
- `POST /api/register/` - Register new user with profile
- `POST /api/google-auth/` - Google authentication
- `POST /api/phone-auth/` - Phone number authentication with OTP
- `POST /api/login/` - Traditional username/password login
- `POST /api/logout/` - Logout user

### Profile Management
- `GET /api/profile/` - Get current user profile
- `PUT /api/profile/` - Update current user profile
- `GET /api/profile/<user_id>/` - Get another user's profile
- `POST /api/update-status/` - Update online/on-call status

### Menu Items
- `GET /api/menu/` - Get all menu items
- `GET /api/terms-conditions/` - Get terms and conditions
- `GET /api/privacy-policy/` - Get privacy policy
- `GET /api/help-line/` - Get help line information

### User Listings
- `GET /api/online-users/` - Get list of online users
- `GET /api/on-call-users/` - Get list of users on call
- `GET /api/users/` - Get all users with pagination

### Coins & Offers
- `GET /api/coins/` - Get user's coin balance
- `POST /api/coins/add/` - Add coins to user account
- `POST /api/coins/deduct/` - Deduct coins from user account
- `GET /api/offers/` - Get all active offers
- `GET /api/offers/<offer_id>/` - Get specific offer details
- `POST /api/offers/<offer_id>/redeem/` - Redeem an offer

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

4. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## Sample Usage

### User Registration
```bash
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "phone_number": "+1234567890",
    "password": "securepassword123",
    "profile": {
      "name": "John Doe",
      "age": 25,
      "gender": "male",
      "phone_number": "+1234567890"
    }
  }'
```

### Google Authentication
```bash
curl -X POST http://localhost:8000/api/google-auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "google_id": "google_user_id_123",
    "email": "user@gmail.com",
    "name": "John Smith"
  }'
```

### Get Online Users
```bash
curl -X GET http://localhost:8000/api/online-users/ \
  -H "Authorization: Token your_auth_token"
```

## Models

### User
- username, email, phone_number
- is_online, is_on_call
- coins balance
- Google authentication support

### Profile
- name, age, gender
- bio, profile_picture
- verification status

### Offer
- title, description
- coin_value
- start_date, end_date
- active status

## Authentication

The API uses token-based authentication. Include the token in the Authorization header:
```
Authorization: Token your_token_here
```

## Development Notes

- CORS is configured for development (allows all origins)
- Media files are served during development
- Uses SQLite database by default
- Passwords are hashed using Django's built-in security

## Admin Interface

Access the Django admin interface at `/admin/` to manage:
- Users and profiles
- Offers and promotions
- Legal documents
- User activities and logs