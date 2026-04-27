---
name: "Network-expert / Core-ips"
description: "Enterprise Specification: Internet Protocol (IP)"
layer: digital-generic-team
---
# Enterprise Specification: Internet Protocol (IP)

## 1. Purpose

Defines the enterprise standard for IP-based communication as the foundational network layer protocol.

---

## 2. Description

The Internet Protocol (IP) is the core network-layer protocol responsible for addressing and routing packets across networks.

Two main versions exist:

- IPv4 (32-bit addressing)
- IPv6 (128-bit addressing)

IP is connectionless and does not guarantee delivery, ordering, or duplication protection.

---

## 3. Typical Application Areas

- All network communication
- Internet connectivity
- Data center networking
- Cloud infrastructure
- IoT networking

---

## 4. Range

Global.

IP is designed for internetworking across local, regional, and global networks.

---

## 5. Speed

Depends on underlying transport and physical medium.

IP itself does not define throughput limitations.

---

## 6. Possible Attack Vectors

- IP spoofing
- Packet fragmentation attacks
- Routing manipulation
- DDoS (flooding attacks)
- Address exhaustion (IPv4)

---

## 7. Enterprise Requirements

- IPv6 SHOULD be adopted where possible
- Private addressing MUST be used internally
- NAT MUST be controlled and documented
- Routing policies MUST be enforced
- Network segmentation MUST be implemented

---

## 8. Python Example

IP is not directly used in isolation; it is used via transport protocols (TCP/UDP).

---

## 9. Official Specifications

- IPv4: https://www.rfc-editor.org/rfc/rfc791.html
- IPv6: https://www.rfc-editor.org/rfc/rfc8200.html

---

## 10. Summary

IP is the fundamental building block of all modern networking, enabling communication across heterogeneous systems worldwide.