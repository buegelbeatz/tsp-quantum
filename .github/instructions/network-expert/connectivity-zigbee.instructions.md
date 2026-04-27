---
name: "Network-expert / Connectivity-zigbees"
description: "Enterprise Specification: Zigbee Connectivity Standard"
layer: digital-generic-team
---
# Enterprise Specification: Zigbee Connectivity Standard

## 1. Purpose

Defines the enterprise standard for Zigbee-based low-power mesh networking.

---

## 2. Description

Zigbee is a low-power wireless mesh networking protocol built on IEEE 802.15.4 and maintained by the Connectivity Standards Alliance (CSA).

It is optimized for:

- Low bandwidth
- Low power consumption
- Reliable mesh networking

---

## 3. Typical Application Areas

- Smart home automation
- Building automation
- Lighting systems
- Energy management
- Industrial monitoring

---

## 4. Range

Short to medium range.

- Single hop: ~10–100 meters
- Mesh extends coverage significantly

---

## 5. Speed

Low throughput (~250 kbps typical).

Designed for small payloads and periodic communication.

---

## 6. Possible Attack Vectors

- Weak device commissioning
- Network key exposure
- Replay attacks
- Unauthorized device joining
- Trust center compromise

---

## 7. Enterprise Requirements

- Secure commissioning MUST be enforced
- Network keys MUST be protected
- Trust center MUST be properly configured
- Device lifecycle MUST be managed
- Mesh topology MUST be validated

---

## 8. Python Example

Not applicable (requires Zigbee coordinator and hardware stack).

---

## 9. Official Specifications

- https://csa-iot.org/all-solutions/zigbee/

---

## 10. RFC References

- RFC 4944 (IPv6 over 802.15.4)
  https://www.rfc-editor.org/rfc/rfc4944.html

---

## 11. Summary

Zigbee is a robust low-power mesh networking solution for IoT environments, particularly suited for distributed sensor and automation systems.