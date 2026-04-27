---
name: "Network-expert / App-dnss"
description: "Enterprise Specification: Domain Name System (DNS)"
layer: digital-generic-team
---
# Enterprise Specification: Domain Name System (DNS)

## 1. Purpose

Defines enterprise standards for name resolution.

---

## 2. Description

DNS translates human-readable domain names into IP addresses.

It is a hierarchical distributed system.

---

## 3. Typical Application Areas

- Web browsing
- Service discovery
- Internal infrastructure
- Email routing

---

## 4. Range

Global.

---

## 5. Speed

Very fast (cached lookup).

---

## 6. Possible Attack Vectors

- DNS spoofing
- Cache poisoning
- Amplification attacks
- Data exfiltration via DNS

---

## 7. Enterprise Requirements

- DNSSEC SHOULD be used
- Internal DNS MUST be separated
- Rate limiting MUST be applied
- Logging MUST be enabled

---

## 8. Python Example

```
import socket

ip = socket.gethostbyname("example.com")
print(ip)
```

---

## 9. Official Specifications

- RFC 1035
  https://www.rfc-editor.org/rfc/rfc1035.html

---

## 10. Summary

DNS is critical infrastructure and must be secured and monitored carefully.