---
name: "Quality-expert / Cleancodes"
description: "Clean Code Guidelines (Enterprise Specification)"
layer: digital-generic-team
---
# Clean Code Guidelines (Enterprise Specification)


**Purpose:**
This document defines mandatory clean coding rules for this repository.
All contributors and AI code assistants must follow these guidelines.

These standards are derived from principles described in *Clean Code* by Robert C. Martin.

---

# 1. Core Philosophy

## 1.1 Readable Code First

Code must prioritize readability and maintainability over cleverness.

**Rules**

* Prefer clear code over compact code.
* Avoid unnecessary abstraction.
* Code should read like natural language.

**Bad**

```python
x=f(a,b,c)
```

**Good**

```python
invoice_total = calculate_invoice_total(items, tax_rate, discounts)
```

---

## 1.2 Single Responsibility Principle

Every unit of code must have **one responsibility**.

Applies to:

* functions
* classes
* modules
* services

**Bad**

```python
def process_order(order):
    validate(order)
    save(order)
    send_email(order)
```

**Good**

```python
def process_order(order):
    validate_order(order)
    persist_order(order)
```

---

# 2. Naming Conventions

Names must clearly describe intent.

## 2.1 Variables

Rules:

* Avoid abbreviations
* Avoid single-letter names (except loop counters)
* Use domain language

**Bad**

```python
d = 86400
```

**Good**

```python
seconds_per_day = 86400
```

---

## 2.2 Functions

Functions must describe **actions**.

Preferred naming pattern:

```
verb + domain_object
```

Examples:

```
calculate_total()
validate_request()
load_configuration()
build_quantum_circuit()
```

Avoid vague names:

```
process()
handle()
run()
data()
```

---

## 2.3 Classes

Classes represent **entities or concepts**.

Good examples:

```
OrderRepository
CacheManager
QuantumCircuitBuilder
GeneExpressionAnalyzer
```

Avoid meaningless names:

```
Helper
Utils
Manager
Processor
```

---

# 3. Function Design

## 3.1 Small Functions

Functions must remain small.

Recommended:

```
< 20 lines
```

Maximum:

```
50 lines
```

If exceeded:

* extract methods
* create helper classes
* split responsibilities

---

## 3.2 Parameter Limits

Functions should have minimal parameters.

Recommended:

```
0–2 parameters
```

Acceptable:

```
3 parameters
```

Avoid:

```
4+ parameters
```

Use a parameter object instead.

**Bad**

```python
create_user(name, age, city, email, role)
```

**Good**

```python
create_user(user_data)
```

---

## 3.3 Avoid Side Effects

Functions must avoid hidden state changes.

**Bad**

```python
def calculate_total(cart):
    global tax_rate
```

**Good**

```python
def calculate_total(cart, tax_rate):
```

---

# 4. Comments

Comments must explain **why**, not **what**.

**Bad**

```python
# increment counter
counter += 1
```

**Good**

```python
# retry counter for API requests
retry_count += 1
```

Prefer **self-documenting code** instead of comments.

---

# 5. Error Handling

Use exceptions instead of error codes.

**Bad**

```python
if result == -1:
    return False
```

**Good**

```python
if not user_exists:
    raise UserNotFoundError()
```

---

## 5.1 Avoid Null Returns

Prefer:

* empty objects
* optionals
* exceptions

Avoid returning `null` or `None` unless necessary.

---

# 6. Testing Standards

Every feature must include tests.

Tests must be:

* deterministic
* independent
* readable

Recommended structure:

```
Arrange
Act
Assert
```

Example:

```python
def test_calculate_total():
    cart = Cart(items=[Item(price=10)])

    total = calculate_total(cart)

    assert total == 10
```

---

# 7. Duplication

Code duplication must be eliminated.

Common duplication sources:

* copy-paste code
* repeated logic
* repeated algorithms

Solutions:

* extract functions
* shared modules
* abstraction

---

# 8. Complexity Limits

Maximum allowed:

```
Cyclomatic complexity ≤ 10
```

Maximum nesting:

```
3 levels
```

Bad example:

```python
if a:
    if b:
        if c:
            if d:
```

Refactor using guard clauses.

---

# 9. Refactoring Rules

Refactor immediately when:

* function length exceeds limits
* naming is unclear
* duplication appears
* nesting depth exceeds limits

Refactoring must not change behavior.

---

# 10. Architecture Guidelines

Recommended architecture layers:

```
Domain
Application
Infrastructure
Interface
```

Dependencies must always point **inward**.

Business logic must never depend on infrastructure.

---

# 11. Pull Request Requirements

Every pull request must include:

* clear description
* linked issue
* tests (if applicable)
* clean commit history

Example commit message:

```
feat: implement quantum circuit optimizer
```

---

# 12. AI Assistant Requirements

AI tools generating code must:

* follow naming conventions
* generate small functions
* avoid duplication
* respect repository architecture
* include tests when appropriate

Generated code must be reviewed before merge.

---

# 13. Definition of Done

A feature is complete only when:

* code passes CI
* tests exist
* naming is clear
* no obvious duplication remains
* clean architecture is preserved

---

# 14. Enforcement

These guidelines are enforced through:

* pull request reviews
* static analysis
* linters
* automated CI checks

Non-compliant code must be refactored before merge.
