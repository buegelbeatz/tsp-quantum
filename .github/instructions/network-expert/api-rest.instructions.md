---
name: "Network-expert / Api-rests"
description: "Enterprise Specification: REST API Style"
layer: digital-generic-team
---
# Enterprise Specification: REST API Style

## 1. Purpose

Defines the enterprise standard for RESTful API design and communication.

---

## 2. Description

REST (Representational State Transfer) is an architectural style for designing networked applications.

Key principles:

- Stateless communication
- Resource-based design
- Standard HTTP methods
- Uniform interface

---

## 3. Core Concepts

- Resources (identified by URLs)
- Representations (JSON, XML)
- HTTP methods:
  - GET (read)
  - POST (create)
  - PUT (update)
  - DELETE (remove)

---

## 4. Typical Application Areas

- Web APIs
- Microservices
- Public APIs
- Mobile backends

---

## 5. Advantages

- Simple and widely understood
- Scalable
- Cacheable
- Language agnostic

---

## 6. Possible Attack Vectors

- Injection attacks
- Broken authentication
- Overexposed endpoints
- Rate abuse
- Insecure serialization

---

## 7. Enterprise Requirements

- HTTPS MUST be used
- JSON SHOULD be preferred
- Versioning MUST be implemented
- Authentication REQUIRED (OAuth2/JWT)
- Rate limiting MUST be enforced
- Input validation REQUIRED

---

## 8. Example

```
GET /api/v1/users/123
Authorization: Bearer <token>
```

---

## 9. Official References

- RFC 9110 (HTTP)
  https://www.rfc-editor.org/rfc/rfc9110.html

---

## 10. Summary

REST is the default standard for enterprise APIs due to simplicity and scalability.