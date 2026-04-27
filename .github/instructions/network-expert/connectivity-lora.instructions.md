---
name: "Network-expert / Connectivity-loras"
description: "Enterprise Specification: LoRa / LoRaWAN Connectivity Standard"
layer: digital-generic-team
---
# Enterprise Specification: LoRa / LoRaWAN Connectivity Standard

## 1. Purpose

Defines enterprise usage of long-range, low-power networking.

---

## 2. Description

LoRa is a physical layer modulation technique.  
LoRaWAN is the network protocol defined by the LoRa Alliance.

Architecture:

- End devices
- Gateways
- Network server
- Application server

---

## 3. Typical Application Areas

- Smart cities
- Agriculture
- Remote monitoring
- Asset tracking
- Environmental sensing

---

## 4. Range

Long range:

- Several kilometers in urban environments
- Up to tens of kilometers in rural areas

---

## 5. Speed

Very low throughput.

Optimized for:

- Small payloads
- Infrequent communication
- Battery-powered devices

---

## 6. Possible Attack Vectors

- Key compromise (AppKey, NwkKey)
- Replay attacks
- Jamming
- Rogue gateways
- Backend API exposure

---

## 7. Enterprise Requirements

- Secure key provisioning MUST be enforced
- Regional parameters MUST be respected
- Gateway infrastructure MUST be secured
- Payload size MUST be minimized
- Duty-cycle constraints MUST be respected

---

## 8. Python Example

Not applicable (requires LoRa hardware + network).

---

## 9. Official Specifications

- https://lora-alliance.org/

---

## 10. RFC References

- No direct RFC (LPWAN defined by LoRa Alliance)

---

## 11. Summary

LoRaWAN is ideal for long-range, low-power IoT use cases but unsuitable for high-throughput or real-time communication.