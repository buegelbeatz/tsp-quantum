---
name: "Network-expert / App-ftps"
description: "Enterprise Specification: FTP Protocol"
layer: digital-generic-team
---
# Enterprise Specification: FTP Protocol

## 1. Purpose

Defines file transfer standards.

---

## 2. Description

FTP is a legacy protocol for file transfer.

Variants:

- FTP (insecure)
- FTPS (TLS)
- SFTP (via SSH)

---

## 3. Typical Application Areas

- Legacy systems
- File exchange

---

## 4. Range

Global.

---

## 5. Speed

Medium.

---

## 6. Possible Attack Vectors

- Plaintext credentials
- MITM
- Data interception

---

## 7. Enterprise Requirements

- FTP MUST NOT be used
- FTPS or SFTP REQUIRED

---

## 8. Python Example

```
from ftplib import FTP

ftp = FTP("localhost")
ftp.login("user", "pass")
ftp.quit()
```

---

## 9. Official Specifications

- RFC 959
  https://www.rfc-editor.org/rfc/rfc959.html

---

## 10. Summary

FTP is deprecated for secure environments and must be replaced by secure alternatives.