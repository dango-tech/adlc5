## Part IV — Head First Design Patterns

*Source: Freeman & Robson, O'Reilly (~650 pp.).*

### IV.1 Core message

Patterns are a **shared vocabulary** for recurring **design** problems. Learn **principles first**, then patterns. Problems don't announce which pattern applies—you need judgment.

### IV.2 Design principles (use on every design task)

1. **Encapsulate what varies**
2. **Favor composition over inheritance**
3. **Program to an interface, not an implementation**
4. **Strive for loosely coupled designs**
5. **Open for extension, closed for modification**
6. **Only talk to your friends** (Law of Demeter / least knowledge)
7. **Single responsibility**

### IV.3 GoF patterns — when to use

| Pattern | Problem | Often confused with |
|---------|---------|---------------------|
| **Strategy** | Interchangeable algorithms/behaviors | Many if/else; **pair with CLRS for which algorithm** |
| **Observer** | One-to-many state notification | Polling; event bus (different scale) |
| **Decorator** | Add behavior without subclass explosion | Inheritance chain |
| **Factory Method** | Subclass decides object type | `new` scattered |
| **Abstract Factory** | Families of related products | Factory Method |
| **Singleton** | Exactly one instance | Global state abuse—use sparingly |
| **Command** | Encapsulate request as object | Undo, queues, macros |
| **Adapter** | Legacy/incompatible interface | Facade (simplifies many) |
| **Facade** | Simple interface to subsystem | Adapter (one class) |
| **Template Method** | Algorithm skeleton, steps vary | Strategy (composition vs inheritance) |
| **Iterator** | Sequential access without exposing structure | Index loops |
| **Composite** | Tree: treat part and whole uniformly | Deep nesting without discipline |
| **State** | Behavior changes with internal state | Large switch on type |
| **Proxy** | Control access, lazy load, remote | Decorator (adds behavior) |

### IV.4 Pattern selection prompts (for agents)

| If the problem is… | Consider… |
|--------------------|-----------|
| Many algorithms for same job | Strategy |
| UI/widgets reacting to model | Observer |
| Add features to object at runtime | Decorator |
| Hide complex subsystem | Facade |
| Object creation is messy | Factory / Builder |
| Tree structures (UI, org, AST) | Composite |
| Mode-dependent behavior | State |
| Cross-cutting request handling | Chain of Responsibility / Decorator |

### IV.5 HFDP ↔ PBE ↔ CLRS

| Layer | Role |
|-------|------|
| **HFDP** | *What shape* the code has (Strategy interface) |
| **CLRS** | *What algorithm* each strategy runs (O(n log n) sort) |
| **PBE** | *Org asset* when the whole shape+scaffold repeats across projects |

GoF patterns are **community specifications**. Add to **org catalog** only when Rule of Three + ROI apply.

---

