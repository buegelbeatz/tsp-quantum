---
name: "Network-expert / Connectivity-wifis"
description: "Enterprise Specification: Wi-Fi Connectivity Standard"
layer: digital-generic-team
---
# Enterprise Specification: Wi-Fi Connectivity Standard

## 1. Purpose

This document defines the enterprise standard for Wi-Fi (Wireless Local Area Network) connectivity, including its design, usage, security, and operational constraints.

The goal is to ensure reliable, secure, and scalable wireless communication across enterprise environments.

---

## 2. Description

Wi-Fi is a wireless networking technology based on the IEEE 802.11 family of standards. It enables devices to communicate over radio frequencies without physical cabling.

Wi-Fi operates primarily in the following frequency bands:

- 2.4 GHz (longer range, more interference)
- 5 GHz (higher throughput, lower range)
- 6 GHz (Wi-Fi 6E / Wi-Fi 7, high performance, lower congestion)

It is the dominant technology for local wireless networking in enterprise, consumer, and IoT environments.

---

## 3. Typical Application Areas

- Enterprise office networking
- Campus and large building deployments
- Public hotspots (airports, hotels, cafes)
- Home networking
- IoT devices with moderate to high bandwidth requirements
- Mobile device connectivity (laptops, phones, tablets)

---

## 4. Range

Wi-Fi is classified as a **short- to medium-range wireless technology**.

Typical influencing factors:

- Frequency band (2.4 GHz > 5 GHz > 6 GHz in range)
- Building materials (walls, metal, glass)
- Interference from other networks/devices
- Access point density and placement
- Antenna design and transmit power

Enterprise deployments MUST rely on **site surveys and RF planning**, not theoretical range values.

---

## 5. Speed

Wi-Fi provides **medium to very high throughput**, depending on:

- Wi-Fi standard (e.g., 802.11n/ac/ax/be)
- Channel width (20–320 MHz)
- MIMO capabilities
- Signal quality and interference
- Number of concurrent users

Important:

- Real-world throughput is significantly lower than theoretical PHY rates
- Performance degrades with congestion and distance

---

## 6. Possible Attack Vectors

Wi-Fi networks are exposed to multiple attack surfaces:

### Network-Level Attacks
- Rogue access points
- Evil twin attacks (fake AP impersonation)
- Deauthentication / disassociation attacks
- Traffic sniffing on unsecured networks

### Authentication Attacks
- Weak passwords (PSK brute force)
- Credential theft in captive portals
- Misconfigured enterprise authentication (EAP)

### Protocol / Configuration Weaknesses
- Legacy protocols (WEP, WPA)
- Downgrade attacks
- Improper VLAN segmentation
- Lack of management frame protection

---

## 7. Enterprise Requirements

### Security
- WPA3 MUST be used where supported
- WPA2 MUST be hardened if fallback is required
- Protected Management Frames (PMF) SHOULD be enabled
- 802.1X authentication SHOULD be used for enterprise networks

### Network Design
- Separate SSIDs for:
  - Employees
  - Guests
  - IoT devices
- VLAN segmentation MUST be enforced

### Operations
- Regular RF site surveys REQUIRED
- Access point placement MUST be planned centrally
- Monitoring and intrusion detection SHOULD be implemented

---

## 8. Python Example

Wi-Fi itself is a transport medium. Communication occurs over IP (TCP/UDP).

### 8.1 Mini Server

```
import socket

HOST = "0.0.0.0"
PORT = 9000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind((HOST, PORT))
    server.listen()
    print(f"Listening on {HOST}:{PORT}")

    conn, addr = server.accept()
    with conn:
        print("Connected:", addr)
        data = conn.recv(1024)
        print("Received:", data.decode())
        conn.sendall(b"hello from wifi server")
```

### 8.2 Mini Client

```
import socket

HOST = "127.0.0.1"  # replace with server IP
PORT = 9000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
    client.connect((HOST, PORT))
    client.sendall(b"hello from wifi client")
    data = client.recv(1024)
    print("Server replied:", data.decode())
```

---

## 9. Official Specifications

- IEEE 802.11: https://www.ieee802.org/11/
- Wi-Fi Alliance: https://www.wi-fi.org/

---

## 10. RFC References

Wi-Fi itself is not defined by a single RFC.

Relevant related RFC:

- RFC 7241 (IEEE / IETF relationship)
  https://www.rfc-editor.org/rfc/rfc7241.html

Underlying protocols used over Wi-Fi:

- TCP: https://www.rfc-editor.org/rfc/rfc9293.html
- UDP: https://www.rfc-editor.org/rfc/rfc768.html
- IPv4: https://www.rfc-editor.org/rfc/rfc791.html
- IPv6: https://www.rfc-editor.org/rfc/rfc8200.html

---

## 11. Summary

Wi-Fi is the primary wireless connectivity technology for enterprise environments. It provides high flexibility and throughput but requires careful design, strong security controls, and active monitoring to ensure reliability and protection against common wireless attack vectors.