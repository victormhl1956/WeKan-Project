#!/usr/bin/env python3
"""
Test script for Wekan API
"""

import requests
import json
import sys

# Configuration
WEKAN_URL = "http://localhost:8088"
USERNAME = "victormhl"
PASSWORD = "Nereida6591"

def authenticate():
    """Authenticate with Wekan and get a token"""
    login_url = f"{WEKAN_URL}/users/login"
    
    try:
        response = requests.post(
            login_url,
            data=f"username={USERNAME}&password={PASSWORD}",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print(f"Authentication failed: {response.status_code} - {response.text}")
            return None, None
        
        data = response.json()
        token = data.get('token')
        user_id = data.get('id')
        
        print(f"Authentication successful. Token: {token[:10]}... User ID: {user_id}")
        return token, user_id
    
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        return None, None

def get_boards(token):
    """Get all boards"""
    boards_url = f"{WEKAN_URL}/api/boards"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(boards_url, headers=headers)
        
        print(f"GET /api/boards Status: {response.status_code}")
        
        if response.status_code == 200:
            boards = response.json()
            print(f"Found {len(boards)} boards:")
            for board in boards:
                print(f"  - {board.get('title')} (ID: {board.get('_id')})")
            return boards
        else:
            print(f"Failed to get boards: {response.text}")
            return None
    
    except Exception as e:
        print(f"Error getting boards: {str(e)}")
        return None

def create_board_json(token, user_id, title="Test Board"):
    """Try to create a board using JSON data"""
    boards_url = f"{WEKAN_URL}/api/boards"
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "title": title,
            "owner": user_id,
            "permission": "private",
            "color": "belize"
        }
        
        print(f"Attempting to create board with JSON data: {json.dumps(data)}")
        response = requests.post(boards_url, headers=headers, json=data)
        
        print(f"POST /api/boards (JSON) Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code == 200 or response.status_code == 201
    
    except Exception as e:
        print(f"Error creating board with JSON: {str(e)}")
        return False

def create_board_form(token, user_id, title="Test Board"):
    """Try to create a board using form data"""
    boards_url = f"{WEKAN_URL}/api/boards"
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = f"title={title}&owner={user_id}&permission=private&color=belize"
        
        print(f"Attempting to create board with form data: {data}")
        response = requests.post(boards_url, headers=headers, data=data)
        
        print(f"POST /api/boards (form) Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code == 200 or response.status_code == 201
    
    except Exception as e:
        print(f"Error creating board with form data: {str(e)}")
        return False

def main():
    """Main function"""
    token, user_id = authenticate()
    
    if not token or not user_id:
        print("Authentication failed. Exiting.")
        return 1
    
    # Get existing boards
    boards = get_boards(token)
    
    # Try to create a board with JSON data
    print("\n=== Testing board creation with JSON data ===")
    json_success = create_board_json(token, user_id, "Test Board JSON")
    
    # Try to create a board with form data
    print("\n=== Testing board creation with form data ===")
    form_success = create_board_form(token, user_id, "Test Board Form")
    
    print("\n=== Summary ===")
    print(f"JSON creation: {'Success' if json_success else 'Failed'}")
    print(f"Form creation: {'Success' if form_success else 'Failed'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
