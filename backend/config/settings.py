"""
Django settings for HelpBridge / Digital Bridge.
ALX Digital Bridge Accessibility Hackathon 2026 - Track 3
"""

import os
import sys
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

env = environ.Env(
    DEBUG=(bool, True),
    DJANGO_ENV=(str, "development"),
)
if (ROOT_DIR / ".env").exists():
    environ.Env.read_env(str(ROOT_DIR / ".env"))

DJANGO_ENV = env("DJANGO_ENV", default="development")
TESTING = "test" in sys.argv or "pytest" in sys.modules or env.bool("PYTEST_RUNNING", default=False)

SECRET_KEY = env("SECRET_KEY", default="django-insecure-digital-bridge-hackathon-2026-demo-key")
DEBUG = env.bool("DEBUG", default=True)
if DJANGO_ENV == "production" and SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Set a non-default SECRET_KEY in production.")

ALLOWED_HOSTS = [
    host.strip()
    for host in env("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0,*").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",
    "drf_spectacular",

    # Shared foundation
    "common.apps.CommonConfig",

    # Platform foundation
    "platforms.apps.PlatformsConfig",
    "courses.apps.CoursesConfig",
    "knowledge.apps.KnowledgeConfig",

    # AI and communication
    "ai_engine.apps.AiEngineConfig",
    "channels.apps.ChannelsConfig",

    # Teammates' apps
    "chat.apps.ChatConfig",
    "accessibility.apps.AccessibilityConfig",
    "support.apps.SupportConfig",
    "careers.apps.CareersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.WidgetCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL")}
elif DJANGO_ENV == "production" and not TESTING:
    raise ImproperlyConfigured(
        "DATABASE_URL is required when DJANGO_ENV=production. "
        "PostgreSQL is required; SQLite is not used in production."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [ROOT_DIR / "frontend"]
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "HelpBridge / Digital Bridge Assistant API",
    "DESCRIPTION": (
        "Level 2 REST API for Track 3: Multilingual Assistant & Live Help. "
        "Includes institution/platform tenancy, course structure, document processing, "
        "knowledge retrieval, retrieval-grounded Q&A, Telegram, and SMS adapters."
    ),
    "VERSION": "1.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

AI_PROVIDER = env("AI_PROVIDER", default="offline")
AI_CLOUD_PROVIDER = env("AI_CLOUD_PROVIDER", default="openai")
AI_CLOUD_API_KEY = env("AI_CLOUD_API_KEY", default="")
AI_CLOUD_MODEL = env("AI_CLOUD_MODEL", default="gpt-4o-mini")
AI_LOCAL_ENDPOINT = env("AI_LOCAL_ENDPOINT", default="")
AI_LOCAL_MODEL = env("AI_LOCAL_MODEL", default="llama3")
AI_GROUNDING_THRESHOLD = env.float("AI_GROUNDING_THRESHOLD", default=0.20)

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="DigitalBridgeAssistantBot")

SMS_GATEWAY_API_KEY = env("SMS_GATEWAY_API_KEY", default="")
SMS_DEFAULT_SENDER = env("SMS_DEFAULT_SENDER", default="+251911000000")

DEFAULT_LANGUAGE = env("DEFAULT_LANGUAGE", default="am")
CHANNEL_PLATFORM_INTEGRATION_ID = env("CHANNEL_PLATFORM_INTEGRATION_ID", default="")
CHANNEL_DEFAULT_COURSE_ID = env("CHANNEL_DEFAULT_COURSE_ID", default="")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

PLATFORM_CONTEXT_SIGNING_KEY = env("PLATFORM_CONTEXT_SIGNING_KEY", default=SECRET_KEY)
PLATFORM_CONTEXT_TTL_SECONDS = env.int("PLATFORM_CONTEXT_TTL_SECONDS", default=900)
DOCUMENT_MAX_UPLOAD_MB = env.int("DOCUMENT_MAX_UPLOAD_MB", default=10)
DOCUMENT_STORAGE_BACKEND = env("DOCUMENT_STORAGE_BACKEND", default="local")
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", default="hash")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "knowledge": {"handlers": ["console"], "level": "INFO"},
        "platforms": {"handlers": ["console"], "level": "INFO"},
    },
}
