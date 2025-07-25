#!/usr/bin/env python3
"""
Test Suite for Standalone Webhook Receiver
"""

import unittest
import requests
import json
import os
from datetime import datetime

class TestWebhookReceiver(unittest.TestCase):
    BASE_URL = "http://localhost:5000"
    TEST_SECRET = "test_secret_key_for_development"

    @classmethod
    def setUpClass(cls):
        """Verify server is running before tests"""
        try:
            response = requests.get(f"{cls.BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Webhook receiver not responding")
        except Exception as e:
            raise ConnectionError(f"Could not connect to webhook receiver: {str(e)}")

    def generate_signature(self, payload):
        """Generate valid GitHub signature for testing"""
        import hmac
        import hashlib
        return hmac.new(
            self.TEST_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertFalse(data['wekan_connected'])
        self.assertEqual(data['mode'], 'standalone')

    def test_ping_event(self):
        """Test GitHub ping event"""
        payload = {
            "zen": "Testing the webhook receiver",
            "hook_id": 12345,
            "hook": {
                "type": "Repository",
                "id": 12345,
                "active": True
            }
        }
        headers = {
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": f"sha256={self.generate_signature(json.dumps(payload).encode())}"
        }
        response = requests.post(
            f"{self.BASE_URL}/github-webhook",
            json=payload,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Webhook receiver is working!')

    def test_issue_event(self):
        """Test GitHub issue event"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 1,
                "title": "Test Issue",
                "body": "This is a test issue",
                "state": "open",
                "created_at": datetime.now().isoformat(),
                "html_url": "http://github.com/test/repo/issues/1",
                "user": {"login": "tester"}
            },
            "repository": {
                "name": "test-repo",
                "full_name": "test/test-repo"
            }
        }
        headers = {
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": f"sha256={self.generate_signature(json.dumps(payload).encode())}"
        }
        response = requests.post(
            f"{self.BASE_URL}/github-webhook",
            json=payload,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'opened')
        self.assertEqual(data['board_name'], 'GitHub Issues - test-repo')
        self.assertEqual(data['card_title'], 'Issue #1: Test Issue')

    def test_pr_event(self):
        """Test GitHub pull request event"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 2,
                "title": "Test PR",
                "body": "This is a test PR",
                "state": "open",
                "created_at": datetime.now().isoformat(),
                "html_url": "http://github.com/test/repo/pull/2",
                "user": {"login": "tester"},
                "base": {"ref": "main"},
                "head": {"ref": "feature"},
                "draft": False
            },
            "repository": {
                "name": "test-repo",
                "full_name": "test/test-repo"
            }
        }
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": f"sha256={self.generate_signature(json.dumps(payload).encode())}"
        }
        response = requests.post(
            f"{self.BASE_URL}/github-webhook",
            json=payload,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'opened')
        self.assertEqual(data['board_name'], 'GitHub PRs - test-repo')
        self.assertEqual(data['card_title'], 'PR #2: Test PR')

    def test_invalid_signature(self):
        """Test webhook with invalid signature"""
        payload = {"test": "data"}
        headers = {
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=invalid_signature"
        }
        response = requests.post(
            f"{self.BASE_URL}/github-webhook",
            json=payload,
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'Invalid signature')

if __name__ == '__main__':
    unittest.main()
