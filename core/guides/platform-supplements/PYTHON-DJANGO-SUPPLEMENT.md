# Python Django Supplement

**Version:** 1.0  
**Last Updated:** 2026  
**Base Guide:** `PYTHON-CODING-GUIDELINES.md` (load first)  
**Target:** Django 5.x projects (with Django REST Framework for APIs). This supplement covers Django-specific models, views, serializers, testing, security, and configuration patterns.

---

## Table of Contents

1. [Dependency Injection](#dependency-injection)
2. [Architecture Patterns](#architecture-patterns)
3. [Validation](#validation)
4. [Testing](#testing)
5. [Security](#security)
6. [Configuration](#configuration)
7. [Build & Dependencies](#build--dependencies)
8. [References](#references)

---

## Dependency Injection

### Django's Approach

Django does not use explicit DI containers. Dependencies are managed through:
- **Module-level imports** for services and utilities
- **Django's app registry** for model access across apps
- **Settings-based configuration** for swappable backends
- **Middleware** for cross-cutting concerns

```python
# services.py — constructor injection for testability
class UserService:
    def __init__(self, repository=None):
        self.repository = repository or UserRepository()

    def create_user(self, email: str, name: str) -> User:
        return self.repository.create(email=email, name=name)
```

For DRF views, use class attributes or method overrides:

```python
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
```

---

## Architecture Patterns

### Project Structure

```
myproject/
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py          # Shared settings
│   │   ├── development.py   # Dev overrides
│   │   ├── staging.py       # Staging overrides
│   │   └── production.py    # Prod overrides
│   ├── urls.py               # Root URL conf
│   └── wsgi.py
├── users/                     # Django app
│   ├── __init__.py
│   ├── models.py
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # DRF viewsets/views
│   ├── urls.py                # App URL conf
│   ├── services.py            # Business logic
│   ├── repositories.py        # Data access abstraction
│   ├── admin.py
│   ├── apps.py
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_views.py
│       └── test_services.py
├── favorites/                 # Another Django app
│   ├── ...
└── common/                    # Shared utilities
    ├── exceptions.py
    ├── permissions.py
    └── pagination.py
```

### Model Layer

```python
from django.db import models
from django.conf import settings
import uuid

class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorites"
        unique_together = [("user", "product_id")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Favorite({self.user_id}, {self.product_id})"
```

### Repository Layer (Optional Abstraction)

```python
from django.db.models import QuerySet
from uuid import UUID

class FavoriteRepository:
    """Data access abstraction for Favorite model."""

    def add(self, user_id: UUID, product_id: UUID) -> Favorite:
        return Favorite.objects.create(user_id=user_id, product_id=product_id)

    def remove(self, user_id: UUID, product_id: UUID) -> None:
        deleted, _ = Favorite.objects.filter(
            user_id=user_id, product_id=product_id
        ).delete()
        if deleted == 0:
            raise NotFoundError("Favorite", f"{user_id}/{product_id}")

    def find_by_user(self, user_id: UUID) -> QuerySet[Favorite]:
        return Favorite.objects.filter(user_id=user_id)

    def exists(self, user_id: UUID, product_id: UUID) -> bool:
        return Favorite.objects.filter(
            user_id=user_id, product_id=product_id
        ).exists()
```

### DRF ViewSet (Controller Layer)

```python
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if Favorite.objects.filter(
            user=request.user, product_id=serializer.validated_data["product_id"]
        ).exists():
            return Response(
                {"detail": "Already favorited"},
                status=status.HTTP_409_CONFLICT,
            )

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### URL Configuration

```python
# favorites/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"favorites", FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("api/v1/", include(router.urls)),
]

# myproject/urls.py
from django.urls import path, include

urlpatterns = [
    path("", include("favorites.urls")),
    path("", include("users.urls")),
]
```

### Global Exception Handler

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, NotFoundError):
        return Response(
            {"code": "NOT_FOUND", "message": str(exc)},
            status=404,
        )
    if isinstance(exc, ConflictError):
        return Response(
            {"code": "CONFLICT", "message": str(exc)},
            status=409,
        )

    return response
```

Configure in settings: `REST_FRAMEWORK = {"EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler"}`

---

## Validation

### DRF Serializers

```python
from rest_framework import serializers

class AddFavoriteSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "user", "product_id", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(min_length=2, max_length=100)

    def validate_name(self, value: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z\s'-]+$", value):
            raise serializers.ValidationError("Name contains invalid characters")
        return value
```

### Model-Level Validation

```python
from django.core.exceptions import ValidationError

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)

    def clean(self):
        if self.name and len(self.name) < 2:
            raise ValidationError({"name": "Name must be at least 2 characters"})
```

---

## Testing

### Unit Tests

```python
from django.test import TestCase
from unittest.mock import Mock
from favorites.services import FavoriteService

class TestFavoriteService(TestCase):
    def setUp(self):
        self.mock_repo = Mock()
        self.service = FavoriteService(repository=self.mock_repo)

    def test_add_favorite_success(self):
        self.mock_repo.exists.return_value = False
        self.mock_repo.add.return_value = self.make_favorite()

        result = self.service.add_favorite(self.user_id, self.product_id)

        self.mock_repo.add.assert_called_once_with(self.user_id, self.product_id)
        self.assertIsNotNone(result)
```

### Integration Tests (API)

```python
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

class TestFavoritesAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_add_favorite(self):
        response = self.client.post(
            "/api/v1/favorites/",
            {"product_id": "550e8400-e29b-41d4-a716-446655440000"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)

    def test_list_favorites(self):
        Favorite.objects.create(
            user=self.user,
            product_id="550e8400-e29b-41d4-a716-446655440000",
        )
        response = self.client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_unauthenticated_returns_401(self):
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, 401)
```

### pytest-django (Alternative)

```python
import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client(db):
    user = User.objects.create_user(email="test@example.com", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_add_favorite(api_client):
    response = api_client.post(
        "/api/v1/favorites/",
        {"product_id": "550e8400-e29b-41d4-a716-446655440000"},
        format="json",
    )
    assert response.status_code == 201
```

---

## Security

### Django Security Settings

```python
# settings/production.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
```

### DRF Authentication

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
}
```

### Secrets Management

```python
import os
from django.core.exceptions import ImproperlyConfigured

def get_env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise ImproperlyConfigured(f"Set the {key} environment variable")
    return value

SECRET_KEY = get_env("DJANGO_SECRET_KEY")
DATABASE_URL = get_env("DATABASE_URL")
```

---

## Configuration

### Settings Module Pattern

```python
# settings/base.py — shared across all environments
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "users",
    "favorites",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env("DB_NAME", "mydb"),
        "USER": get_env("DB_USER", "postgres"),
        "PASSWORD": get_env("DB_PASSWORD", "postgres"),
        "HOST": get_env("DB_HOST", "localhost"),
        "PORT": get_env("DB_PORT", "5432"),
    }
}

# settings/development.py
from .base import *
DEBUG = True

# settings/production.py
from .base import *
DEBUG = False
```

Activate with: `DJANGO_SETTINGS_MODULE=myproject.settings.production`

### Migrations

```bash
# Create migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

---

## Build & Dependencies

### pyproject.toml

```toml
[project]
name = "my-service"
version = "1.0.0"
dependencies = [
    "django>=5.0,<6.0",
    "djangorestframework>=3.15,<4.0",
    "djangorestframework-simplejwt>=5.3,<6.0",
    "psycopg[binary]>=3.1,<4.0",
    "gunicorn>=21.2,<23.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-django",
    "factory-boy",
    "mypy",
    "django-stubs",
    "black",
    "ruff",
]
```

### Common Commands

```bash
# Run development server
python manage.py runserver 0.0.0.0:8000

# Run with production server
gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Run tests
python manage.py test
# or with pytest
pytest

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

### Common Files to Watch (Phase 4 Conflict Detection)

These Django-specific files are frequently modified by multiple stories:
- `settings/base.py` — `INSTALLED_APPS`, `MIDDLEWARE`, `REST_FRAMEWORK`
- `myproject/urls.py` — root URL configuration
- `requirements.txt` / `pyproject.toml` — dependencies
- Migration files — order-dependent, auto-generated names can conflict

---

## References

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)

---

**Version History:**
- v1.0 (2026) - Initial Django supplement
