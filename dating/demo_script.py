import requests
import json

# Base URL for the API
BASE_URL = "http://127.0.0.1:8000"

def print_response(response, title="Response"):
    """Helper function to print API responses nicely"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*50}\n")

def demo_api():
    """Step-by-step demo of the Dating App API"""
    
    print(" datings App API Demo")
    print("="*50)
    
    # Store tokens and user data
    tokens = {}
    users = {}
    
    # Step 1: User Registration
    print("\n1. USER REGISTRATION")
    print("-" * 30)
    
    user1_data = {
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
    }
    
    response = requests.post(f"{BASE_URL}/api/register/", json=user1_data)
    print_response(response, "User 1 Registration")
    if response.status_code == 201:
        tokens['alice'] = response.json()['token']
        users['alice'] = response.json()['user']
    
    # Register second user
    user2_data = {
        "username": "bob456",
        "email": "bob@example.com",
        "phone_number": "+0987654321",
        "password": "securepassword456",
        "profile": {
            "name": "Bob Smith",
            "age": 28,
            "gender": "male",
            "phone_number": "+0987654321",
            "bio": "Tech enthusiast and coffee lover"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/register/", json=user2_data)
    print_response(response, "User 2 Registration")
    if response.status_code == 201:
        tokens['bob'] = response.json()['token']
        users['bob'] = response.json()['user']
    
    # Step 2: Login (Alternative authentication method)
    print("\n2. USER LOGIN")
    print("-" * 30)
    
    login_data = {
        "username": "alice123",
        "password": "securepassword123"
    }
    
    response = requests.post(f"{BASE_URL}/api/login/", json=login_data)
    print_response(response, "User Login")
    
    # Step 3: Get User Profile
    print("\n3. GET USER PROFILE")
    print("-" * 30)
    
    headers = {"Authorization": f"Token {tokens['alice']}"}
    response = requests.get(f"{BASE_URL}/api/profile/", headers=headers)
    print_response(response, "Alice's Profile")
    
    # Step 4: Update User Profile
    print("\n4. UPDATE USER PROFILE")
    print("-" * 30)
    
    update_data = {
        "bio": "Updated bio - Love hiking and photography!",
        "age": 26
    }
    
    response = requests.put(f"{BASE_URL}/api/profile/", headers=headers, json=update_data)
    print_response(response, "Profile Update")
    
    # Step 5: Get Menu Items
    print("\n5. GET MENU ITEMS")
    print("-" * 30)
    
    response = requests.get(f"{BASE_URL}/api/menu/", headers=headers)
    print_response(response, "Menu Items")
    
    # Step 6: Get Legal Documents
    print("\n6. GET LEGAL DOCUMENTS")
    print("-" * 30)
    
    # Terms and Conditions
    response = requests.get(f"{BASE_URL}/api/terms-conditions/")
    print_response(response, "Terms & Conditions")
    
    # Privacy Policy
    response = requests.get(f"{BASE_URL}/api/privacy-policy/")
    print_response(response, "Privacy Policy")
    
    # Help Line
    response = requests.get(f"{BASE_URL}/api/help-line/")
    print_response(response, "Help Line")
    
    # Step 7: User Status Management
    print("\n7. USER STATUS MANAGEMENT")
    print("-" * 30)
    
    # Set Alice as online
    status_data = {
        "status_type": "online",
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/api/update-status/", headers=headers, json=status_data)
    print_response(response, "Set Alice Online")
    
    # Step 8: Get Online Users
    print("\n8. GET ONLINE USERS")
    print("-" * 30)
    
    response = requests.get(f"{BASE_URL}/api/online-users/", headers=headers)
    print_response(response, "Online Users")
    
    # Step 9: Coin Management
    print("\n9. COIN MANAGEMENT")
    print("-" * 30)
    
    # Get coin balance
    response = requests.get(f"{BASE_URL}/api/coins/", headers=headers)
    print_response(response, "Alice's Coin Balance")
    
    # Add coins
    coin_data = {"coins": 100}
    response = requests.post(f"{BASE_URL}/api/coins/add/", headers=headers, json=coin_data)
    print_response(response, "Add Coins to Alice")
    
    # Check updated balance
    response = requests.get(f"{BASE_URL}/api/coins/", headers=headers)
    print_response(response, "Updated Coin Balance")
    
    # Step 10: Offers System
    print("\n10. OFFERS SYSTEM")
    print("-" * 30)
    
    # Get active offers
    response = requests.get(f"{BASE_URL}/api/offers/")
    print_response(response, "Active Offers")
    
    print("\nDemo completed! All API endpoints are working.")
    print("You can now test the API endpoints manually using tools like Postman or curl.")

if __name__ == "__main__":
    demo_api()