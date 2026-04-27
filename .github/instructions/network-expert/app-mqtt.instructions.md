---
name: "Network-expert / App-mqtts"
description: "Enterprise Specification: MQTT Protocol"
layer: digital-generic-team
---
# Enterprise Specification: MQTT Protocol

## 1. Purpose

Defines the enterprise standard for lightweight messaging and event-driven communication, especially in IoT environments.

---

## 2. Description

MQTT (Message Queuing Telemetry Transport) is a lightweight publish/subscribe messaging protocol.

Architecture:

- Broker (central server)
- Publisher (sends messages)
- Subscriber (receives messages)

---

## 3. Protocol Features

### Quality of Service (QoS)

- QoS 0 → At most once (no guarantee)
- QoS 1 → At least once (may duplicate)
- QoS 2 → Exactly once (highest overhead)

---

### Retained Messages

- Broker stores last message per topic
- New subscribers receive it immediately

---

### Last Will & Testament (LWT)

- Defines message sent if client disconnects unexpectedly

---

### Keep Alive

- Client sends heartbeat to broker
- Detects connection loss

---

### Sessions

- Clean session vs persistent session
- Controls message durability

---

## 4. Typical Application Areas

- IoT telemetry
- Smart home systems
- Industrial monitoring
- Event-driven systems
- Edge computing

---

## 5. Range

Global (over TCP/IP).

---

## 6. Speed

Low bandwidth optimized.

- Small payloads
- Efficient headers
- Minimal overhead

---

## 7. Possible Attack Vectors

- Unauthorized topic access
- Weak authentication
- Broker compromise
- Message injection
- DoS via flooding
- Unencrypted connections

---

## 8. Enterprise Requirements

- TLS MUST be used (MQTTS)
- Authentication REQUIRED (user/password or certs)
- Topic ACLs MUST be enforced
- QoS MUST be selected based on criticality
- Retained messages MUST be used carefully

---

## 9. MQTT CLI Tools (mosquitto)

### Publish

```
mosquitto_pub -h localhost -t "test/topic" -m "hello"
```

---

### Subscribe

```
mosquitto_sub -h localhost -t "test/topic"
```

---

### Publish with QoS

```
mosquitto_pub -h localhost -t "test/topic" -m "hello" -q 1
```

---

### Publish Retained Message

```
mosquitto_pub -h localhost -t "test/topic" -m "state" -r
```

---

### Authentication

```
mosquitto_pub -h localhost -t "test" -u user -P pass -m "secure"
```

---

## 10. Python Example

```
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected:", rc)
    client.subscribe("test/topic")

def on_message(client, userdata, msg):
    print(msg.topic, msg.payload.decode())

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)
client.loop_forever()
```

---

## 11. Official Specifications

- MQTT Standard
  https://mqtt.org/

---

## 12. Summary

MQTT is a highly efficient messaging protocol for distributed and IoT systems. Its flexibility (QoS, retained messages, sessions) makes it powerful but also requires strict governance and security configuration.