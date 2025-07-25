#!/usr/bin/env python3
"""
WeKan Boards Cleaner - List and Delete Test Boards
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
from datetime import datetime, date
from wekan_board_manager import WekanAuthManager, WekanAPIClient

def list_boards(api_client):
    """List all boards with creation dates"""
    boards = api_client._make_request('GET', '/boards')
    board_list = []
    for board in boards:
        created_at = board.get('createdAt')
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
        else:
            created_date = None
        board_list.append({
            'id': board['_id'],
            'title': board['title'],
            'created_at': created_date
        })
    return board_list

def delete_board(api_client, board_id):
    """Delete a board by ID"""
    return api_client._make_request('DELETE', f'/boards/{board_id}')

if __name__ == "__main__":
    config = json.load(open('wekan_config.json'))
    wekan_url = config['wekan_url']
    username = config['credentials']['username']
    password = config['credentials']['password']

    auth_manager = WekanAuthManager(wekan_url, username, password)
    api_client = WekanAPIClient(wekan_url, auth_manager)

    boards = list_boards(api_client)
    today = date.today()
    test_boards = [b for b in boards if b['created_at'] == today]

    print("Boards created today:")
    for board in test_boards:
        print(f"ID: {board['id']}, Title: {board['title']}, Created: {board['created_at']}")

    # For deletion, uncomment and confirm
    for board in test_boards:
        delete_board(api_client, board['id'])
        print(f"Deleted board: {board['title']}")
