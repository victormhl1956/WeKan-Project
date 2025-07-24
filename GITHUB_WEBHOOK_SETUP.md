# GitHub Webhook Setup Guide

This guide explains how to set up GitHub webhooks to synchronize with WeKan boards automatically.

## Prerequisites

1. **WeKan Instance Running**
   ```bash
   docker-compose up -d
   ```

2. **Python Dependencies Installed**
   ```bash
   pip install flask python-dotenv requests
   ```

3. **WeKan User Account**
   - Create an admin user in WeKan
   - Note the username and password

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# WeKan Configuration
WEKAN_URL=http://localhost:8088
WEKAN_USERNAME=your_wekan_username
WEKAN_PASSWORD=your_wekan_password

# GitHub Webhook Configuration
GITHUB_WEBHOOK_SECRET=your_secure_webhook_secret
PORT=5000
DEBUG=false
```

### 2. WeKan Configuration

Copy and customize the WeKan configuration:

```bash
cp wekan_config.json.example wekan_config.json
```

Edit `wekan_config.json`:

```json
{
  "wekan_url": "http://localhost:8088",
  "credentials": {
    "username": "your_wekan_username",
    "password": "your_wekan_password"
  },
  "default_template": "kanban_basic",
  "board_settings": {
    "color": "belize",
    "permission": "private"
  }
}
```

## Running the Webhook Receiver

### 1. Test the Setup

First, test the webhook processing logic:

```bash
python src/test_webhook_receiver.py
```

### 2. Start the Webhook Receiver

```bash
python src/webhook_receiver.py
```

The receiver will start on `http://localhost:5000` with the following endpoints:

- `POST /github-webhook` - Main webhook endpoint
- `GET /health` - Health check endpoint

### 3. Make it Accessible (Production)

For production use, you'll need to make the webhook receiver accessible from the internet:

#### Option A: Using ngrok (Development/Testing)

```bash
# Install ngrok
# Download from https://ngrok.com/

# Expose local port 5000
ngrok http 5000
```

Copy the HTTPS URL provided by ngrok (e.g., `https://abc123.ngrok.io`).

#### Option B: Deploy to Cloud (Production)

Deploy the webhook receiver to a cloud service like:
- Heroku
- AWS Lambda
- Google Cloud Functions
- DigitalOcean App Platform

## GitHub Webhook Configuration

### 1. Repository Settings

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks**
3. Click **Add webhook**

### 2. Webhook Configuration

Fill in the webhook form:

- **Payload URL**: `https://your-domain.com/github-webhook`
- **Content type**: `application/json`
- **Secret**: Use the same secret from your `.env` file
- **SSL verification**: Enable (recommended)

### 3. Event Selection

Choose which events to send:

**Individual events:**
- [x] Issues
- [x] Pull requests
- [x] Pushes
- [x] Repository

**Or select "Send me everything" for all events**

### 4. Test the Webhook

1. Click **Add webhook**
2. GitHub will send a test ping
3. Check the webhook receiver logs for successful processing

## Supported GitHub Events

### Issues (`issues`)

**Triggers:**
- `opened` - New issue created
- `reopened` - Issue reopened
- `edited` - Issue title/description changed
- `closed` - Issue closed

**WeKan Action:**
- Creates a card in "GitHub Issues - {repo_name}" board
- Card placed in "To Do" list for new issues
- Card moved to "Done" list when closed

### Pull Requests (`pull_request`)

**Triggers:**
- `opened` - New PR created
- `reopened` - PR reopened
- `edited` - PR title/description changed

**WeKan Action:**
- Creates a card in "GitHub PRs - {repo_name}" board
- Card placed in "To Do" list for review

### Push Events (`push`)

**Triggers:**
- Commits pushed to main/master branch

**WeKan Action:**
- Creates cards in "GitHub Commits - {repo_name}" board
- Cards placed in "Done" list (completed work)
- Limited to 5 most recent commits per push

### Repository Events (`repository`)

**Triggers:**
- `created` - New repository created

**WeKan Action:**
- Creates a new project board "Project - {repo_name}"
- Adds initial setup card

## Webhook Payload Examples

### Issue Event

```json
{
  "action": "opened",
  "issue": {
    "number": 123,
    "title": "Bug in authentication",
    "body": "Description of the issue...",
    "html_url": "https://github.com/user/repo/issues/123",
    "user": {"login": "username"},
    "state": "open",
    "labels": [{"name": "bug"}]
  },
  "repository": {
    "name": "my-repo",
    "html_url": "https://github.com/user/repo"
  }
}
```

### Pull Request Event

```json
{
  "action": "opened",
  "pull_request": {
    "number": 456,
    "title": "Fix authentication bug",
    "body": "This PR fixes the authentication issue...",
    "html_url": "https://github.com/user/repo/pull/456",
    "user": {"login": "username"},
    "base": {"ref": "main"},
    "head": {"ref": "fix-auth"}
  },
  "repository": {
    "name": "my-repo"
  }
}
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   ERROR - Failed to initialize WeKan API: Authentication failed
   ```
   - Check WeKan username/password in configuration
   - Ensure WeKan instance is running
   - Verify WeKan URL is accessible

2. **Invalid Signature**
   ```
   WARNING - Invalid webhook signature
   ```
   - Check webhook secret matches in GitHub and configuration
   - Ensure secret is properly set in environment variables

3. **Module Not Found**
   ```
   ModuleNotFoundError: No module named 'flask'
   ```
   - Install required dependencies: `pip install flask python-dotenv`
   - Activate virtual environment if using one

4. **Connection Refused**
   ```
   ConnectionError: Failed to establish connection
   ```
   - Check if WeKan is running: `docker ps`
   - Verify WeKan URL and port
   - Check firewall settings

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python src/webhook_receiver.py
```

### Health Check

Test the webhook receiver health:

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-24T18:00:00.000000",
  "wekan_connected": true
}
```

## Security Considerations

1. **Use HTTPS**: Always use HTTPS for webhook URLs in production
2. **Verify Signatures**: The receiver validates GitHub webhook signatures
3. **Environment Variables**: Store secrets in environment variables, not code
4. **Access Control**: Restrict access to the webhook endpoint
5. **Rate Limiting**: Consider implementing rate limiting for production use

## Monitoring and Logging

The webhook receiver logs all activities:

- **INFO**: Normal operations (webhook received, card created)
- **WARNING**: Non-critical issues (invalid signature, unhandled events)
- **ERROR**: Critical failures (authentication failed, API errors)

Monitor logs for:
- Failed webhook deliveries
- Authentication issues
- API rate limits
- Unexpected errors

## Next Steps

1. **Bidirectional Sync**: Implement WeKan → GitHub synchronization
2. **Card Mapping**: Store GitHub issue/PR IDs in WeKan cards for updates
3. **Advanced Filtering**: Add rules for which events to process
4. **Multiple Repositories**: Support multiple GitHub repositories
5. **Dashboard**: Create a web dashboard for monitoring sync status

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review webhook receiver logs
3. Test with the provided test script
4. Verify GitHub webhook delivery logs
