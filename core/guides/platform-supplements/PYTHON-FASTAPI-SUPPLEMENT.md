# Python FastAPI Supplement

**Version:** 1.0  
**Last Updated:** 2026  
**Base Guide:** `PYTHON-CODING-GUIDELINES.md` (load first)  
**Target:** FastAPI 0.100+ projects. This supplement covers FastAPI-specific routing, dependency injection, validation, testing, and configuration patterns.

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

### FastAPI Depends()

FastAPI uses `Depends()` for dependency injection at the route level:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

def get_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)

def get_service(repo: UserRepository = Depends(get_repository)) -> UserService:
    return UserService(repository=repo)
```

**Rules:**
- Use `Depends()` for all service/repository wiring in routes
- Use `yield` dependencies for resources that need cleanup (sessions, connections)
- Keep dependency chains shallow (max 3 levels)
- Use `Depends()` in route parameters, not inside function bodies

---

## Architecture Patterns

### Router (Controller Layer)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

router = APIRouter(prefix="/favorites", tags=["favorites"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=FavoriteResponse)
async def add_favorite(
    dto: AddFavoriteDto,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteResponse:
    """Add a product to user's favorites."""
    try:
        return await service.add_favorite(user.id, dto.product_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    product_id: UUID,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    """Remove a product from user's favorites."""
    await service.remove_favorite(user.id, product_id)

@router.get("/", response_model=PaginatedResponse[FavoriteResponse])
async def get_favorites(
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> PaginatedResponse[FavoriteResponse]:
    """Get user's favorites with pagination."""
    items = await service.get_user_favorites(user.id, pagination)
    total = await service.count_user_favorites(user.id)

    return PaginatedResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
        has_more=pagination.offset + len(items) < total,
    )
```

### Application Wiring

```python
from fastapi import FastAPI
from app.api import favorites, users, auth

app = FastAPI(
    title="My Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(favorites.router)
```

### Lifespan (Startup/Shutdown)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()

app = FastAPI(lifespan=lifespan)
```

### Exception Handlers (Global)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"code": "NOT_FOUND", "message": str(exc)},
    )

@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"code": "CONFLICT", "message": str(exc)},
    )
```

---

## Validation

### Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class AddFavoriteDto(BaseModel):
    """Request body for adding a favorite."""
    product_id: UUID = Field(..., description="Product UUID to favorite")

class FavoriteResponse(BaseModel):
    """Response model for favorite."""
    id: UUID
    user_id: UUID
    product_id: UUID
    created_at: str

    model_config = {"from_attributes": True}

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool
```

FastAPI validates request bodies automatically when type-annotated with Pydantic models. Invalid requests return 422 with detailed error messages.

### Custom Validators

```python
from pydantic import BaseModel, field_validator

class CreateUserRequest(BaseModel):
    email: str
    name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be 2-100 characters")
        return v.strip()
```

---

## Testing

### Unit Tests

Unit tests with pytest + mocks work the same as the base guide — no FastAPI-specific setup needed for service/repository tests.

### Integration Tests (TestClient)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

@pytest.fixture
async def auth_token(client: AsyncClient) -> str:
    """Get authentication token for tests."""
    response = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]

class TestFavoritesAPI:
    """Integration tests for Favorites API."""

    async def test_add_and_retrieve_favorite(self, client: AsyncClient, auth_token: str):
        """Test adding favorite and retrieving it."""
        add_response = await client.post(
            "/favorites",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"product_id": "550e8400-e29b-41d4-a716-446655440000"}
        )
        assert add_response.status_code == 201
        assert "id" in add_response.json()

        get_response = await client.get(
            "/favorites",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        favorites = get_response.json()["items"]
        assert len(favorites) == 1

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/favorites")
        assert response.status_code == 401
```

### Dependency Overrides (for mocking in integration tests)

```python
from app.main import app
from app.dependencies import get_user_service

@pytest.fixture
def mock_service():
    service = Mock(spec=UserService)
    service.create_user = AsyncMock(return_value=test_user())
    app.dependency_overrides[get_user_service] = lambda: service
    yield service
    app.dependency_overrides.clear()
```

---

## Security

### OAuth2 / JWT Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Extract and validate user from JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return await user_service.find_by_id(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Configuration

### Settings with Pydantic

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    database_url: str
    secret_key: str
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env"}

settings = Settings()
```

### Environment-Based Configuration

```
.env              # Local development (git-ignored)
.env.example      # Template committed to version control
```

---

## Build & Dependencies

### pyproject.toml

```toml
[project]
name = "my-service"
version = "1.0.0"
dependencies = [
    "fastapi>=0.110.0,<1.0.0",
    "uvicorn[standard]>=0.27.0,<1.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",
    "sqlalchemy[asyncio]>=2.0.0,<3.0.0",
    "python-jose[cryptography]>=3.3.0,<4.0.0",
    "bcrypt>=4.0.0,<5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
    "mypy",
    "black",
    "ruff",
]
```

### Common Commands

```bash
# Run development server
uvicorn app.main:app --reload --port 8000

# Run with production settings
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Common Files to Watch (Phase 4 Conflict Detection)

These FastAPI-specific files are frequently modified by multiple stories:
- `app/main.py` — router registration, middleware, lifespan
- `app/dependencies.py` — shared dependency injection functions
- `app/config.py` / `app/settings.py` — configuration
- `pyproject.toml` / `requirements.txt` — dependencies

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**Version History:**
- v1.0 (2026) - Initial FastAPI supplement (extracted from PYTHON-CODING-GUIDELINES.md and IMPLEMENTATION-PATTERNS.md)
