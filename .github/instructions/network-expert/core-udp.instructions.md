---
name: "Network-expert / Core-udps"
description: "Enterprise Specification: User Datagram Protocol (UDP)"
layer: digital-generic-team
---
# Enterprise Specification: User Datagram Protocol (UDP)

## 1. Purpose

Defines the enterprise usage of connectionless, low-latency communication.

---

## 2. Description

UDP is a lightweight transport protocol that provides:

- No connection setup
- No reliability guarantees
- No ordering guarantees

It is optimized for speed and low overhead.

---

## 3. Typical Application Areas

- Streaming
- DNS
- VoIP
- Gaming
- Real-time telemetry

---

## 4. Range

Global (via IP).

---

## 5. Speed

Very high (low overhead).

---

## 6. Possible Attack Vectors

- UDP flood attacks
- Amplification attacks (e.g., DNS)
- Packet spoofing

---

## 7. Enterprise Requirements

- Rate limiting MUST be applied
- Exposure MUST be minimized
- Protocol-specific protections SHOULD be implemented

---

## 8. Python Example

Server

```
import socket

HOST = "0.0.0.0"
PORT = 8001

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind((HOST, PORT))
    data, addr = s.recvfrom(1024)
    print("Received:", data.decode())
    s.sendto(b"udp response", addr)
```

Client

```
import socket

HOST = "127.0.0.1"
PORT = 8001

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(b"udp request", (HOST, PORT))
    data, _ = s.recvfrom(1024)
    print(data.decode())
```

---

## 9. Official Specifications

- RFC 768: https://www.rfc-editor.org/rfc/rfc768.html

---

## 10. Summary

UDP is ideal for real-time and low-latency applications but requires higher-level protocols for reliability and security.