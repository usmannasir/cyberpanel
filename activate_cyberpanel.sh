#!/bin/bash
# CyberPanel Django Environment Activator
# This script activates the virtual environment for CyberPanel with Django 5.2.5

echo "Activating CyberPanel virtual environment..."

# Check if virtual environment exists
if [[ ! -f "cyberpanel_env/bin/activate" ]]; then
    echo "Error: CyberPanel virtual environment not found at cyberpanel_env/bin/activate"
    echo "Please run setup-dev.sh first to create the virtual environment."
    exit 1
fi

source cyberpanel_env/bin/activate

# Verify activation worked
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment activated successfully!"
    echo "Django version: $(python -c 'import django; print(django.get_version())')"
    echo ""
    echo "You can now run Django commands like:"
    echo "  python manage.py runserver"
    echo "  python manage.py check"
    echo "  python manage.py makemigrations"
    echo ""
    echo "To deactivate, run: deactivate"
else
    echo "Error: Failed to activate virtual environment"
    exit 1
fi
