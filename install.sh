#!/usr/bin/env bash
# Simple installer for the Workshop Quotes app
# 1. Ensures Python 3 is installed
# 2. Ensures pip is available (tries to bootstrap if missing)
# 3. Sets up a virtual environment and installs requirements

set -e

# Helper to print messages
info() { echo "[INFO] $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# Check for python3
if ! command -v python3 >/dev/null 2>&1; then
    error "Python 3 is required but not found. Please install Python 3."
fi

# Ensure pip exists for python3
if ! python3 -m pip --version >/dev/null 2>&1; then
    info "pip not found, attempting to bootstrap using ensurepip..."
    if python3 -m ensurepip --default-pip; then
        info "pip installed via ensurepip."
    else
        info "ensurepip failed, trying get-pip.py from bootstrap.pypa.io"
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3 || error "Unable to install pip."
    fi
fi

# create virtual environment
if [ ! -d "venv" ]; then
    info "Creating virtual environment in ./venv"
    python3 -m venv venv
fi

# activate and install requirements
# shellcheck disable=SC1090
source venv/bin/activate
info "Installing Python dependencies from requirements.txt"
pip install --upgrade pip
pip install -r requirements.txt

# no system libraries required for minimal Azure deployment
# we use pure-Python reportlab for any PDF needs; avoid heavy native deps

info "Setup complete. Activate the environment with 'source venv/bin/activate' and run 'python app.py' to start the server."
