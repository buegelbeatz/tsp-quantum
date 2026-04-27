---
name: "Network-expert / App-sshs"
description: "Enterprise Specification: SSH / SCP Protocol"
layer: digital-generic-team
---
# Enterprise Specification: SSH / SCP Protocol

## 1. Purpose

Defines the enterprise standard for secure remote access, tunneling, automation, and file transfer using SSH.

---

## 2. Description

SSH (Secure Shell) is an encrypted protocol used for:

- Remote shell access
- Secure command execution
- Tunneling (port forwarding)
- File transfer (SCP / SFTP)

SSH provides:

- Encryption
- Authentication (key-based)
- Integrity protection

---

## 3. Typical Application Areas

- Server administration
- DevOps / CI/CD pipelines
- Infrastructure automation
- Secure file transfer
- Secure tunneling / VPN-like setups
- Bastion host access

---

## 4. Range

Global (via TCP/IP).

---

## 5. Speed

Medium (encryption overhead), typically negligible in modern systems.

---

## 6. Possible Attack Vectors

- Brute-force login attempts
- Stolen SSH keys
- Weak key formats
- MITM (if host keys not verified)
- Agent forwarding abuse
- Misconfigured tunnels
- Unauthorized lateral movement

---

## 7. Enterprise Requirements

### Authentication
- Password authentication MUST be disabled
- Key-based authentication REQUIRED
- Ed25519 or RSA-4096 keys SHOULD be used

### Access Control
- SSH access MUST be restricted via firewall
- Bastion hosts SHOULD be used
- Root login MUST be disabled

### Monitoring
- All SSH access MUST be logged
- Failed login attempts MUST be monitored

---

## 8. SSH Command Line Usage

### 8.1 Basic Connection

```
ssh user@host
```

---

### 8.2 Key-Based Authentication

```
ssh-keygen -t ed25519
ssh-copy-id user@host
```

---

### 8.3 Port Forwarding (Local Tunnel)

Forward local port → remote service

```
ssh -L 8080:localhost:80 user@host
```

---

### 8.4 Remote Port Forwarding

Expose local service to remote host

```
ssh -R 9000:localhost:3000 user@host
```

---

### 8.5 Dynamic Proxy (SOCKS / VPN-like)

```
ssh -D 1080 user@host
```

Use with browser proxy → acts like VPN

---

### 8.6 Jump Host / Bastion

```
ssh -J user@bastion target@internal-host
```

---

### 8.7 SSH Config File

File: ~/.ssh/config

```
Host myserver
    HostName example.com
    User myuser
    IdentityFile ~/.ssh/id_ed25519
    Port 22

Host internal
    HostName 10.0.0.10
    ProxyJump bastion
```

---

### 8.8 SCP File Transfer

```
scp file.txt user@host:/remote/path/
```

---

### 8.9 SSH as VPN Replacement (Advanced)

```
ssh -D 1080 -C -N user@host
```

- -D → SOCKS proxy  
- -C → compression  
- -N → no shell  

---

## 9. Python Example

```
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect("localhost", username="user", password="pass")
stdin, stdout, stderr = client.exec_command("uptime")

print(stdout.read().decode())
client.close()
```

---

## 10. Official Specifications

- RFC 4251
  https://www.rfc-editor.org/rfc/rfc4251.html

---

## 11. Summary

SSH is one of the most critical enterprise protocols. It provides secure access, tunneling, and automation capabilities but must be tightly controlled to prevent lateral movement and unauthorized access.