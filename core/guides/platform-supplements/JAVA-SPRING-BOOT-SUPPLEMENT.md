# Java Spring Boot Supplement

**Version:** 1.0  
**Last Updated:** 2026  
**Base Guide:** `JAVA-CODING-GUIDELINES.md` (load first)  
**Target:** Spring Boot 3.x projects. This supplement covers Spring-specific DI, testing, security, configuration, and build patterns.

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

### Constructor Injection (Preferred)

```java
@Service
public class UserService {
  private final UserRepository userRepository;
  private final PasswordEncoder passwordEncoder;
  private final EventPublisher eventPublisher;

  // Single constructor — @Autowired is optional when there's only one
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

### Stereotype Annotations

| Annotation | Use For |
|------------|---------|
| `@Service` | Business logic / use case classes |
| `@Repository` | Data access layer |
| `@Component` | General-purpose beans |
| `@Controller` / `@RestController` | Web layer |
| `@Configuration` | Bean definition classes |

**Rules:**
- Prefer constructor injection over field injection (`@Autowired` on fields)
- All dependencies should be `final`
- Avoid `@Autowired` — constructor injection makes it implicit when there is a single constructor
- Use `@Qualifier` only when multiple beans of the same type exist

---

## Architecture Patterns

### Repository Layer (Spring Data JPA)

```java
// Domain layer — interface (from base guide)
public interface UserRepository {
  Optional<User> findById(Long id);
  User save(User user);
  void deleteById(Long id);
  List<User> findByRole(String role);
}

// Infrastructure layer — Spring Data JPA implementation
@Repository
public class JpaUserRepository implements UserRepository {
  private final JpaUserEntityRepository jpaRepository;
  private final UserMapper mapper;

  public JpaUserRepository(JpaUserEntityRepository jpaRepository, UserMapper mapper) {
    this.jpaRepository = jpaRepository;
    this.mapper = mapper;
  }

  @Override
  public Optional<User> findById(Long id) {
    return jpaRepository.findById(id).map(mapper::toDomain);
  }

  @Override
  public User save(User user) {
    JpaUserEntity entity = mapper.toEntity(user);
    return mapper.toDomain(jpaRepository.save(entity));
  }
}

// Spring Data JPA interface (auto-implemented by Spring)
public interface JpaUserEntityRepository extends JpaRepository<JpaUserEntity, Long> {
  @Query("SELECT u FROM JpaUserEntity u WHERE u.email = :email")
  Optional<JpaUserEntity> findByEmail(@Param("email") String email);
}
```

### Controller Layer

```java
@RestController
@RequestMapping("/api/v1/users")
public class UserController {
  private final UserService userService;

  public UserController(UserService userService) {
    this.userService = userService;
  }

  @PostMapping
  public ResponseEntity<UserResponse> createUser(@Valid @RequestBody CreateUserRequest request) {
    User user = userService.createUser(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(UserResponse.from(user));
  }

  @GetMapping("/{id}")
  public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
    return userService.findById(id)
        .map(user -> ResponseEntity.ok(UserResponse.from(user)))
        .orElse(ResponseEntity.notFound().build());
  }
}
```

### Global Exception Handler

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(NotFoundException.class)
  public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(new ErrorResponse(ex.getErrorCode(), ex.getMessage()));
  }

  @ExceptionHandler(ValidationException.class)
  public ResponseEntity<ErrorResponse> handleValidation(ValidationException ex) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(new ErrorResponse(ex.getErrorCode(), ex.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<ErrorResponse> handleGeneral(Exception ex) {
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred"));
  }
}

public record ErrorResponse(String code, String message) {}
```

---

## Validation

### Jakarta Bean Validation (Spring Boot auto-integrates)

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

Use `@Valid` on controller method parameters to trigger validation:

```java
@PostMapping
public ResponseEntity<UserResponse> createUser(@Valid @RequestBody CreateUserRequest request) {
  // request is guaranteed to be valid here
}
```

---

## Testing

### Unit Tests

Unit tests with Mockito work the same as the base guide — no Spring-specific setup needed.

### Integration Tests

```java
@SpringBootTest
@Testcontainers
class UserRepositoryIntegrationTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

  @DynamicPropertySource
  static void configureProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired
  private UserRepository userRepository;

  @Test
  void shouldPersistAndRetrieveUser() {
    User saved = userRepository.save(new User("test@example.com", "Test User"));

    Optional<User> found = userRepository.findById(saved.getId());

    assertThat(found).isPresent();
    assertThat(found.get().getEmail()).isEqualTo("test@example.com");
  }
}
```

### Test Slices

| Annotation | What It Tests | What It Loads |
|------------|--------------|---------------|
| `@WebMvcTest` | Controllers only | Web layer (no service/repo beans) |
| `@DataJpaTest` | JPA repositories | Database layer with H2/Testcontainers |
| `@SpringBootTest` | Full application | Entire Spring context |

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

  @Autowired
  private MockMvc mockMvc;

  @MockitoBean
  private UserService userService;

  @Test
  void shouldReturn201WhenUserCreated() throws Exception {
    when(userService.createUser(any())).thenReturn(testUser());

    mockMvc.perform(post("/api/v1/users")
        .contentType(MediaType.APPLICATION_JSON)
        .content("""
            {"email": "test@example.com", "name": "Test User", "role": "USER"}
            """))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.email").value("test@example.com"));
  }
}
```

---

## Security

### Spring Security Configuration

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    return http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/api/v1/auth/**").permitAll()
            .requestMatchers("/actuator/health").permitAll()
            .anyRequest().authenticated()
        )
        .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .build();
  }

  @Bean
  public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder(12);
  }
}
```

### Secrets Management

```java
// application.yml properties
@Value("${app.api-key}")
private String apiKey;

// Vault integration
@VaultPropertySource("secret/myapp")
@Configuration
public class VaultConfig { }
```

---

## Configuration

### application.yml Conventions

```yaml
# Use kebab-case for property names
spring:
  application:
    name: my-service
  datasource:
    url: ${DATABASE_URL}
    username: ${DATABASE_USERNAME}
    password: ${DATABASE_PASSWORD}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      idle-timeout: 300000
      connection-timeout: 20000
      max-lifetime: 1200000
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
```

### Profile-Specific Configuration

```
src/main/resources/
├── application.yml           # Shared defaults
├── application-dev.yml       # Dev overrides
├── application-staging.yml   # Staging overrides
└── application-prod.yml      # Prod overrides
```

Activate with: `--spring.profiles.active=prod`

---

## Build & Dependencies

### Maven

```xml
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>3.3.0</version>
</parent>

<dependencies>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
  </dependency>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
  </dependency>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
  </dependency>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
  </dependency>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
  </dependency>
</dependencies>
```

### Gradle

```kotlin
plugins {
  id("org.springframework.boot") version "3.3.0"
  id("io.spring.dependency-management") version "1.1.5"
  java
}

dependencies {
  implementation("org.springframework.boot:spring-boot-starter-web")
  implementation("org.springframework.boot:spring-boot-starter-data-jpa")
  implementation("org.springframework.boot:spring-boot-starter-validation")
  implementation("org.springframework.boot:spring-boot-starter-security")
  testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```

### Common Files to Watch (Phase 4 Conflict Detection)

These Spring Boot-specific files are frequently modified by multiple stories:
- `Application.java` — main class
- `*Config.java` — Spring configuration classes
- `application.yml` / `application.properties`
- `pom.xml` / `build.gradle`

---

## References

- [Spring Boot Reference Documentation](https://docs.spring.io/spring-boot/docs/current/reference/html/)
- [Spring Security Reference](https://docs.spring.io/spring-security/reference/)
- [Spring Data JPA Reference](https://docs.spring.io/spring-data/jpa/docs/current/reference/html/)
- [Spring Boot Testing](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing)
- [Testcontainers for Spring Boot](https://java.testcontainers.org/modules/databases/jdbc/)

---

**Version History:**
- v1.0 (2026) - Initial Spring Boot supplement (extracted from JAVA-CODING-GUIDELINES.md)
