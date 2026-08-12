"""
Test settings for running integration tests.
Uses SQLite for testing to avoid PostgreSQL dependency.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path
BASE_DIR = Path(__file__).resolve().parent.parent

# Import the main settings
from config.settings import *

# Override database settings for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
    }
}

# Disable migrations for faster testing
class DisableMigrations(object):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

if 'test' in sys.argv:
    MIGRATION_MODULES = DisableMigrations()

# Set a default INTERNAL_API_KEY for testing
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY', 'test-internal-api-key-12345')

# Use a simpler password hasher for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
