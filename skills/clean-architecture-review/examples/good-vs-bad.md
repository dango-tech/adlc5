# S2 — Good vs Bad Architecture Examples

## Dependency direction

### Bad

Use case imports ORM entity and HTTP types:

```java
// application/CreateOrderUseCase.java
import org.springframework.web.bind.annotation.*;
import jakarta.persistence.EntityManager;

public class CreateOrderUseCase {
  @Autowired EntityManager em;
}
```

### Good

Use case depends on port; adapter implements persistence:

```java
// application/CreateOrderUseCase.java
public class CreateOrderUseCase {
  private final OrderRepository orders;
  public OrderId execute(CreateOrderCommand cmd) { ... }
}
```

---

## Folder layout (screaming architecture)

### Bad

```
src/
  controllers/
  services/
  models/
  repositories/
```

Technology buckets only — use cases hidden.

### Good

```
src/
  place_order/
    PlaceOrderUseCase.java
    PlaceOrderController.java
  cancel_order/
    ...
```

---

## Review comment

### Bad

> "Architecture looks wrong."

### Good

> **high / dependency rule** — `CreateOrderUseCase` imports `jakarta.persistence.EntityManager` (line 4). Introduce `OrderRepository` port in application layer; implement in `infrastructure/persistence`.
