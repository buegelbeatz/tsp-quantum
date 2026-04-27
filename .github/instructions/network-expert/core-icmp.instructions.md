---
name: "Network-expert / Core-icmps"
description: "Enterprise Specification: Internet Control Message Protocol (ICMP)"
layer: digital-generic-team
---
# Enterprise Specification: Internet Control Message Protocol (ICMP)

## 1. Purpose

Defines enterprise usage of ICMP for diagnostics and network control.

---

## 2. Description

ICMP is used for:

- Error reporting
- Network diagnostics
- Reachability testing

Examples:

- Ping
- Traceroute

---

## 3. Typical Application Areas

- Network troubleshooting
- Monitoring
- Routing diagnostics

---

## 4. Range

Global (via IP).

---

## 5. Speed

Minimal data usage; not designed for throughput.

---

## 6. Possible Attack Vectors

- ICMP flood (DoS)
- Ping of death
- Network reconnaissance

---

## 7. Enterprise Requirements

- ICMP SHOULD be rate-limited
- External ICMP MAY be restricted
- Internal diagnostics MUST remain functional

---

## 8. Python Example

ICMP requires raw sockets (admin privileges).

---

## 9. Official Specifications

- RFC 792: https://www.rfc-editor.org/rfc/rfc792.html

---

## 10. Summary

ICMP is essential for diagnostics but must be carefully controlled to prevent abuse.