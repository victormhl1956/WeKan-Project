#!/usr/bin/env python3
"""
Test script for Wekan integration
"""

import os
import sys
import json
import requests

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

def create_board(token, user_id, title="Test Board"):
    """Create a board using JSON data"""
    boards_url = f"{WEKAN_URL}/api/boards"
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Generate a slug from the title
        slug = title.lower().replace(" ", "-").replace("(", "").replace(")", "")
        
        data = {
            "title": title,
            "owner": user_id,
            "permission": "private",
            "color": "belize",
            "slug": slug
        }
        
        print(f"Creating board: {title}")
        print(f"Using token: {token[:10]}...")
        print(f"Using user_id: {user_id}")
        print(f"Using slug: {slug}")
        print(f"Request URL: {boards_url}")
        print(f"Request headers: {headers}")
        print(f"Request data: {data}")
        
        response = requests.post(boards_url, headers=headers, json=data)
        
        print(f"POST /api/boards Status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response text: {response.text}")
        
        if response.status_code in [200, 201]:
            try:
                board_data = response.json()
                board_id = board_data.get('_id')
                print(f"Board created successfully: {board_id}")
                return board_id, slug
            except Exception as e:
                print(f"Error parsing response: {str(e)}")
                return None, None
        else:
            print(f"Failed to create board: {response.text}")
            return None, None
    
    except Exception as e:
        print(f"Error creating board: {str(e)}")
        return None, None

def main():
    """Main function"""
    token, user_id = authenticate()
    
    if not token or not user_id:
        print("Authentication failed. Exiting.")
        return 1
    
    # Create a test board
    board_id, board_slug = create_board(token, user_id)
    
    if not board_id:
        print("Failed to create board. Exiting.")
        return 1
    
    print("\n=== Summary ===")
    print(f"Board ID: {board_id}")
    print(f"Board Slug: {board_slug}")
    print(f"Board URL: {WEKAN_URL}/b/{board_id}/{board_slug}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
