#!/usr/bin/env python3
"""
GitHub Webhook Receiver for WeKan Integration (Standalone Version)
This version works without WeKan connection for testing and debugging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'test_secret_key_for_development')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

def verify_signature(payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        logger.warning("No signature provided")
        return True  # Allow for testing without signature
    
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'wekan_connected': False,
        'mode': 'standalone'
    })

@app.route('/github-webhook', methods=['POST'])
def handle_webhook():
    """Main webhook handler"""
    try:
        # Verify signature (optional in standalone mode)
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
        elif event == 'ping':
            return handle_ping_event(payload)
        else:
            logger.info(f"Unhandled event type: {event}")
            return jsonify({'status': 'Event not handled', 'event': event}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_ping_event(payload: Dict) -> Any:
    """Handle GitHub ping events"""
    logger.info("Received ping event from GitHub")
    return jsonify({
        'status': 'success',
        'message': 'Webhook receiver is working!',
        'zen': payload.get('zen', 'No zen provided')
    })

def handle_issue_event(payload: Dict) -> Any:
    """Handle GitHub issue events"""
    try:
        action = payload['action']
        issue = payload['issue']
        repository = payload['repository']
        
        logger.info(f"Processing issue event: {action} for issue #{issue['number']}")
        
        if action in ['opened', 'reopened', 'edited']:
            # Simulate WeKan board creation
            board_name = f"GitHub Issues - {repository['name']}"
            
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
            
            logger.info(f"Would create WeKan card: {card_title}")
            logger.info(f"In board: {board_name}")
            
            return jsonify({
                'status': 'success',
                'action': action,
                'board_name': board_name,
                'card_title': card_title,
                'message': f"Issue #{issue['number']} would be synchronized to WeKan",
                'mode': 'standalone'
            })
        
        elif action == 'closed':
            logger.info(f"Issue #{issue['number']} closed - would move card to Done list")
            return jsonify({
                'status': 'success',
                'action': action,
                'message': f"Issue #{issue['number']} closed",
                'mode': 'standalone'
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
            # Simulate WeKan board creation
            board_name = f"GitHub PRs - {repository['name']}"
            
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
            
            logger.info(f"Would create WeKan card: {card_title}")
            logger.info(f"In board: {board_name}")
            
            return jsonify({
                'status': 'success',
                'action': action,
                'board_name': board_name,
                'card_title': card_title,
                'message': f"PR #{pr['number']} would be synchronized to WeKan",
                'mode': 'standalone'
            })
        
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
            
            cards_created = 0
            for commit in commits[:5]:  # Limit to 5 most recent commits
                commit_message = commit['message'].split('\n')[0]  # First line only
                card_title = f"Commit: {commit_message}"
                
                logger.info(f"Would create WeKan card: {card_title}")
                cards_created += 1
            
            logger.info(f"Would create {cards_created} cards in board: {board_name}")
            
            return jsonify({
                'status': 'success',
                'board_name': board_name,
                'cards_created': cards_created,
                'message': f"Processed {len(commits)} commits, would create {cards_created} cards",
                'mode': 'standalone'
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
            # Simulate creating a new board for the repository
            board_name = f"Project - {repository['name']}"
            
            logger.info(f"Would create WeKan board: {board_name}")
            
            return jsonify({
                'status': 'success',
                'action': action,
                'board_name': board_name,
                'message': f"Would create board for repository {repository['name']}",
                'mode': 'standalone'
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
    # Start the Flask application
    logger.info("Starting GitHub Webhook Receiver (Standalone Mode)...")
    logger.info(f"Port: {PORT}")
    logger.info("Webhook endpoint: /github-webhook")
    logger.info("Health check endpoint: /health")
    logger.info("Mode: Standalone (no WeKan connection required)")
    
    app.run(
        host='0.0.0.0', 
        port=PORT,
        debug=DEBUG
    )
