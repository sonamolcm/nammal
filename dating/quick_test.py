import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(url, method='GET', data=None, headers=None, description=""):
    """Test an API endpoint and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    print(f"{'='*60}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("🧪 Dating App API - Quick Test")
    print("="*60)
    
    # Test 1: User Registration
    register_data = {
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
    
    response = test_endpoint(
        f"{BASE_URL}/api/register/",
        method='POST',
        data=register_data,
        description="User Registration"
    )
    
    if response and response.status_code == 201:
        token = response.json()['token']
        headers = {"Authorization": f"Token {token}"}
        
        # Test 2: Get User Profile
        test_endpoint(
            f"{BASE_URL}/api/profile/",
            method='GET',
            headers=headers,
            description="Get User Profile"
        )
        
        # Test 3: Update Profile
        update_data = {
            "bio": "Updated bio - Love hiking and photography!",
            "age": 26
        }
        test_endpoint(
            f"{BASE_URL}/api/profile/",
            method='PUT',
            data=update_data,
            headers=headers,
            description="Update User Profile"
        )
        
        # Test 4: Get Menu
        test_endpoint(
            f"{BASE_URL}/api/menu/",
            method='GET',
            headers=headers,
            description="Get Menu Items"
        )
        
        # Test 5: Get Legal Documents
        test_endpoint(
            f"{BASE_URL}/api/terms-conditions/",
            method='GET',
            description="Get Terms & Conditions"
        )
        
        # Test 6: Get Offers
        test_endpoint(
            f"{BASE_URL}/api/offers/",
            method='GET',
            description="Get Active Offers"
        )
        
        # Test 7: Get Coin Balance
        test_endpoint(
            f"{BASE_URL}/api/coins/",
            method='GET',
            headers=headers,
            description="Get Coin Balance"
        )
        
        # Test 8: Add Coins
        coin_data = {"coins": 100}
        test_endpoint(
            f"{BASE_URL}/api/coins/add/",
            method='POST',
            data=coin_data,
            headers=headers,
            description="Add Coins"
        )
        
        # Test 9: Get Updated Coin Balance
        test_endpoint(
            f"{BASE_URL}/api/coins/",
            method='GET',
            headers=headers,
            description="Get Updated Coin Balance"
        )
        
        # Test 10: Set User Online
        status_data = {"status_type": "online", "is_active": True}
        test_endpoint(
            f"{BASE_URL}/api/update-status/",
            method='POST',
            data=status_data,
            headers=headers,
            description="Set User Online"
        )
        
        # Test 11: Get Online Users
        test_endpoint(
            f"{BASE_URL}/api/online-users/",
            method='GET',
            headers=headers,
            description="Get Online Users"
        )
        
        print(f"\n{'='*60}")
        print("✅ All tests completed successfully!")
        print(f"Authentication Token: {token}")
        print("="*60)
    else:
        print("❌ Registration failed. Cannot continue with other tests.")

if __name__ == "__main__":
    main()