---
name: "Network-expert / Core-tcps"
description: "Enterprise Specification: Transmission Control Protocol (TCP)"
layer: digital-generic-team
---
# Enterprise Specification: Transmission Control Protocol (TCP)

## 1. Purpose

Defines the enterprise standard for reliable, connection-oriented transport communication.

---

## 2. Description

TCP is a transport-layer protocol providing:

- Reliable delivery
- Ordered data transfer
- Congestion control
- Flow control

TCP establishes a connection using a three-way handshake.

---

## 3. Typical Application Areas

- Web (HTTP/HTTPS)
- File transfer
- Databases
- APIs
- SSH and remote access

---

## 4. Range

Global (depends on IP).

---

## 5. Speed

Medium to high.

Overhead exists due to:

- Handshake
- Acknowledgments
- Retransmissions
- Congestion control

---

## 6. Possible Attack Vectors

- SYN flood (DoS)
- Session hijacking
- Reset attacks
- Packet injection

---

## 7. Enterprise Requirements

- TLS MUST be used on top of TCP for sensitive data
- Connection limits MUST be enforced
- Firewalls MUST control access
- Timeouts and retries MUST be configured

---

## 8. Python Example

Server

```
import socket

HOST = "0.0.0.0"
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        data = conn.recv(1024)
        conn.sendall(b"tcp response")
```

Client

```
import socket

HOST = "127.0.0.1"
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b"tcp request")
    print(s.recv(1024).decode())
```

---

## 9. Official Specifications

- RFC 9293: https://www.rfc-editor.org/rfc/rfc9293.html

---

## 10. Summary

TCP is the standard for reliable communication, forming the backbone of most enterprise services and applications.