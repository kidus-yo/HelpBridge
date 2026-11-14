"""
Django settings for Digital Bridge project.
ALX Digital Bridge Accessibility Hackathon 2026 - Track 3
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR.parent / '.env')

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-digital-bridge-hackathon-2026-demo-key'
)

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,*').split(',')
    if host.strip()
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'drf_spectacular',
    # Project Apps
    'common.apps.CommonConfig',
    'ai_engine.apps.AiEngineConfig',
    'channels.apps.ChannelsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# Default to SQLite for easy local development / judging; PostgreSQL if configured
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# DRF Spectacular OpenAPI documentation settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Digital Bridge Assistant API',
    'DESCRIPTION': (
        'Level 2 REST API for Digital Bridge Assistant (Track 3: Multilingual Assistant & Live Help). '
        'Provides retrieval-grounded course Q&A in English and Amharic, offline FAQ fallback, '
        'Telegram bot webhook, and 160-char low-bandwidth SMS delivery adapter.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# AI Engine Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'offline')  # offline, cloud, local, mock
AI_CLOUD_PROVIDER = os.getenv('AI_CLOUD_PROVIDER', 'openai')
AI_CLOUD_API_KEY = os.getenv('AI_CLOUD_API_KEY', '')
AI_CLOUD_MODEL = os.getenv('AI_CLOUD_MODEL', 'gpt-4o-mini')
AI_LOCAL_ENDPOINT = os.getenv('AI_LOCAL_ENDPOINT', 'http://localhost:11434/v1')
AI_LOCAL_MODEL = os.getenv('AI_LOCAL_MODEL', 'llama3')
AI_GROUNDING_THRESHOLD = float(os.getenv('AI_GROUNDING_THRESHOLD', '0.20'))

# Channels Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'DigitalBridgeAssistantBot')

SMS_GATEWAY_API_KEY = os.getenv('SMS_GATEWAY_API_KEY', '')
SMS_DEFAULT_SENDER = os.getenv('SMS_DEFAULT_SENDER', '+251911000000')

DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'am')
