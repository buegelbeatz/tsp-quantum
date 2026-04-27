---
name: "Security-expert / Ddoss"
description: "DDoS Protection & Resilience Instructions"
layer: digital-generic-team
---
# DDoS Protection & Resilience Instructions


These rules apply to all systems, APIs, and services in this repository.
All services must be designed with DDoS resilience in mind.

---

# 1. Core Principles

- Assume hostile traffic at all times.
- Design for resilience, not just prevention.
- Protect availability as a primary security objective.
- Apply defense-in-depth.
- Prefer automatic mitigation over manual intervention.

---

# 2. Infrastructure-Level Protection

- Use a managed DDoS protection service where available (e.g., CDN, WAF, cloud DDoS protection).
- Place public services behind:
  - Reverse proxies
  - Load balancers
  - CDN/WAF layers
- Never expose internal services directly to the public internet.
- Block direct IP access where possible.

---

# 3. Rate Limiting (Mandatory)

- All public endpoints must implement rate limiting.
- Use:
  - IP-based limits
  - Token-based limits (for authenticated APIs)
  - Burst + sustained rate models
- Apply stricter limits to:
  - Authentication endpoints
  - Password reset endpoints
  - Expensive computation endpoints
- Rate limit responses must not leak internal details.

---

# 4. Resource Protection

- Protect against:
  - CPU exhaustion
  - Memory exhaustion
  - File descriptor exhaustion
  - Thread pool starvation
- Always configure:
  - Maximum request size
  - Request timeouts
  - Connection limits
- Use circuit breakers where applicable.
- Reject overly large payloads early.

---

# 5. Timeouts & Limits (Mandatory)

All services must define:

- Connection timeout
- Read timeout
- Write timeout
- Upstream service timeout
- Maximum request body size
- Maximum concurrent connections

Never allow unbounded requests.

---

# 6. API & Application-Level Protections

- Validate input before heavy processing.
- Avoid expensive synchronous operations on public endpoints.
- Offload heavy tasks to background workers.
- Cache frequently requested data.
- Avoid database queries without indexes.

---

# 7. Caching Strategy

- Cache:
  - Static content
  - Public GET responses
  - Repeated queries
- Use CDN caching when possible.
- Implement proper cache-control headers.
- Avoid unnecessary cache invalidation storms.

---

# 8. Monitoring & Detection

- Monitor:
  - Requests per second
  - Error rate
  - Latency spikes
  - Resource utilization
- Set alert thresholds for abnormal traffic patterns.
- Log abnormal traffic behavior.
- Implement automated scaling where appropriate.

---

# 9. Auto-Scaling & Graceful Degradation

- Use horizontal scaling where possible.
- Implement:
  - Auto-scaling policies
  - Queue backpressure
- Prefer partial service degradation over total failure.
- Disable non-essential features under load.

---

# 10. Bot & Abuse Protection

- Use CAPTCHA or bot-detection for sensitive endpoints.
- Detect abnormal request patterns.
- Block suspicious IP ranges where necessary.
- Apply progressive delays for repeated failures.

---

# 11. Network-Level Controls

- Enable SYN flood protection.
- Configure firewall rate limits.
- Block unused ports.
- Disable unnecessary protocols.
- Use Anycast or geographically distributed infrastructure where possible.

---

# 12. Logging & Forensics

- Log:
  - Source IP
  - Request rate anomalies
  - Blocked requests
- Ensure logs are centralized and immutable.
- Avoid logging excessive payload data during attack conditions.

---

# 13. Dependency Resilience

- Protect upstream dependencies with:
  - Timeouts
  - Retries with backoff
  - Circuit breakers
- Avoid cascading failures.
- Limit retry storms.

---

# 14. Testing & Simulation

- Perform load testing regularly.
- Simulate:
  - Traffic spikes
  - Slowloris-style attacks
  - Burst traffic
- Validate that rate limiting behaves correctly.
- Validate system recovery after attack simulation.

---

# 15. Prohibited Practices

- No unlimited request handling
- No unbounded queues
- No synchronous heavy computation on public endpoints
- No missing request size limits
- No infinite retries
- No lack of timeout configuration

---

# 16. Incident Response

- Maintain a documented DDoS response procedure.
- Define escalation paths.
- Ensure ability to:
  - Increase rate limits temporarily
  - Enable stricter firewall rules
  - Switch traffic to backup infrastructure
- Perform post-incident review and mitigation hardening.

---

Availability is a security requirement.
Systems must fail gracefully under stress, not catastrophically.
