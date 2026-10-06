# Java Quarkus Supplement

**Version:** 1.0  
**Last Updated:** 2026  
**Base Guide:** `JAVA-CODING-GUIDELINES.md` (load first)  
**Target:** Quarkus 3.x projects. This supplement covers Quarkus-specific CDI, testing, security, configuration, and build patterns.

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

### CDI (Contexts and Dependency Injection)

Quarkus uses CDI (Jakarta CDI / ArC) for dependency injection.

```java
@ApplicationScoped
public class UserService {
  private final UserRepository userRepository;
  private final PasswordEncoder passwordEncoder;
  private final EventPublisher eventPublisher;

  @Inject
  public UserService(
      UserRepository userRepository,
      PasswordEncoder passwordEncoder,
      EventPublisher eventPublisher) {
    this.userRepository = userRepository;
    this.passwordEncoder = passwordEncoder;
    this.eventPublisher = eventPublisher;
  }
}
```

### CDI Scopes

| Scope | Annotation | Use For |
|-------|-----------|---------|
| Application | `@ApplicationScoped` | Singleton-like beans (services, repositories) |
| Request | `@RequestScoped` | Per-HTTP-request beans |
| Dependent | `@Dependent` | New instance per injection point (default if no scope) |
| Singleton | `@Singleton` | True singleton (no proxy, not passivation-capable) |

**Rules:**
- Prefer `@ApplicationScoped` for service and repository beans
- Use `@Inject` on constructors (required when more than one constructor exists)
- All dependencies should be `final`
- Quarkus uses build-time CDI (ArC) — not all CDI features from full servers are available
- Avoid `@Produces` on fields; use producer methods

---

## Architecture Patterns

### Repository Layer (Hibernate ORM with Panache)

```java
// Domain layer — interface (from base guide)
public interface UserRepository {
  Optional<User> findById(Long id);
  User save(User user);
  void deleteById(Long id);
  List<User> findByRole(String role);
}

// Infrastructure layer — Panache-based implementation
@ApplicationScoped
public class PanacheUserRepository implements UserRepository {
  private final UserMapper mapper;

  @Inject
  public PanacheUserRepository(UserMapper mapper) {
    this.mapper = mapper;
  }

  @Override
  @Transactional
  public Optional<User> findById(Long id) {
    return UserEntity.findByIdOptional(id).map(e -> mapper.toDomain((UserEntity) e));
  }

  @Override
  @Transactional
  public User save(User user) {
    UserEntity entity = mapper.toEntity(user);
    entity.persist();
    return mapper.toDomain(entity);
  }

  @Override
  @Transactional
  public List<User> findByRole(String role) {
    return UserEntity.<UserEntity>find("role", role)
        .stream()
        .map(mapper::toDomain)
        .toList();
  }
}

// Panache entity (Active Record pattern)
@Entity
@Table(name = "users")
public class UserEntity extends PanacheEntity {
  @Column(nullable = false, unique = true)
  public String email;

  @Column(nullable = false)
  public String name;

  @Column(nullable = false)
  public String role;
}
```

**Alternative: Panache Repository pattern (if you prefer the Repository pattern over Active Record):**

```java
@ApplicationScoped
public class UserEntityRepository implements PanacheRepository<UserEntity> {
  public Optional<UserEntity> findByEmail(String email) {
    return find("email", email).firstResultOptional();
  }
}
```

### RESTEasy Reactive (JAX-RS) Controller

```java
@Path("/api/v1/users")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
@ApplicationScoped
public class UserResource {
  private final UserService userService;

  @Inject
  public UserResource(UserService userService) {
    this.userService = userService;
  }

  @POST
  public Response createUser(@Valid CreateUserRequest request) {
    User user = userService.createUser(request);
    return Response.status(Response.Status.CREATED)
        .entity(UserResponse.from(user))
        .build();
  }

  @GET
  @Path("/{id}")
  public Response getUser(@PathParam("id") Long id) {
    return userService.findById(id)
        .map(user -> Response.ok(UserResponse.from(user)).build())
        .orElse(Response.status(Response.Status.NOT_FOUND).build());
  }
}
```

### Exception Mapper (Global Error Handling)

```java
@Provider
public class NotFoundExceptionMapper implements ExceptionMapper<NotFoundException> {

  @Override
  public Response toResponse(NotFoundException exception) {
    return Response.status(Response.Status.NOT_FOUND)
        .entity(new ErrorResponse(exception.getErrorCode(), exception.getMessage()))
        .build();
  }
}

@Provider
public class ValidationExceptionMapper implements ExceptionMapper<ValidationException> {

  @Override
  public Response toResponse(ValidationException exception) {
    return Response.status(Response.Status.BAD_REQUEST)
        .entity(new ErrorResponse(exception.getErrorCode(), exception.getMessage()))
        .build();
  }
}
```

---

## Validation

### Hibernate Validator (Jakarta Bean Validation)

```java
import jakarta.validation.constraints.*;

public record CreateUserRequest(
    @NotBlank @Email
    String email,

    @NotBlank @Size(min = 2, max = 100)
    @Pattern(regexp = "^[a-zA-Z\\s'-]+$", message = "Name contains invalid characters")
    String name,

    @NotNull
    Role role
) {}
```

Use `@Valid` on resource method parameters:

```java
@POST
public Response createUser(@Valid CreateUserRequest request) {
  // request is guaranteed to be valid here
}
```

---

## Testing

### Unit Tests

Unit tests with JUnit 5 + Mockito + AssertJ work the same as the base guide — no Quarkus-specific setup needed.

### Integration Tests

```java
@QuarkusTest
class UserResourceTest {

  @Test
  void shouldCreateUser() {
    given()
        .contentType(ContentType.JSON)
        .body("""
            {"email": "test@example.com", "name": "Test User", "role": "USER"}
            """)
        .when()
        .post("/api/v1/users")
        .then()
        .statusCode(201)
        .body("email", is("test@example.com"));
  }

  @Test
  void shouldReturn404ForMissingUser() {
    given()
        .when()
        .get("/api/v1/users/9999")
        .then()
        .statusCode(404);
  }
}
```

### Test with Database (Dev Services)

Quarkus Dev Services automatically starts test containers for databases, Kafka, Redis, etc. — no manual container setup needed.

```java
@QuarkusTest
@TestProfile(TestDatabaseProfile.class)
class UserRepositoryIntegrationTest {

  @Inject
  UserRepository userRepository;

  @Test
  @Transactional
  void shouldPersistAndRetrieveUser() {
    User saved = userRepository.save(new User("test@example.com", "Test User"));

    Optional<User> found = userRepository.findById(saved.getId());

    assertThat(found).isPresent();
    assertThat(found.get().getEmail()).isEqualTo("test@example.com");
  }
}
```

**Dev Services configuration** (no explicit container setup needed — Quarkus starts PostgreSQL automatically when `quarkus-jdbc-postgresql` is on the classpath):

```properties
# application.properties (test profile uses Dev Services by default)
%test.quarkus.datasource.devservices.enabled=true
%test.quarkus.datasource.devservices.image-name=postgres:16
```

### Native Mode Testing

```java
@QuarkusIntegrationTest
class UserResourceIT {
  // Same tests as @QuarkusTest but runs against the native executable
  // or the packaged JAR (depending on build profile)
}
```

### Mocking in Quarkus Tests

```java
@QuarkusTest
class UserResourceTest {

  @InjectMock
  UserService userService;

  @Test
  void shouldReturn201WhenUserCreated() {
    when(userService.createUser(any())).thenReturn(testUser());

    given()
        .contentType(ContentType.JSON)
        .body("""
            {"email": "test@example.com", "name": "Test User", "role": "USER"}
            """)
        .when()
        .post("/api/v1/users")
        .then()
        .statusCode(201);
  }
}
```

---

## Security

### Quarkus Security Configuration

```java
// Use annotations for method-level security
@Path("/api/v1/users")
@ApplicationScoped
public class UserResource {

  @GET
  @RolesAllowed("admin")
  public List<UserResponse> listUsers() {
    return userService.findAll();
  }

  @GET
  @Path("/me")
  @Authenticated
  public UserResponse getCurrentUser(@Context SecurityContext securityContext) {
    String userId = securityContext.getUserPrincipal().getName();
    return userService.findById(Long.parseLong(userId));
  }
}
```

**application.properties for security:**

```properties
# OIDC (Keycloak, Auth0, etc.)
quarkus.oidc.auth-server-url=https://auth.example.com/realms/myapp
quarkus.oidc.client-id=my-service
quarkus.oidc.credentials.secret=${OIDC_CLIENT_SECRET}

# HTTP policy
quarkus.http.auth.permission."public".paths=/api/v1/auth/*,/q/health
quarkus.http.auth.permission."public".policy=permit
quarkus.http.auth.permission."authenticated".paths=/api/*
quarkus.http.auth.permission."authenticated".policy=authenticated
```

### Password Hashing

```java
import io.quarkus.elytron.security.common.BcryptUtil;

public class PasswordService {
  public String hashPassword(String rawPassword) {
    return BcryptUtil.bcryptHash(rawPassword);
  }

  public boolean verifyPassword(String rawPassword, String hashedPassword) {
    return BcryptUtil.matches(rawPassword, hashedPassword);
  }
}
```

### Secrets Management

```java
// MicroProfile Config (environment variables, application.properties, config maps)
@ConfigProperty(name = "app.api-key")
String apiKey;

// Vault integration
// quarkus.vault.url=https://vault.example.com
// quarkus.vault.authentication.userpass.username=myapp
@ConfigProperty(name = "vault.api-key")
String vaultApiKey;
```

---

## Configuration

### application.properties Conventions

```properties
# Use dot-separated lowercase names (MicroProfile Config standard)
quarkus.http.port=8080

# Datasource
quarkus.datasource.db-kind=postgresql
quarkus.datasource.jdbc.url=${DATABASE_URL:jdbc:postgresql://localhost:5432/mydb}
quarkus.datasource.username=${DATABASE_USERNAME:postgres}
quarkus.datasource.password=${DATABASE_PASSWORD:postgres}
quarkus.datasource.jdbc.max-size=20
quarkus.datasource.jdbc.min-size=5

# Hibernate ORM
quarkus.hibernate-orm.database.generation=validate
quarkus.hibernate-orm.log.sql=false

# Flyway migrations
quarkus.flyway.migrate-at-start=true
```

### Profile-Specific Configuration

```properties
# Default values (all profiles)
quarkus.http.port=8080

# Dev profile overrides
%dev.quarkus.datasource.jdbc.url=jdbc:postgresql://localhost:5432/mydb_dev
%dev.quarkus.log.level=DEBUG

# Test profile overrides
%test.quarkus.datasource.devservices.enabled=true

# Prod profile overrides
%prod.quarkus.datasource.jdbc.url=${DATABASE_URL}
%prod.quarkus.log.level=INFO
```

Activate with: `-Dquarkus.profile=prod` or `QUARKUS_PROFILE=prod`

---

## Build & Dependencies

### Maven

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>io.quarkus.platform</groupId>
      <artifactId>quarkus-bom</artifactId>
      <version>3.8.0</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>

<dependencies>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-resteasy-reactive-jackson</artifactId>
  </dependency>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-hibernate-orm-panache</artifactId>
  </dependency>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-hibernate-validator</artifactId>
  </dependency>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-jdbc-postgresql</artifactId>
  </dependency>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-oidc</artifactId>
  </dependency>
  <dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-junit5</artifactId>
    <scope>test</scope>
  </dependency>
  <dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <scope>test</scope>
  </dependency>
</dependencies>

<build>
  <plugins>
    <plugin>
      <groupId>io.quarkus.platform</groupId>
      <artifactId>quarkus-maven-plugin</artifactId>
      <version>3.8.0</version>
      <extensions>true</extensions>
      <executions>
        <execution>
          <goals>
            <goal>build</goal>
            <goal>generate-code</goal>
          </goals>
        </execution>
      </executions>
    </plugin>
  </plugins>
</build>
```

### Gradle

```kotlin
plugins {
  id("io.quarkus") version "3.8.0"
  java
}

dependencies {
  implementation(enforcedPlatform("io.quarkus.platform:quarkus-bom:3.8.0"))
  implementation("io.quarkus:quarkus-resteasy-reactive-jackson")
  implementation("io.quarkus:quarkus-hibernate-orm-panache")
  implementation("io.quarkus:quarkus-hibernate-validator")
  implementation("io.quarkus:quarkus-jdbc-postgresql")
  implementation("io.quarkus:quarkus-oidc")
  testImplementation("io.quarkus:quarkus-junit5")
  testImplementation("io.rest-assured:rest-assured")
}
```

### Common Commands

```bash
# Dev mode (live reload)
./mvnw quarkus:dev
# or
./gradlew quarkusDev

# Run tests
./mvnw test

# Build JAR
./mvnw package

# Build native executable
./mvnw package -Dnative

# Add extension
./mvnw quarkus:add-extension -Dextensions="hibernate-orm-panache"
```

### Common Files to Watch (Phase 4 Conflict Detection)

These Quarkus-specific files are frequently modified by multiple stories:
- `application.properties` — centralized config
- `pom.xml` / `build.gradle` — dependencies
- Resource classes with `@Path` annotations — route registration is implicit, but shared paths conflict

---

## References

- [Quarkus Guides](https://quarkus.io/guides/)
- [Quarkus CDI Reference](https://quarkus.io/guides/cdi-reference)
- [RESTEasy Reactive Guide](https://quarkus.io/guides/resteasy-reactive)
- [Hibernate ORM with Panache](https://quarkus.io/guides/hibernate-orm-panache)
- [Quarkus Testing Guide](https://quarkus.io/guides/getting-started-testing)
- [Quarkus Security](https://quarkus.io/guides/security-overview)
- [Quarkus Dev Services](https://quarkus.io/guides/dev-services)

---

**Version History:**
- v1.0 (2026) - Initial Quarkus supplement
