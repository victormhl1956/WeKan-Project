#!/usr/bin/env python3
"""
GitHub Webhook Receiver for WeKan Integration
Implements bidirectional synchronization between GitHub and WeKan
"""

import os
import sys
import json
import hmac
import hashlib
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Optional, Any

# Add parent directory to path to import wekan_board_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wekan_board_manager import WekanAuthManager, WekanAPIClient, BoardCreator, BoardTemplateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'your_github_webhook_secret')
WEKAN_URL = os.getenv('WEKAN_URL', 'http://localhost:8088')
WEKAN_USERNAME = os.getenv('WEKAN_USERNAME', 'admin')
WEKAN_PASSWORD = os.getenv('WEKAN_PASSWORD', 'admin123')

# Global WeKan components
wekan_auth = None
wekan_api = None
board_creator = None

def initialize_wekan():
    """Initialize WeKan API components"""
    global wekan_auth, wekan_api, board_creator
    
    try:
        wekan_auth = WekanAuthManager(WEKAN_URL, WEKAN_USERNAME, WEKAN_PASSWORD)
        wekan_api = WekanAPIClient(WEKAN_URL, wekan_auth)
        template_manager = BoardTemplateManager()
        board_creator = BoardCreator(wekan_api, template_manager)
        logger.info("WeKan API components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize WeKan API: {str(e)}")
        return False

def verify_signature(payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    
    try:
        hmac_digest = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f'sha256={hmac_digest}', signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False

def get_or_create_board(board_name: str) -> Optional[Dict]:
    """Get existing board or create new one"""
    try:
        # For now, we'll create boards using the template system
        # In a full implementation, we'd first check if board exists
        result = board_creator.create_board_from_template(
            template_name='kanban_basic',
            board_title=board_name
        )
        return {
            '_id': result['board_id'],
            'title': board_name,
            'url': result['board_url']
        }
    except Exception as e:
        logger.error(f"Error creating board '{board_name}': {str(e)}")
        return None

def add_card_to_board(board_id: str, list_name: str, title: str, description: str = "") -> Optional[Dict]:
    """Add a card to a specific board and list"""
    try:
        result = board_creator.add_card_to_board(
            board_id=board_id,
            list_name=list_name,
            card_title=title,
            card_description=description
        )
        return {
            '_id': result['card_id'],
            'title': title,
            'description': description,
            'url': result.get('card_url')
        }
    except Exception as e:
        logger.error(f"Error adding card to board {board_id}: {str(e)}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'wekan_connected': wekan_auth is not None
    })

@app.route('/github-webhook', methods=['POST'])
def handle_webhook():
    """Main webhook handler"""
    try:
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401

        event = request.headers.get('X-GitHub-Event')
        payload = request.get_json()

        if not payload:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        logger.info(f"Received GitHub webhook event: {event}")

        # Process different GitHub events
        if event == 'issues':
            return handle_issue_event(payload)
        elif event == 'pull_request':
            return handle_pull_request_event(payload)
        elif event == 'push':
            return handle_push_event(payload)
        elif event == 'repository':
            return handle_repository_event(payload)
        else:
            logger.info(f"Unhandled event type: {event}")
            return jsonify({'status': 'Event not handled', 'event': event}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_issue_event(payload: Dict) -> Any:
    """Handle GitHub issue events"""
    try:
        action = payload['action']
        issue = payload['issue']
        repository = payload['repository']
        
        logger.info(f"Processing issue event: {action} for issue #{issue['number']}")
        
        if action in ['opened', 'reopened', 'edited']:
            # Create board name based on repository
            board_name = f"GitHub Issues - {repository['name']}"
            
            # Get or create the board
            board = get_or_create_board(board_name)
            if not board:
                return jsonify({'error': 'Failed to create/get board'}), 500
            
            # Create card title and description
            card_title = f"Issue #{issue['number']}: {issue['title']}"
            card_desc = f"""
**GitHub Issue**: {issue['html_url']}
**Author**: {issue['user']['login']}
**State**: {issue['state']}
**Created**: {issue['created_at']}

**Description**:
{issue['body'] or 'No description provided'}

**Labels**: {', '.join([label['name'] for label in issue.get('labels', [])])}
"""
            
            # Add card to the appropriate list
            list_name = 'To Do' if action == 'opened' else 'Backlog'
            card = add_card_to_board(board['_id'], list_name, card_title, card_desc)
            
            if card:
                return jsonify({
                    'status': 'success',
                    'action': action,
                    'board_id': board['_id'],
                    'card_id': card['_id'],
                    'message': f"Issue #{issue['number']} synchronized to WeKan"
                })
            else:
                return jsonify({'error': 'Failed to create card'}), 500
        
        elif action == 'closed':
            # In a full implementation, we'd move the card to 'Done'
            logger.info(f"Issue #{issue['number']} closed - would move card to Done list")
            return jsonify({
                'status': 'success',
                'action': action,
                'message': f"Issue #{issue['number']} closed"
            })
        
        return jsonify({'status': 'Issue event processed', 'action': action})
        
    except Exception as e:
        logger.error(f"Error handling issue event: {str(e)}")
        return jsonify({'error': 'Failed to process issue event'}), 500

def handle_pull_request_event(payload: Dict) -> Any:
    """Handle GitHub pull request events"""
    try:
        action = payload['action']
        pr = payload['pull_request']
        repository = payload['repository']
        
        logger.info(f"Processing PR event: {action} for PR #{pr['number']}")
        
        if action in ['opened', 'reopened', 'edited']:
            # Create board name based on repository
            board_name = f"GitHub PRs - {repository['name']}"
            
            # Get or create the board
            board = get_or_create_board(board_name)
            if not board:
                return jsonify({'error': 'Failed to create/get board'}), 500
            
            # Create card title and description
            card_title = f"PR #{pr['number']}: {pr['title']}"
            card_desc = f"""
**GitHub Pull Request**: {pr['html_url']}
**Author**: {pr['user']['login']}
**State**: {pr['state']}
**Base Branch**: {pr['base']['ref']}
**Head Branch**: {pr['head']['ref']}
**Created**: {pr['created_at']}

**Description**:
{pr['body'] or 'No description provided'}

**Mergeable**: {pr.get('mergeable', 'Unknown')}
**Draft**: {pr.get('draft', False)}
"""
            
            # Add card to Review list
            card = add_card_to_board(board['_id'], 'To Do', card_title, card_desc)
            
            if card:
                return jsonify({
                    'status': 'success',
                    'action': action,
                    'board_id': board['_id'],
                    'card_id': card['_id'],
                    'message': f"PR #{pr['number']} synchronized to WeKan"
                })
            else:
                return jsonify({'error': 'Failed to create card'}), 500
        
        return jsonify({'status': 'PR event processed', 'action': action})
        
    except Exception as e:
        logger.error(f"Error handling PR event: {str(e)}")
        return jsonify({'error': 'Failed to process PR event'}), 500

def handle_push_event(payload: Dict) -> Any:
    """Handle GitHub push events"""
    try:
        ref = payload['ref']
        commits = payload['commits']
        repository = payload['repository']
        
        logger.info(f"Processing push event: {len(commits)} commits to {ref}")
        
        # Only process pushes to main/master branch
        if ref in ['refs/heads/main', 'refs/heads/master']:
            board_name = f"GitHub Commits - {repository['name']}"
            
            # Get or create the board
            board = get_or_create_board(board_name)
            if not board:
                return jsonify({'error': 'Failed to create/get board'}), 500
            
            cards_created = 0
            for commit in commits[:5]:  # Limit to 5 most recent commits
                commit_message = commit['message'].split('\n')[0]  # First line only
                card_title = f"Commit: {commit_message}"
                card_desc = f"""
**GitHub Commit**: {commit['url']}
**Author**: {commit['author']['name']} <{commit['author']['email']}>
**Timestamp**: {commit['timestamp']}
**SHA**: {commit['id'][:8]}

**Full Message**:
{commit['message']}

**Modified Files**: {len(commit.get('modified', []))}
**Added Files**: {len(commit.get('added', []))}
**Removed Files**: {len(commit.get('removed', []))}
"""
                
                card = add_card_to_board(board['_id'], 'Done', card_title, card_desc)
                if card:
                    cards_created += 1
            
            return jsonify({
                'status': 'success',
                'board_id': board['_id'],
                'cards_created': cards_created,
                'message': f"Processed {len(commits)} commits, created {cards_created} cards"
            })
        
        return jsonify({'status': 'Push event processed', 'ref': ref})
        
    except Exception as e:
        logger.error(f"Error handling push event: {str(e)}")
        return jsonify({'error': 'Failed to process push event'}), 500

def handle_repository_event(payload: Dict) -> Any:
    """Handle GitHub repository events"""
    try:
        action = payload['action']
        repository = payload['repository']
        
        logger.info(f"Processing repository event: {action} for {repository['name']}")
        
        if action == 'created':
            # Create a new board for the repository
            board_name = f"Project - {repository['name']}"
            board = get_or_create_board(board_name)
            
            if board:
                # Add initial setup card
                setup_card = add_card_to_board(
                    board['_id'], 
                    'To Do', 
                    'Repository Setup',
                    f"""
**Repository**: {repository['html_url']}
**Description**: {repository.get('description', 'No description')}
**Language**: {repository.get('language', 'Unknown')}
**Private**: {repository['private']}
**Created**: {repository['created_at']}

Initial setup tasks for the new repository.
"""
                )
                
                return jsonify({
                    'status': 'success',
                    'action': action,
                    'board_id': board['_id'],
                    'message': f"Created board for repository {repository['name']}"
                })
        
        return jsonify({'status': 'Repository event processed', 'action': action})
        
    except Exception as e:
        logger.error(f"Error handling repository event: {str(e)}")
        return jsonify({'error': 'Failed to process repository event'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize WeKan connection
    if not initialize_wekan():
        logger.error("Failed to initialize WeKan connection. Exiting.")
        sys.exit(1)
    
    # Start the Flask application
    logger.info("Starting GitHub Webhook Receiver...")
    logger.info(f"WeKan URL: {WEKAN_URL}")
    logger.info("Webhook endpoint: /github-webhook")
    logger.info("Health check endpoint: /health")
    
    app.run(
        host='0.0.0.0', 
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
