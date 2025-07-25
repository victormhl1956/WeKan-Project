#!/bin/bash

# WeKan-Project Deployment Script
# This script automates the setup and deployment of the WeKan-GitHub integration.

# Exit on any error
set -e

# --- Configuration ---
ENV_FILE=".env"
WEKAN_CONFIG_FILE="wekan_config.json"
WEKAN_CONFIG_EXAMPLE="wekan_config.json.example"
DOCKER_COMPOSE_FILE="../docker-compose.yml"

# --- Helper Functions ---
log_info() {
    echo "[INFO] $1"
}

log_success() {
    echo "[SUCCESS] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# --- Main Deployment Steps ---

# 1. Check for prerequisites
log_info "Checking for prerequisites..."
command -v docker >/dev/null 2>&1 || log_error "Docker is not installed. Please install it first."
command -v docker-compose >/dev/null 2>&1 || log_error "Docker Compose is not installed. Please install it first."
command -v py >/dev/null 2>&1 || log_error "Python is not installed. Please install it first."
py -m pip --version >/dev/null 2>&1 || log_error "pip is not installed. Please install it first."

# 2. Set up environment file
if [ ! -f "$ENV_FILE" ]; then
    log_info "Creating .env file from template..."
    cat > "$ENV_FILE" <<EOL
# WeKan Configuration
WEKAN_URL=http://localhost:8088
WEKAN_USERNAME=your_wekan_username
WEKAN_PASSWORD=your_wekan_password

# GitHub Webhook Configuration
GITHUB_WEBHOOK_SECRET=your_secure_webhook_secret
PORT=5000
DEBUG=false
EOL
    log_success ".env file created. Please edit it with your credentials."
else
    log_info ".env file already exists."
fi

# 3. Set up WeKan config file
if [ ! -f "$WEKAN_CONFIG_FILE" ]; then
    log_info "Creating wekan_config.json from example..."
    cp "$WEKAN_CONFIG_EXAMPLE" "$WEKAN_CONFIG_FILE"
    log_success "wekan_config.json created. Please edit it with your credentials."
else
    log_info "wekan_config.json already exists."
fi

# 4. Start WeKan instance
log_info "Starting WeKan instance with Docker Compose..."
if [ -f "$DOCKER_COMPOSE_FILE" ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d wekan-app wekan-db
    log_success "WeKan instance started."
else
    log_error "docker-compose.yml not found in parent directory."
fi

# 5. Install Python dependencies
log_info "Installing Python dependencies from requirements.txt..."
py -m pip install -r requirements.txt
log_success "Python dependencies installed."

# 6. Run tests
log_info "Running tests..."
py test_wekan_api.py
py test_wekan_integration.py
py src/test_webhook_receiver.py
log_success "All tests passed."

# 7. Start the webhook receiver
log_info "Starting the webhook receiver..."
log_info "To run in development mode: py src/webhook_receiver.py"
log_info "To run in production mode: gunicorn --bind 0.0.0.0:5000 src.webhook_receiver:app"

log_success "Deployment script completed successfully."
echo "Please make sure to configure your .env and wekan_config.json files before starting the webhook receiver."
