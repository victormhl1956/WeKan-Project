#!/usr/bin/env python3
"""
Wekan Board Manager
==================

A script for automated creation of Wekan boards with customizable templates.
This tool simplifies the process of creating boards, lists, and cards in Wekan
through its REST API.

Author: AI Coder - NiceDev Project
Date: 2025-07-15
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
import subprocess
import shlex
from wekan_api_external import create_wekan_board_external

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Default templates
DEFAULT_TEMPLATES = {
    "kanban_basic": {
        "title": "Basic Kanban Board",
        "lists": [
            {"title": "Backlog"},
            {"title": "To Do"},
            {"title": "In Progress"},
            {"title": "Done"}
        ],
        "cards": {
            "Backlog": [
                {"title": "Example Card 1", "description": "This is an example card"}
            ]
        }
    },
    "scrum": {
        "title": "Scrum Board",
        "lists": [
            {"title": "Product Backlog"},
            {"title": "Sprint Backlog"},
            {"title": "In Progress"},
            {"title": "Review"},
            {"title": "Done"}
        ],
        "cards": {}
    },
    "devops": {
        "title": "DevOps Pipeline",
        "lists": [
            {"title": "Backlog"},
            {"title": "Planning"},
            {"title": "Development"},
            {"title": "Testing"},
            {"title": "Deployment"},
            {"title": "Monitoring"}
        ],
        "cards": {}
    },
    "nicedev_agent": {
        "title": "NiceDev Agent Tasks",
        "lists": [
            {"title": "Backlog"},
            {"title": "In Progress"},
            {"title": "Blocked"},
            {"title": "Done"}
        ],
        "cards": {
            "Backlog": [
                {"title": "Initial Setup", "description": "Configure agent environment"},
                {"title": "Integration Testing", "description": "Test agent integrations"}
            ]
        }
    }
}


class WekanAuthManager:
    """
    Manages authentication with Wekan API, including token handling and expiration.
    """
    
    def __init__(self, wekan_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the authentication manager.
        
        Args:
            wekan_url: Base URL of the Wekan instance
            username: Wekan username
            password: Wekan password
        """
        self.wekan_url = wekan_url.rstrip('/')
        self.username = username
        self.password = password
        
        if not self.username or not self.password:
            raise ValueError("Wekan credentials not provided.")
        
        self.token = None
        self.user_id = None
        self.token_expires = None
        self.operations_log = []
        
        # Authenticate immediately
        self.authenticate()
    
    def authenticate(self) -> Tuple[str, str, datetime]:
        """
        Authenticate with Wekan API and get a token.
        
        Returns:
            Tuple of (token, user_id, expiration_datetime)
        """
        login_url = f"{self.wekan_url}/users/login"
        
        try:
            start_time = time.time()
            self.operations_log.append(f"Authenticating with Wekan at {login_url}")
            
            response = requests.post(
                login_url,
                data=f"username={self.username}&password={self.password}",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_msg = f"Authentication failed: {response.status_code} - {response.text}"
                self.operations_log.append(f"ERROR: {error_msg}")
                raise Exception(error_msg)
            
            data = response.json()
            self.token = data.get('token')
            self.user_id = data.get('id')
            
            # Parse expiration time
            expires_str = data.get('tokenExpires')
            if expires_str:
                self.token_expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            else:
                # Default to 90 days if not provided
                self.token_expires = datetime.now() + timedelta(days=90)
            
            elapsed = time.time() - start_time
            self.operations_log.append(f"Authentication successful. Token obtained in {elapsed:.2f}s")
            
            return self.token, self.user_id, self.token_expires
            
        except requests.RequestException as e:
            error_msg = f"Error connecting to Wekan: {str(e)}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise Exception(error_msg)
    
    def get_valid_token(self) -> str:
        """
        Get a valid token, re-authenticating if the current token is expired.
        
        Returns:
            Valid authentication token
        """
        # Check if token is expired or about to expire (within 5 minutes)
        now_aware = datetime.now(timezone.utc)
        if not self.token or not self.token_expires or \
           now_aware + timedelta(minutes=5) >= self.token_expires:
            self.operations_log.append("Token expired or about to expire. Re-authenticating...")
            self.authenticate()
        
        return self.token
    
    def get_operations_log(self) -> List[str]:
        """
        Get the operations log.
        
        Returns:
            List of operation log entries
        """
        return self.operations_log


class WekanAPIClient:
    """
    Enhanced client for interacting with Wekan API, including retry logic.
    """
    
    def __init__(self, wekan_url: str, auth_manager: WekanAuthManager):
        """
        Initialize the API client.
        
        Args:
            wekan_url: Base URL of the Wekan instance
            auth_manager: Authentication manager instance
        """
        self.wekan_url = wekan_url.rstrip('/')
        self.api_url = f"{self.wekan_url}/api/"
        self.auth_manager = auth_manager
        self.operations_log = []
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers with valid authentication token.
        
        Returns:
            Dictionary of headers
        """
        token = self.auth_manager.get_valid_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     form_data: Optional[Dict] = None, retry_count: int = 3, 
                     backoff_factor: float = 0.5) -> Dict:
        """
        Make a request to the Wekan API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: JSON data for the request
            form_data: Form data for the request
            retry_count: Number of retries on failure
            backoff_factor: Backoff factor for retries
            
        Returns:
            Response data as dictionary
        """
        url = urljoin(self.api_url, endpoint.lstrip('/'))
        headers = self._get_headers()
        
        if form_data:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            headers['Content-Type'] = 'application/json'
        
        self.operations_log.append(f"Making {method} request to {url}")
        
        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    wait_time = backoff_factor * (2 ** (attempt - 1))
                    self.operations_log.append(f"Retry attempt {attempt} after {wait_time:.2f}s")
                    time.sleep(wait_time)
                
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers)
                elif method.upper() == 'POST':
                    if form_data:
                        # Convert dict to form data string
                        form_data_str = '&'.join([f"{k}={v}" for k, v in form_data.items()])
                        response = requests.post(url, headers=headers, data=form_data_str)
                    else:
                        response = requests.post(url, headers=headers, json=data)
                elif method.upper() == 'PUT':
                    response = requests.put(url, headers=headers, json=data)
                elif method.upper() == 'DELETE':
                    response = requests.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for authentication errors
                if response.status_code == 401:
                    self.operations_log.append("Authentication error. Refreshing token...")
                    self.auth_manager.authenticate()
                    headers = self._get_headers()
                    continue
                
                # Check for success
                if response.status_code in [200, 201]:
                    try:
                        return response.json()
                    except ValueError:
                        return {"status": "success", "statusCode": response.status_code}
                
                # Handle other errors
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                self.operations_log.append(f"ERROR: {error_msg}")
                
                # If we've exhausted retries, raise the exception
                if attempt == retry_count:
                    raise Exception(error_msg)
                
            except requests.RequestException as e:
                error_msg = f"Request error: {str(e)}"
                self.operations_log.append(f"ERROR: {error_msg}")
                
                # If we've exhausted retries, raise the exception
                if attempt == retry_count:
                    raise Exception(error_msg)
    
    def create_board(self, title: str, owner: Optional[str] = None, color: str = "belize",
                    permission: str = "private") -> Dict:
        """
        Create a new board.
        """
        self.operations_log.append(f"Creating board: {title}")
        
        # Generate a slug from the title
        slug = title.lower().replace(" ", "-").replace("(", "").replace(")", "")
        
        data = {
            "title": title,
            "owner": owner or self.auth_manager.user_id,
            "permission": permission,
            "color": color,
            "slug": slug
        }
        
        # Direct implementation without using _make_request
        boards_url = f"{self.wekan_url}/api/boards/"
        headers = {
            "Authorization": f"Bearer {self.auth_manager.get_valid_token()}",
            "Content-Type": "application/json"
        }
        
        self.operations_log.append(f"Request URL: {boards_url}")
        self.operations_log.append(f"Request data: {data}")
        
        try:
            response = requests.post(boards_url, headers=headers, json=data)
            
            self.operations_log.append(f"POST /api/boards Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                try:
                    board_data = response.json()
                    board_id = board_data.get('_id')
                    self.operations_log.append(f"Board created successfully: {board_id}")
                    return board_data
                except Exception as e:
                    error_msg = f"Error parsing response: {str(e)}"
                    self.operations_log.append(f"ERROR: {error_msg}")
                    raise Exception(error_msg)
            else:
                error_msg = f"Failed to create board: {response.status_code} - {response.text}"
                self.operations_log.append(f"ERROR: {error_msg}")
                raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Error creating board: {str(e)}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise Exception(error_msg)
    
    def create_list(self, board_id: str, title: str) -> Dict:
        """
        Create a new list in a board.
        
        Args:
            board_id: Board ID
            title: List title
            
        Returns:
            List data including ID
        """
        data = {"title": title}
        
        self.operations_log.append(f"Creating list '{title}' in board {board_id}")
        return self._make_request('POST', f'/boards/{board_id}/lists', data=data)
    
    def create_card(self, board_id: str, list_id: str, title: str,
                   description: Optional[str] = None,
                   author_id: Optional[str] = None,
                   members: Optional[List[str]] = None,
                   label_ids: Optional[List[str]] = None) -> Dict:
        """
        Create a new card in a list.
        
        Args:
            board_id: Board ID
            list_id: List ID
            title: Card title
            description: Card description
            author_id: Author ID (defaults to authenticated user)
            members: List of member IDs
            label_ids: List of label IDs
            
        Returns:
            Card data including ID
        """
        author_id = author_id or self.auth_manager.user_id
        
        # Get the default swimlane ID
        swimlane_id = self.get_default_swimlane(board_id)
        if not swimlane_id:
            raise Exception("Failed to get swimlane ID. Cannot create card.")

        data = {
            "title": title,
            "description": description or "",
            "authorId": author_id,
            "swimlaneId": swimlane_id,
            "members": members or [],
            "labelIds": label_ids or []
        }
        
        self.operations_log.append(f"Creating card '{title}' in list {list_id}")
        return self._make_request('POST', f'/boards/{board_id}/lists/{list_id}/cards', data=data)
    
    def get_lists(self, board_id: str) -> List[Dict]:
        """
        Get all lists for a board.
        
        Args:
            board_id: Board ID
            
        Returns:
            List of list dictionaries
        """
        self.operations_log.append(f"Getting lists for board {board_id}")
        try:
            result = self._make_request('GET', f'/boards/{board_id}/lists')
            self.operations_log.append(f"DEBUG: get_lists result type: {type(result)}")
            self.operations_log.append(f"DEBUG: get_lists result: {result}")
            return result
        except Exception as e:
            self.operations_log.append(f"ERROR in get_lists: {str(e)}")
            return []
    
    def get_list_by_name(self, board_id: str, list_name: str) -> Optional[Dict]:
        """
        Get a list by name.
        
        Args:
            board_id: Board ID
            list_name: List name
            
        Returns:
            List dictionary or None if not found
        """
        self.operations_log.append(f"Looking for list '{list_name}' in board {board_id}")
        try:
            lists = self.get_lists(board_id)
            
            # Check if lists is a list or dict
            if isinstance(lists, list):
                for list_item in lists:
                    if isinstance(list_item, dict) and list_item.get('title') == list_name:
                        self.operations_log.append(f"Found list '{list_name}' with ID {list_item.get('_id')}")
                        return list_item
            else:
                self.operations_log.append(f"WARNING: get_lists returned non-list: {type(lists)}")
            
            self.operations_log.append(f"WARNING: List '{list_name}' not found in board {board_id}")
            return None
        except Exception as e:
            self.operations_log.append(f"ERROR in get_list_by_name: {str(e)}")
            return None

    def get_swimlanes(self, board_id: str) -> List[Dict]:
        """
        Get all swimlanes for a board.
        
        Args:
            board_id: Board ID
            
        Returns:
            List of swimlane dictionaries
        """
        self.operations_log.append(f"Getting swimlanes for board {board_id}")
        return self._make_request('GET', f'/boards/{board_id}/swimlanes')

    def move_card(self, board_id: str, card_id: str, new_list_id: str) -> Dict:
        """
        Move a card to a new list.
        
        Args:
            board_id: Board ID
            card_id: Card ID to move
            new_list_id: ID of the destination list
            
        Returns:
            Result of the update operation
        """
        self.operations_log.append(f"Moving card {card_id} to list {new_list_id} in board {board_id}")
        # Wekan API uses the authorId to move the card, which is unusual but required.
        # The user moving the card becomes the new author.
        data = {
            "listId": new_list_id,
            "authorId": self.auth_manager.user_id 
        }
        return self._make_request('PUT', f'/boards/{board_id}/lists/{new_list_id}/cards/{card_id}', data=data)

    def add_comment_to_card(self, board_id: str, card_id: str, comment_text: str) -> Dict:
        """
        Add a comment to a card.
        
        Args:
            board_id: Board ID
            card_id: Card ID to comment on
            comment_text: The text of the comment
            
        Returns:
            The created comment data
        """
        self.operations_log.append(f"Adding comment to card {card_id} in board {board_id}")
        data = {
            "comment": comment_text,
            "authorId": self.auth_manager.user_id
        }
        return self._make_request('POST', f'/boards/{board_id}/cards/{card_id}/comments', data=data)

    def get_default_swimlane(self, board_id: str) -> Optional[str]:
        """
        Get the default swimlane ID for a board.
        
        Args:
            board_id: Board ID
            
        Returns:
            Default swimlane ID or None
        """
        swimlanes = self.get_swimlanes(board_id)
        if swimlanes and len(swimlanes) > 0:
            return swimlanes[0].get('_id')
        return None
    
    def get_operations_log(self) -> List[str]:
        """
        Get the operations log.
        
        Returns:
            List of operation log entries
        """
        return self.operations_log


class BoardTemplateManager:
    """
    Manages board templates for different types of projects.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Directory containing template JSON files
        """
        self.templates = DEFAULT_TEMPLATES.copy()
        self.operations_log = []
        
        # Load custom templates if directory provided
        if templates_dir:
            self._load_custom_templates(templates_dir)
    
    def _load_custom_templates(self, templates_dir: str) -> None:
        """
        Load custom templates from a directory.
        
        Args:
            templates_dir: Directory containing template JSON files
        """
        if not os.path.isdir(templates_dir):
            self.operations_log.append(f"WARNING: Templates directory not found: {templates_dir}")
            return
        
        self.operations_log.append(f"Loading custom templates from {templates_dir}")
        
        for filename in os.listdir(templates_dir):
            if filename.endswith('.json'):
                template_name = os.path.splitext(filename)[0]
                filepath = os.path.join(templates_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        template = json.load(f)
                    
                    if self.validate_template(template):
                        self.templates[template_name] = template
                        self.operations_log.append(f"Loaded template: {template_name}")
                    
                except Exception as e:
                    self.operations_log.append(f"ERROR: Failed to load template {filepath}: {str(e)}")
    
    def get_template(self, template_name: str) -> Dict:
        """
        Get a template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template data
        """
        if template_name not in self.templates:
            available = ", ".join(self.templates.keys())
            error_msg = f"Template '{template_name}' not found. Available templates: {available}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        self.operations_log.append(f"Using template: {template_name}")
        return self.templates[template_name]
    
    def list_templates(self) -> List[str]:
        """
        List available templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
    
    def validate_template(self, template: Dict) -> bool:
        """
        Validate a template structure.
        
        Args:
            template: Template data
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if 'title' not in template:
            self.operations_log.append("ERROR: Template missing 'title' field")
            return False
        
        if 'lists' not in template or not isinstance(template['lists'], list):
            self.operations_log.append("ERROR: Template missing 'lists' field or 'lists' is not an array")
            return False
        
        # Check that each list has a title
        for i, list_item in enumerate(template['lists']):
            if 'title' not in list_item:
                self.operations_log.append(f"ERROR: List at index {i} missing 'title' field")
                return False
        
        # Check cards structure if present
        if 'cards' in template:
            if not isinstance(template['cards'], dict):
                self.operations_log.append("ERROR: Template 'cards' field must be an object")
                return False
            
            # Check that each card list exists and has valid cards
            for list_title, cards in template['cards'].items():
                list_exists = any(list_item['title'] == list_title for list_item in template['lists'])
                if not list_exists:
                    self.operations_log.append(f"ERROR: Cards specified for non-existent list '{list_title}'")
                    return False
                
                if not isinstance(cards, list):
                    self.operations_log.append(f"ERROR: Cards for list '{list_title}' must be an array")
                    return False
                
                for i, card in enumerate(cards):
                    if 'title' not in card:
                        self.operations_log.append(f"ERROR: Card at index {i} in list '{list_title}' missing 'title' field")
                        return False
        
        return True
    
    def get_operations_log(self) -> List[str]:
        """
        Get the operations log.
        
        Returns:
            List of operation log entries
        """
        return self.operations_log


class BoardCreator:
    """
    Main class for creating boards, lists, and cards in Wekan.
    """
    
    def __init__(self, api_client: WekanAPIClient, template_manager: BoardTemplateManager):
        """
        Initialize the board creator.
        
        Args:
            api_client: Wekan API client
            template_manager: Board template manager
        """
        self.api_client = api_client
        self.template_manager = template_manager
        self.operations_log = []
    
    def create_board_from_template(self, template_name: str, board_title: Optional[str] = None, 
                                  **kwargs) -> Dict:
        """
        Create a board based on a template.
        
        Args:
            template_name: Name of the template to use
            board_title: Override the template title (optional)
            **kwargs: Additional parameters for board creation
            
        Returns:
            Dictionary with board, lists, and cards data
        """
        start_time = time.time()
        self.operations_log.append(f"Creating board from template: {template_name}")
        
        # Get the template
        template = self.template_manager.get_template(template_name)
        
        # Use provided title or template title
        title = board_title or template['title']
        
        # Create the board
        board_data = self.api_client.create_board(title, **kwargs)
        board_id = board_data.get('_id')
        
        if not board_id:
            error_msg = f"Failed to create board: {board_data}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        
        self.operations_log.append(f"Board created successfully: {board_id}")
        
        # Create lists
        lists_data = []
        for list_item in template['lists']:
            list_data = self.api_client.create_list(board_id, list_item['title'])
            list_id = list_data.get('_id')
            
            if not list_id:
                self.operations_log.append(f"WARNING: Failed to create list '{list_item['title']}': {list_data}")
                continue
            
            lists_data.append({
                'name': list_item['title'],
                'id': list_id
            })
            
            self.operations_log.append(f"List created: {list_item['title']} ({list_id})")
        
        # Create cards
        cards_data = []
        if 'cards' in template:
            for list_title, cards in template['cards'].items():
                # Find the list ID
                list_id = next((item['id'] for item in lists_data if item['name'] == list_title), None)
                
                if not list_id:
                    self.operations_log.append(f"WARNING: Cannot create cards for list '{list_title}': List not found")
                    continue
                
                for card in cards:
                    card_data = self.api_client.create_card(
                        board_id, 
                        list_id, 
                        card['title'], 
                        description=card.get('description')
                    )
                    
                    card_id = card_data.get('_id')
                    
                    if not card_id:
                        self.operations_log.append(f"WARNING: Failed to create card '{card['title']}': {card_data}")
                        continue
                    
                    cards_data.append({
                        'title': card['title'],
                        'id': card_id,
                        'list_id': list_id
                    })
                    
                    self.operations_log.append(f"Card created: {card['title']} ({card_id})")
        
        elapsed = time.time() - start_time
        self.operations_log.append(f"Board creation completed in {elapsed:.2f}s")
        
        # Construct the board URL
        wekan_url = self.api_client.wekan_url
        board_url = f"{wekan_url}/b/{board_id}"
        
        return {
            'success': True,
            'board_id': board_id,
            'board_url': board_url,
            'lists': lists_data,
            'cards': cards_data,
            'execution_time': f"{elapsed:.2f}s"
        }
    
    def create_custom_board(self, board_config: Dict) -> Dict:
        """
        Create a board based on custom configuration.
        
        Args:
            board_config: Custom board configuration
            
        Returns:
            Dictionary with board, lists, and cards data
        """
        # Validate the configuration
        if not self.template_manager.validate_template(board_config):
            error_msg = "Invalid board configuration"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Create the board using the configuration as a template
        start_time = time.time()
        self.operations_log.append("Creating board from custom configuration")
        
        # Create the board
        board_data = self.api_client.create_board(board_config['title'])
        board_id = board_data.get('_id')
        
        if not board_id:
            error_msg = f"Failed to create board: {board_data}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        
        self.operations_log.append(f"Board created successfully: {board_id}")
        
        # Create lists
        lists_data = []
        for list_item in board_config['lists']:
            list_data = self.api_client.create_list(board_id, list_item['title'])
            list_id = list_data.get('_id')
            
            if not list_id:
                self.operations_log.append(f"WARNING: Failed to create list '{list_item['title']}': {list_data}")
                continue
            
            lists_data.append({
                'name': list_item['title'],
                'id': list_id
            })
            
            self.operations_log.append(f"List created: {list_item['title']} ({list_id})")
        
        # Create cards
        cards_data = []
        if 'cards' in board_config:
            for list_title, cards in board_config['cards'].items():
                # Find the list ID
                list_id = next((item['id'] for item in lists_data if item['name'] == list_title), None)
                
                if not list_id:
                    self.operations_log.append(f"WARNING: Cannot create cards for list '{list_title}': List not found")
                    continue
                
                for card in cards:
                    card_data = self.api_client.create_card(
                        board_id, 
                        list_id, 
                        card['title'], 
                        description=card.get('description')
                    )
                    
                    card_id = card_data.get('_id')
                    
                    if not card_id:
                        self.operations_log.append(f"WARNING: Failed to create card '{card['title']}': {card_data}")
                        continue
                    
                    cards_data.append({
                        'title': card['title'],
                        'id': card_id,
                        'list_id': list_id
                    })
                    
                    self.operations_log.append(f"Card created: {card['title']} ({card_id})")
        
        elapsed = time.time() - start_time
        self.operations_log.append(f"Board creation completed in {elapsed:.2f}s")
        
        # Construct the board URL
        wekan_url = self.api_client.wekan_url
        board_url = f"{wekan_url}/b/{board_id}"
        
        return {
            'success': True,
            'board_id': board_id,
            'board_url': board_url,
            'lists': lists_data,
            'cards': cards_data,
            'execution_time': f"{elapsed:.2f}s"
        }
    
    def add_card_to_board(self, board_id: str, list_name: str, card_title: str, 
                         card_description: Optional[str] = None) -> Dict:
        """
        Add a card to an existing board in the specified list.
        
        Args:
            board_id: Board ID
            list_name: List name
            card_title: Card title
            card_description: Card description (optional)
            
        Returns:
            Dictionary with card data
        """
        start_time = time.time()
        self.operations_log.append(f"Adding card '{card_title}' to list '{list_name}' in board {board_id}")
        
        # Get the list ID by name
        list_data = self.api_client.get_list_by_name(board_id, list_name)
        
        if not list_data:
            error_msg = f"List '{list_name}' not found in board {board_id}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        list_id = list_data['_id']
        
        # Create the card
        card_data = self.api_client.create_card(
            board_id,
            list_id,
            card_title,
            description=card_description
        )
        
        card_id = card_data.get('_id')
        
        if not card_id:
            error_msg = f"Failed to create card: {card_data}"
            self.operations_log.append(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        
        self.operations_log.append(f"Card created successfully: {card_id}")
        
        elapsed = time.time() - start_time
        self.operations_log.append(f"Card creation completed in {elapsed:.2f}s")
        
        # Construct the card URL
        wekan_url = self.api_client.wekan_url
        card_url = f"{wekan_url}/b/{board_id}/cards/{card_id}"
        
        return {
            'success': True,
            'board_id': board_id,
            'card_id': card_id,
            'card_url': card_url,
            'list_name': list_name,
            'list_id': list_id,
            'title': card_title,
            'description': card_description,
            'execution_time': f"{elapsed:.2f}s"
        }
    
    def get_operations_log(self) -> List[str]:
        """
        Get the operations log.
        
        Returns:
            List of operation log entries
        """
        return self.operations_log


class OutputFormatter:
    """
    Formats the output as structured JSON.
    """
    
    def __init__(self):
        """
        Initialize the output formatter.
        """
        self.start_time = time.time()
    
    def format_output(self, success: bool, board_id: Optional[str] = None, 
                     board_url: Optional[str] = None, lists: Optional[List] = None, 
                     cards: Optional[List] = None, operations_log: Optional[List] = None) -> Dict:
        """
        Format the output as structured JSON.
        
        Args:
            success: Whether the operation was successful
            board_id: Board ID
            board_url: Board URL
            lists: List of lists data
            cards: List of cards data
            operations_log: List of operation log entries
            
        Returns:
            Structured output dictionary
        """
        elapsed = time.time() - self.start_time
        
        output = {
            "success": success,
            "execution_time": f"{elapsed:.2f}s",
            "operations_log": operations_log or []
        }
        
        if success:
            output["board_id"] = board_id
            output["board_url"] = board_url
            output["lists"] = lists or []
            output["cards"] = cards or []
        
        return output


def load_config(config_path: str = 'wekan_config.json') -> Dict:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = os.path.join(os.path.dirname(__file__), config_path)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def validate_prerequisites(config: Dict) -> bool:
    """
    Validate prerequisites for running the script.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if prerequisites are met, False otherwise
    """
    # Check for required credentials
    if 'credentials' not in config or 'username' not in config['credentials'] or 'password' not in config['credentials']:
        logger.error("Wekan credentials not found in configuration file.")
        return False
    
    # Check connectivity to Wekan
    wekan_url = config.get('wekan_url', 'http://localhost:8088')
    try:
        response = requests.get(wekan_url)
        if response.status_code != 200:
            logger.error(f"Cannot connect to Wekan at {wekan_url}: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Cannot connect to Wekan at {wekan_url}: {str(e)}")
        return False
    
    return True


def main():
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(description='Create Wekan boards automatically')
    parser.add_argument('--template', help='Template to use (kanban_basic, scrum, devops, nicedev_agent)')
    parser.add_argument('--title', help='Board title')
    parser.add_argument('--config', help='Path to custom configuration file')
    parser.add_argument('--output', help='Path to output file (default: stdout)')
    parser.add_argument('--url', help='Wekan URL (default: http://localhost:8088)')
    parser.add_argument('--username', help='Wekan username (default: from WEKAN_USERNAME env var)')
    parser.add_argument('--password', help='Wekan password (default: from WEKAN_PASSWORD env var)')
    parser.add_argument('--templates-dir', help='Directory containing template JSON files')

    parser.add_argument('--list-templates', action='store_true', help='List available templates and exit')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose (debug) output')

    parser.add_argument('--dry-run', action='store_true', help='Show planned operations without executing API calls and exit')
    parser.add_argument('--health-check', action='store_true', help='Check Wekan health and exit')
    
    # Arguments for adding a card to an existing board
    parser.add_argument('--add-card', action='store_true', help='Add a card to an existing board')
    parser.add_argument('--board-id', help='Board ID (required when adding a card)')
    parser.add_argument('--list-name', help='List name (required when adding a card)')
    parser.add_argument('--card-title', help='Card title (required when adding a card)')
    parser.add_argument('--card-description', help='Card description (optional when adding a card)')

    # Arguments for moving a card
    parser.add_argument('--move-card', action='store_true', help='Move a card to a new list')
    parser.add_argument('--card-id', help='Card ID to move or comment on')
    parser.add_argument('--new-list-name', help='Name of the destination list for moving a card')

    # Arguments for adding a comment
    parser.add_argument('--add-comment', action='store_true', help='Add a comment to a card')
    parser.add_argument('--comment-text', help='The text for the comment')
    

    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Set up the output formatter
    output_formatter = OutputFormatter()
    
    try:
        # Load configuration
        config = load_config()
        
        # Get Wekan URL from args or config
        wekan_url = args.url or config.get('wekan_url', 'http://localhost:8088')
        
        # Set up the template manager
        templates_dir = args.templates_dir or os.path.join(os.path.dirname(__file__), 'templates')
        template_manager = BoardTemplateManager(templates_dir)
        

        # List templates and exit if requested
        if args.list_templates:
            templates = template_manager.list_templates()
            print("Available templates:")
            for template in templates:
                print(f"  - {template}")
            return

        # Dry-run mode: show planned operations without executing
        if args.dry_run:
            logger.info("Dry run mode: planning operations without execution")
            if args.template:
                tpl = template_manager.get_template(args.template)
                title = args.title or tpl.get('title')
                logger.info(f"Would create board '{title}' using template '{args.template}'")
                logger.info(f"Lists to create: {[lst['title'] for lst in tpl.get('lists', [])]}")
                logger.info(f"Cards to create per list: {tpl.get('cards', {})}")
            elif args.config:
                try:
                    with open(args.config, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    logger.info(f"Would create custom board '{cfg.get('title')}'")
                    logger.info(f"Lists to create: {[lst['title'] for lst in cfg.get('lists', [])]}")
                    logger.info(f"Cards to create per list: {cfg.get('cards', {})}")
                except Exception as e:
                    logger.error(f"Error reading config for dry run: {e}")
            elif args.add_card:
                logger.info(f"Would add card '{args.card_title}' to list '{args.list_name}' in board '{args.board_id}'")
            else:
                logger.error("Dry run: no action specified")
            return
        
        # Health-check mode: check connectivity and exit
        if args.health_check:
            if validate_prerequisites(config):
                print("Wekan health check passed")
                return 0
            else:
                print("Wekan health check failed")
                return 1

        # Validate prerequisites
        if not validate_prerequisites(config):
            output = output_formatter.format_output(
                success=False,
                operations_log=["ERROR: Prerequisites not met"]
            )
            _output_result(output, args.output)
            return 1
        
        # Set up the authentication manager
        auth_manager = WekanAuthManager(
            wekan_url=wekan_url,
            username=args.username or config['credentials']['username'],
            password=args.password or config['credentials']['password']
        )
        
        # Set up the API client
        api_client = WekanAPIClient(wekan_url, auth_manager)
        
        # Set up the board creator
        board_creator = BoardCreator(api_client, template_manager)
        
        # Collect all operation logs
        all_logs = []
        all_logs.extend(auth_manager.get_operations_log())
        all_logs.extend(api_client.get_operations_log())
        all_logs.extend(template_manager.get_operations_log())
        all_logs.extend(board_creator.get_operations_log())
        
        # Create board from template, custom configuration, or add card to existing board
        if args.move_card:
            if not all([args.board_id, args.card_id, args.new_list_name]):
                logger.error("Moving a card requires --board-id, --card-id, and --new-list-name")
                output = output_formatter.format_output(success=False, operations_log=all_logs + ["ERROR: Missing arguments for moving card."])
            else:
                try:
                    dest_list = api_client.get_list_by_name(args.board_id, args.new_list_name)
                    if not dest_list:
                        raise ValueError(f"Destination list '{args.new_list_name}' not found.")
                    result = api_client.move_card(args.board_id, args.card_id, dest_list['_id'])
                    all_logs.extend(api_client.get_operations_log())
                    output = output_formatter.format_output(success=True, operations_log=all_logs)
                except Exception as e:
                    logger.error(f"Error moving card: {str(e)}")
                    output = output_formatter.format_output(success=False, operations_log=all_logs + [f"ERROR: {str(e)}"])
        
        elif args.add_comment:
            if not all([args.board_id, args.card_id, args.comment_text]):
                logger.error("Adding a comment requires --board-id, --card-id, and --comment-text")
                output = output_formatter.format_output(success=False, operations_log=all_logs + ["ERROR: Missing arguments for adding comment."])
            else:
                try:
                    result = api_client.add_comment_to_card(args.board_id, args.card_id, args.comment_text)
                    all_logs.extend(api_client.get_operations_log())
                    output = output_formatter.format_output(success=True, operations_log=all_logs)
                except Exception as e:
                    logger.error(f"Error adding comment: {str(e)}")
                    output = output_formatter.format_output(success=False, operations_log=all_logs + [f"ERROR: {str(e)}"])

        elif args.add_card:
            # Add card to existing board
            if not args.board_id:
                logger.error("Board ID is required when adding a card")
                output = output_formatter.format_output(
                    success=False,
                    operations_log=all_logs + ["ERROR: Board ID is required when adding a card. Use --board-id."]
                )
            elif not args.list_name:
                logger.error("List name is required when adding a card")
                output = output_formatter.format_output(
                    success=False,
                    operations_log=all_logs + ["ERROR: List name is required when adding a card. Use --list-name."]
                )
            elif not args.card_title:
                logger.error("Card title is required when adding a card")
                output = output_formatter.format_output(
                    success=False,
                    operations_log=all_logs + ["ERROR: Card title is required when adding a card. Use --card-title."]
                )
            else:
                try:
                    # Add card to board
                    result = board_creator.add_card_to_board(
                        board_id=args.board_id,
                        list_name=args.list_name,
                        card_title=args.card_title,
                        card_description=args.card_description
                    )
                    
                    # Add logs from card creation
                    all_logs.extend(board_creator.get_operations_log())
                    
                    # Format output
                    output = output_formatter.format_output(
                        success=True,
                        board_id=result['board_id'],
                        board_url=result.get('board_url'),
                        cards=[{
                            'title': result['title'],
                            'id': result['card_id'],
                            'list_id': result['list_id']
                        }],
                        operations_log=all_logs
                    )
                    
                except Exception as e:
                    logger.error(f"Error adding card to board: {str(e)}")
                    output = output_formatter.format_output(
                        success=False,
                        operations_log=all_logs + [f"ERROR: {str(e)}"]
                    )
        
        elif args.config:
            # Load custom configuration
            try:
                with open(args.config, 'r', encoding='utf-8') as f:
                    board_config = json.load(f)
                
                # Create board from custom configuration
                result = board_creator.create_custom_board(board_config)
                
                # Add logs from board creation
                all_logs.extend(board_creator.get_operations_log())
                
                # Format output
                output = output_formatter.format_output(
                    success=True,
                    board_id=result['board_id'],
                    board_url=result['board_url'],
                    lists=result['lists'],
                    cards=result['cards'],
                    operations_log=all_logs
                )
                
            except Exception as e:
                logger.error(f"Error creating board from configuration: {str(e)}")
                output = output_formatter.format_output(
                    success=False,
                    operations_log=all_logs + [f"ERROR: {str(e)}"]
                )
        
        elif args.template:
            # Create board from template
            try:
                result = board_creator.create_board_from_template(
                    template_name=args.template,
                    board_title=args.title
                )
                
                # Add logs from board creation
                all_logs.extend(board_creator.get_operations_log())
                
                # Format output
                output = output_formatter.format_output(
                    success=True,
                    board_id=result['board_id'],
                    board_url=result['board_url'],
                    lists=result['lists'],
                    cards=result['cards'],
                    operations_log=all_logs
                )
                
            except Exception as e:
                logger.error(f"Error creating board from template: {str(e)}")
                output = output_formatter.format_output(
                    success=False,
                    operations_log=all_logs + [f"ERROR: {str(e)}"]
                )
        
        else:
            # No template, configuration, or add-card specified
            logger.error("No action specified")
            output = output_formatter.format_output(
                success=False,
                operations_log=all_logs + ["ERROR: No action specified. Use --template, --config, or --add-card."]
            )
        
        # Output the result
        _output_result(output, args.output)
        
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        output = output_formatter.format_output(
            success=False,
            operations_log=[f"ERROR: {str(e)}"]
        )
        _output_result(output, args.output)
        return 1
    
    return 0


def _output_result(output: Dict, output_file: Optional[str] = None) -> None:
    """
    Output the result to a file or stdout.
    
    Args:
        output: Output data
        output_file: Path to output file (optional)
    """
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            logger.info(f"Output written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing output to {output_file}: {str(e)}")
            print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
