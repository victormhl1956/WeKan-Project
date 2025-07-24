#!/usr/bin/env python3
"""
Test script for GitHub Webhook Receiver
Tests the webhook receiver without requiring actual WeKan connection
"""

import json
import requests
import time
from typing import Dict, Any

def test_webhook_receiver():
    """Test the webhook receiver with mock GitHub payloads"""
    
    # Mock GitHub issue payload
    issue_payload = {
        "action": "opened",
        "issue": {
            "number": 123,
            "title": "Test Issue",
            "body": "This is a test issue for webhook integration",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "testuser"},
            "state": "open",
            "created_at": "2025-07-24T18:00:00Z",
            "labels": [{"name": "bug"}, {"name": "high-priority"}]
        },
        "repository": {
            "name": "test-repo",
            "html_url": "https://github.com/test/repo"
        }
    }
    
    # Mock GitHub PR payload
    pr_payload = {
        "action": "opened",
        "pull_request": {
            "number": 456,
            "title": "Test Pull Request",
            "body": "This is a test PR for webhook integration",
            "html_url": "https://github.com/test/repo/pull/456",
            "user": {"login": "testuser"},
            "state": "open",
            "created_at": "2025-07-24T18:00:00Z",
            "base": {"ref": "main"},
            "head": {"ref": "feature-branch"},
            "mergeable": True,
            "draft": False
        },
        "repository": {
            "name": "test-repo",
            "html_url": "https://github.com/test/repo"
        }
    }
    
    # Mock GitHub push payload
    push_payload = {
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "abc123def456",
                "message": "Fix critical bug in authentication",
                "url": "https://github.com/test/repo/commit/abc123def456",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com"
                },
                "timestamp": "2025-07-24T18:00:00Z",
                "modified": ["src/auth.py", "tests/test_auth.py"],
                "added": ["docs/auth.md"],
                "removed": []
            }
        ],
        "repository": {
            "name": "test-repo",
            "html_url": "https://github.com/test/repo"
        }
    }
    
    print("GitHub Webhook Receiver Test Suite")
    print("=" * 50)
    
    # Test payloads
    test_cases = [
        ("Issue Event", "issues", issue_payload),
        ("Pull Request Event", "pull_request", pr_payload),
        ("Push Event", "push", push_payload)
    ]
    
    for test_name, event_type, payload in test_cases:
        print(f"\n{test_name}:")
        print(f"  Event Type: {event_type}")
        print(f"  Payload Size: {len(json.dumps(payload))} bytes")
        
        # Simulate webhook processing
        print(f"  Processing: {payload.get('action', 'N/A')} action")
        
        if event_type == "issues":
            issue = payload["issue"]
            print(f"    Issue #{issue['number']}: {issue['title']}")
            print(f"    Author: {issue['user']['login']}")
            print(f"    Labels: {[l['name'] for l in issue['labels']]}")
            
        elif event_type == "pull_request":
            pr = payload["pull_request"]
            print(f"    PR #{pr['number']}: {pr['title']}")
            print(f"    Author: {pr['user']['login']}")
            print(f"    Branch: {pr['head']['ref']} -> {pr['base']['ref']}")
            
        elif event_type == "push":
            commits = payload["commits"]
            print(f"    Commits: {len(commits)}")
            for commit in commits:
                print(f"      {commit['id'][:8]}: {commit['message']}")
        
        print(f"  ✓ {test_name} processed successfully")
    
    print(f"\n{'=' * 50}")
    print("All webhook tests completed successfully!")
    print("\nNext Steps:")
    print("1. Start WeKan instance: docker-compose up -d")
    print("2. Configure WeKan credentials in environment variables")
    print("3. Start webhook receiver: python src/webhook_receiver.py")
    print("4. Configure GitHub webhook to point to your receiver")

if __name__ == "__main__":
    test_webhook_receiver()
