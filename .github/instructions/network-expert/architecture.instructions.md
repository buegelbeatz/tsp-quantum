---
name: "Network-expert / Architectures"
description: "Enterprise Blueprint: Network Architecture, Communication Layers, and Protocol Decision Framework"
layer: digital-generic-team
---
# Enterprise Blueprint: Network Architecture, Communication Layers, and Protocol Decision Framework

## 1. Purpose

This document defines the enterprise reference blueprint for structuring network communication across connectivity technologies, core network protocols, application and service protocols, and API / meta-protocol styles.

The objective is to ensure:

- Consistent architectural decision-making
- Clear separation of concerns across communication layers
- Secure and scalable protocol selection
- Improved interoperability across systems, devices, platforms, and services
- Governance for enterprise integration patterns

---

## 2. Scope

This blueprint applies to:

- Enterprise infrastructure and platform teams
- Backend, frontend, mobile, IoT, and integration teams
- Cloud and on-premise architectures
- Industrial, embedded, and edge environments
- API and service governance initiatives

---

## 3. Reference Model Overview

The enterprise communication model is structured into four decision layers:

1. Connectivity / Communication Technologies
2. Core Network Protocols
3. Application & Service Protocols
4. API / Meta-Protocol Styles

These layers answer different architectural questions:

- **Connectivity**: How do devices physically or wirelessly connect?
- **Core Protocols**: How are packets addressed, transported, and controlled?
- **Application Protocols**: Which protocol carries the service communication?
- **API Styles**: How is the interaction model designed semantically?

---

## 4. Layered Architecture Blueprint

```
Business Capability
    ↓
Application / API Style
    ↓
Application & Service Protocol
    ↓
Core Network Protocol
    ↓
Connectivity Technology
    ↓
Physical / Wireless Medium
```

---

## 5. Enterprise Layer Classification

### 5.1 Connectivity / Communication Technologies

This layer defines the medium or access technology used by a device or system.

Examples:

- Ethernet
- Wi-Fi
- Cellular
- Bluetooth
- Zigbee
- LoRa / LoRaWAN

Key decision criteria:

- Range
- Mobility
- Throughput
- Power consumption
- Environmental constraints
- Hardware support
- Deployment cost

---

### 5.2 Core Network Protocols

This layer defines packet addressing, routing, reliability, control, and transport.

Examples:

- IPv4 / IPv6
- TCP
- UDP
- QUIC
- ICMP

Key decision criteria:

- Reliability requirements
- Latency sensitivity
- Ordered delivery
- Congestion handling
- Internet compatibility
- Diagnostic / control requirements

---

### 5.3 Application & Service Protocols

This layer defines how systems communicate operationally.

Examples:

- HTTP / HTTPS
- DNS
- SSH / SCP / SFTP
- MQTT
- SMTP / IMAP
- FTP / FTPS / SFTP

Key decision criteria:

- Human vs machine interaction
- Request/response vs pub/sub
- Session model
- Security expectations
- Legacy interoperability
- Administration vs business communication

---

### 5.4 API / Meta-Protocol Styles

This layer defines the semantic interaction pattern and contract model.

Examples:

- REST
- GraphQL
- SOAP
- gRPC
- SPARQL
- Event-driven / AsyncAPI

Key decision criteria:

- Flexibility of data access
- Contract strictness
- Performance requirements
- Client diversity
- Internal vs external exposure
- Event-driven vs synchronous patterns

---

## 6. Mapping to OSI / Internet Model

### 6.1 Simplified Mapping

```
OSI Layer 7  → API / Meta-Protocol Styles + Application Protocols
OSI Layer 6  → Serialization / Encryption / Encoding
OSI Layer 5  → Session / Authentication / Stateful Interaction
OSI Layer 4  → TCP / UDP / QUIC
OSI Layer 3  → IP / ICMP
OSI Layer 2  → Ethernet / Wi-Fi MAC / Zigbee MAC / etc.
OSI Layer 1  → Physical Medium / Radio / Cable / Fiber
```

### 6.2 Practical Enterprise Interpretation

In enterprise architecture, the OSI model is useful conceptually, but real design decisions are usually made using the four enterprise layers described above.

This is because enterprise teams rarely choose "Layer 5" or "Layer 6" directly. Instead, they choose:

- Wi-Fi vs Ethernet vs Cellular
- TCP vs UDP vs QUIC
- HTTP vs MQTT vs SSH
- REST vs GraphQL vs gRPC

---

## 7. Decision Matrix

### 7.1 Connectivity Selection Matrix

| Requirement | Preferred Technology |
|-------------|----------------------|
| High reliability, fixed infrastructure | Ethernet |
| Office / campus wireless | Wi-Fi |
| Wide-area mobility | Cellular |
| Very low power short range | Bluetooth LE |
| Mesh building automation | Zigbee |
| Long-range low-power telemetry | LoRa / LoRaWAN |

---

### 7.2 Core Protocol Selection Matrix

| Requirement | Preferred Protocol |
|-------------|--------------------|
| Reliable ordered communication | TCP |
| Low-latency best-effort datagrams | UDP |
| Modern web transport with integrated TLS | QUIC |
| Diagnostics / control signaling | ICMP |
| Global addressing and routing | IP |

---

### 7.3 Application Protocol Selection Matrix

| Requirement | Preferred Protocol |
|-------------|--------------------|
| Web and API communication | HTTP / HTTPS |
| Secure administration | SSH |
| Lightweight IoT messaging | MQTT |
| Name resolution | DNS |
| Email transport | SMTP |
| Legacy file transfer | SFTP / FTPS preferred over FTP |

---

### 7.4 API Style Selection Matrix

| Requirement | Preferred Style |
|-------------|-----------------|
| Public web APIs | REST |
| Flexible frontend-driven querying | GraphQL |
| High-performance internal RPC | gRPC |
| Legacy / regulated enterprise integration | SOAP |
| Knowledge graph / semantic data | SPARQL |
| Event-driven architectures | AsyncAPI / PubSub style |

---

## 8. Architecture Decision Tree

### 8.1 Step 1: Choose Connectivity

Ask:

- Is the system fixed or mobile?
- Is low power more important than throughput?
- Is local or wide-area coverage required?
- Is mesh networking needed?

Example decisions:

- Office workstation → Ethernet or Wi-Fi
- Remote sensor → LoRaWAN or Cellular
- Wearable device → Bluetooth LE
- Smart building sensor → Zigbee

---

### 8.2 Step 2: Choose Core Transport

Ask:

- Must delivery be reliable?
- Is ordered delivery required?
- Is low latency more important than delivery guarantees?

Example decisions:

- Business API → TCP
- Real-time voice / telemetry → UDP
- Modern browser communication → QUIC

---

### 8.3 Step 3: Choose Service Protocol

Ask:

- Is this interactive admin access, messaging, or request/response?
- Is this machine-to-machine or human-to-system?
- Is the communication synchronous or asynchronous?

Example decisions:

- Admin access → SSH
- Device telemetry → MQTT
- Web API → HTTPS
- Name resolution → DNS

---

### 8.4 Step 4: Choose API Style

Ask:

- Do clients need flexible field selection?
- Is strict contract-first design required?
- Is performance critical?
- Is asynchronous integration preferred?

Example decisions:

- Public API → REST
- Frontend aggregation → GraphQL
- Internal service-to-service → gRPC
- Event-driven integration → AsyncAPI / PubSub

---

## 9. Security Blueprint

### 9.1 Security by Layer

#### Connectivity Layer
Primary controls:

- Physical security
- Wireless encryption
- Network segmentation
- Device onboarding controls
- Access point and gateway hardening

#### Core Protocol Layer
Primary controls:

- Firewall policy
- Routing control
- Anti-spoofing
- Rate limiting
- DoS protection

#### Application Protocol Layer
Primary controls:

- TLS / encryption
- Authentication
- Access control
- Service hardening
- Secure configuration

#### API / Meta-Protocol Layer
Primary controls:

- Authorization
- Schema validation
- Query complexity limits
- Versioning
- Input validation
- Governance of exposure

---

### 9.2 Enterprise Security Rules

- Unencrypted protocols MUST be avoided unless explicitly justified
- Internal and external traffic MUST be segmented
- Authentication MUST be enforced at the application layer where applicable
- Encryption in transit MUST be the default
- Protocol exposure MUST be minimized
- Management protocols MUST be isolated
- Legacy protocols MUST be documented and phased out where possible

---

## 10. Reference Architecture Patterns

### 10.1 Standard Enterprise Web Application

```
Client
  → Wi-Fi / Ethernet
  → IP
  → TCP / QUIC
  → HTTPS
  → REST or GraphQL
  → Backend Services
```

Typical usage:

- Browser-based enterprise application
- Mobile application backend
- External customer portal

---

### 10.2 Internal Microservice Platform

```
Service A
  → Ethernet / Cloud Network
  → IP
  → TCP / QUIC
  → HTTPS or gRPC
  → Service B
```

Typical usage:

- Container platforms
- Service mesh environments
- Internal domain-driven systems

---

### 10.3 IoT Telemetry Pattern

```
Sensor
  → Bluetooth / Zigbee / LoRaWAN / Cellular
  → IP or gateway translation
  → MQTT
  → Broker
  → Event Processing Platform
```

Typical usage:

- Smart buildings
- Industrial telemetry
- Remote environmental sensors

---

### 10.4 Secure Operations Pattern

```
Admin Workstation
  → VPN / Enterprise Network
  → IP
  → TCP
  → SSH
  → Bastion Host
  → Target System
```

Typical usage:

- Secure infrastructure administration
- Production server access
- Restricted operational control plane

---

### 10.5 Event-Driven Enterprise Integration

```
Producer Service
  → HTTPS / MQTT / Broker Protocol
  → Event Broker
  → Consumer Services
  → AsyncAPI-governed contract
```

Typical usage:

- Business event streaming
- Order processing
- Notification systems
- Cross-domain integration

---

## 11. Governance Model

### 11.1 Standardization Principles

The enterprise SHOULD define:

- Approved connectivity technologies
- Approved transport protocols
- Approved service protocols
- Approved API styles
- Banned or deprecated protocols
- Exception handling procedures

---

### 11.2 Approved-by-Default Guidance

#### Preferred defaults
- Ethernet or Wi-Fi for enterprise user connectivity
- IP-based networking
- TCP for reliable communication
- HTTPS for service access
- REST for broad interoperability
- gRPC for high-performance internal service-to-service
- MQTT for lightweight IoT messaging
- SSH for secure administration

#### Restricted / legacy usage
- FTP
- Telnet
- Unencrypted HTTP
- Weak Wi-Fi security modes
- Password-only remote admin without MFA or strong controls

---

### 11.3 Decision Ownership

| Decision Area | Recommended Owner |
|---------------|-------------------|
| Connectivity technology | Network / Platform Architecture |
| Core transport protocol | Network / Security Architecture |
| Application protocol | Platform / Integration Architecture |
| API style | Application / Enterprise Architecture |
| Security controls | Security Architecture |
| Exceptions | Architecture Governance Board |

---

## 12. Example Enterprise Ruleset

### 12.1 General Rules

- All externally exposed APIs MUST use HTTPS
- All production administration MUST use SSH with key-based authentication
- All public APIs SHOULD be REST unless a justified alternative exists
- All internal high-performance service communication MAY use gRPC
- All IoT messaging SHOULD use MQTT unless another protocol is explicitly justified
- All DNS infrastructure MUST be centrally governed
- Unsecured legacy protocols MUST NOT be introduced into new systems

---

### 12.2 IoT-Specific Rules

- Bluetooth LE SHOULD be used for local low-power short-range device communication
- Zigbee SHOULD be used for mesh-based building and automation scenarios
- LoRaWAN SHOULD be used only for low-bandwidth long-range telemetry
- Cellular SHOULD be used where mobility or remote-area coverage is required
- MQTT SHOULD be the default broker-based messaging protocol for IoT integrations

---

### 12.3 API Rules

- REST is the default style for public-facing APIs
- GraphQL SHOULD be limited to clearly justified frontend-driven aggregation use cases
- SOAP MAY be used only for required legacy or regulated integrations
- SPARQL SHOULD be limited to semantic or graph-based platforms
- AsyncAPI SHOULD be used to document event-driven interfaces

---

## 13. Protocol Selection Examples

### 13.1 Example A: Public Customer Portal
Recommended stack:

- Connectivity: Wi-Fi / Ethernet / Cellular
- Core: IP + TCP / QUIC
- Service Protocol: HTTPS
- API Style: REST

Reason:
Broad interoperability, strong browser support, standard security model.

---

### 13.2 Example B: Internal High-Performance Service Platform
Recommended stack:

- Connectivity: Ethernet / cloud virtual network
- Core: IP + TCP / QUIC
- Service Protocol: gRPC over HTTP/2
- API Style: RPC

Reason:
Performance, typed contracts, efficient internal communication.

---

### 13.3 Example C: Smart Building Sensor Mesh
Recommended stack:

- Connectivity: Zigbee
- Core: gateway-mediated IP integration
- Service Protocol: MQTT
- API Style: Event-driven

Reason:
Low power, mesh support, asynchronous telemetry flow.

---

### 13.4 Example D: Remote Agricultural Sensor
Recommended stack:

- Connectivity: LoRaWAN
- Core: LPWAN + gateway + IP backend
- Service Protocol: MQTT or HTTPS at backend side
- API Style: Event-driven or REST for management

Reason:
Long range, low power, low data volumes.

---

### 13.5 Example E: Operations Access to Production
Recommended stack:

- Connectivity: Ethernet / secure VPN
- Core: IP + TCP
- Service Protocol: SSH
- API Style: Not API-centric; secure admin channel

Reason:
Operational control, security, auditability.

---

## 14. Maturity Model

### Level 1 – Ad hoc
- Protocols chosen per project without standards
- Limited security consistency
- Little architectural governance

### Level 2 – Standardized
- Preferred protocols documented
- Basic security baseline defined
- Teams follow common defaults

### Level 3 – Governed
- Architectural review for protocol choices
- Security controls aligned by layer
- Exceptions documented and approved

### Level 4 – Optimized
- Protocol decisions tied to measurable performance and risk criteria
- Automated policy validation
- Full lifecycle governance and observability

---

## 15. Summary

This blueprint provides an enterprise-wide decision framework for network and communication architecture.

It separates concerns into four practical layers:

- Connectivity technologies
- Core network protocols
- Application and service protocols
- API and meta-protocol styles

Using this structure, the enterprise can make communication decisions consistently, securely, and transparently across infrastructure, platforms, devices, and applications.