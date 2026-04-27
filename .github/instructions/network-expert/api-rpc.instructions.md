---
name: "Network-expert / Api-rpcs"
description: "Enterprise Specification: gRPC Protocol"
layer: digital-generic-team
---
# Enterprise Specification: gRPC Protocol

## 1. Purpose

Defines enterprise usage of high-performance RPC communication.

---

## 2. Description

gRPC is a modern RPC framework:

- Uses HTTP/2
- Uses Protocol Buffers
- Supports streaming

---

## 3. Core Concepts

- Service definitions (.proto)
- Unary calls
- Streaming (client/server/bidirectional)

---

## 4. Typical Application Areas

- Microservices
- Internal APIs
- High-performance systems

---

## 5. Advantages

- High performance
- Strong typing
- Efficient binary format

---

## 6. Possible Attack Vectors

- Unauthorized service access
- Misconfigured TLS
- Reflection exposure
- Input validation issues

---

## 7. Enterprise Requirements

- TLS MUST be used
- Authentication REQUIRED
- Schema MUST be versioned
- Access control REQUIRED

---

## 8. Example

```
service UserService {
  rpc GetUser (UserRequest) returns (UserResponse);
}
```

---

## 9. Official References

- https://grpc.io/

---

## 10. Summary

gRPC is the preferred choice for high-performance internal service communication.