---
name: "Network-expert / App-https"
description: "Enterprise Specification: HTTP / HTTPS Protocol"
layer: digital-generic-team
---
# Enterprise Specification: HTTP / HTTPS Protocol

## 1. Purpose

Defines the enterprise standard for web communication and API transport.

---

## 2. Description

HTTP (Hypertext Transfer Protocol) is an application-layer protocol for request/response communication.

HTTPS = HTTP over TLS (encrypted).

Key characteristics:

- Stateless
- Client-server model
- Widely used for APIs and web applications

---

## 3. Typical Application Areas

- Web applications
- REST APIs
- Microservices communication
- File transfer (via HTTP)
- Cloud services

---

## 4. Range

Global (via TCP/IP or QUIC).

---

## 5. Speed

Medium to very high.

Depends on:

- HTTP version (1.1, 2, 3)
- Transport (TCP vs QUIC)
- Payload size

---

## 6. Possible Attack Vectors

- Man-in-the-middle (MITM)
- Injection attacks
- Header manipulation
- Session hijacking
- TLS misconfiguration

---

## 7. Enterprise Requirements

- HTTPS MUST be used
- TLS 1.2+ REQUIRED (prefer 1.3)
- Headers MUST be validated
- Input MUST be sanitized
- Authentication MUST be enforced

---

## 8. Python Example

Server

```
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"hello http")

server = HTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever()
```

Client

```
import requests

r = requests.get("http://localhost:8080")
print(r.text)
```

---

## 9. Official Specifications

- RFC 9110 (HTTP Semantics)
  https://www.rfc-editor.org/rfc/rfc9110.html

---

## 10. Summary

HTTP(S) is the dominant protocol for modern applications and APIs, forming the backbone of web-based systems.