"""
Pytest configuration for backend tests.
Sets up required environment variables before any imports.
"""

import os

# Set test environment variables BEFORE any application imports
# These are test-only values and should never be used in production
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key-for-testing-only")
