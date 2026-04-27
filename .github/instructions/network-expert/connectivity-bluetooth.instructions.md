---
name: "Network-expert / Connectivity-bluetooths"
description: "Enterprise Specification: Bluetooth Connectivity Standard"
layer: digital-generic-team
---
# Enterprise Specification: Bluetooth Connectivity Standard

## 1. Purpose

This document defines the enterprise standard for Bluetooth connectivity, including Classic Bluetooth and Bluetooth Low Energy (BLE), covering usage, security, and operational considerations.

---

## 2. Description

Bluetooth is a short-range wireless communication technology standardized by the Bluetooth Special Interest Group (SIG).

It supports two main modes:

- Bluetooth Classic (higher throughput, e.g., audio)
- Bluetooth Low Energy (BLE) (low power, IoT-focused)

BLE is the dominant mode for modern enterprise and IoT applications.

---

## 3. Typical Application Areas

- Wearables and health devices
- Audio devices (headphones, speakers)
- Peripheral devices (keyboard, mouse)
- IoT sensors
- Proximity detection and beacons
- Device onboarding and pairing

---

## 4. Range

Short-range communication.

Range depends on:

- Device class (Class 1, 2, 3)
- BLE PHY mode
- Antenna design
- Environment (indoor vs outdoor)

BLE Long Range (coded PHY) allows extended range at reduced data rates.

---

## 5. Speed

Low to medium throughput.

- BLE optimized for low energy usage
- Throughput depends on:
  - PHY mode
  - MTU size
  - Connection interval

---

## 6. Possible Attack Vectors

### Pairing & Authentication
- Weak pairing mechanisms
- Passkey guessing
- Just Works pairing vulnerabilities

### Privacy Risks
- Device tracking via MAC address
- Beacon tracking

### Protocol-Level
- Man-in-the-middle (MITM)
- Replay attacks
- GATT service exposure

### Implementation Risks
- Firmware vulnerabilities
- Improper key storage

---

## 7. Enterprise Requirements

- BLE MUST be preferred over Classic where possible
- Secure pairing (LE Secure Connections) MUST be used
- Device identity randomization SHOULD be enabled
- Unused GATT services MUST be disabled
- Firmware MUST support secure updates

---

## 8. Python Example

### BLE Scanner

```
import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover(timeout=5.0)
    for d in devices:
        print(d)

asyncio.run(main())
```

---

## 9. Official Specifications

- Bluetooth SIG: https://www.bluetooth.com/specifications/

---

## 10. RFC References

- RFC 7668 (IPv6 over BLE)
  https://www.rfc-editor.org/rfc/rfc7668.html

---

## 11. Summary

Bluetooth (especially BLE) is the standard for short-range, low-power communication. It is widely used in IoT and mobile ecosystems but requires careful handling of pairing, identity, and device security.