---
name: "Network-expert / App-smtps"
description: "Enterprise Specification: SMTP / IMAP Protocols"
layer: digital-generic-team
---
# Enterprise Specification: SMTP / IMAP Protocols

## 1. Purpose

Defines enterprise email communication standards.

---

## 2. Description

SMTP:

- Sending email

IMAP:

- Retrieving email

---

## 3. Typical Application Areas

- Email systems
- Notifications
- Alerts

---

## 4. Range

Global.

---

## 5. Speed

Medium.

---

## 6. Possible Attack Vectors

- Email spoofing
- Phishing
- Open relay abuse
- Credential theft

---

## 7. Enterprise Requirements

- TLS REQUIRED
- SPF, DKIM, DMARC MUST be configured
- Authentication REQUIRED

---

## 8. Python Example

```
import smtplib

server = smtplib.SMTP("localhost", 25)
server.sendmail("from@test.com", "to@test.com", "hello")
server.quit()
```

---

## 9. Official Specifications

- SMTP: RFC 5321
  https://www.rfc-editor.org/rfc/rfc5321.html

---

## 10. Summary

Email protocols remain critical but require strict security controls.