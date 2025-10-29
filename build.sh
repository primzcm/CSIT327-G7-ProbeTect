#!/usr/bin/env bash

# Fail fast on errors or unset variables
set -o errexit
set -o nounset
set -o pipefail

# Install Python dependencies and collect static assets for deployment
pip install -r requirements.txt
python manage.py collectstatic --noinput
