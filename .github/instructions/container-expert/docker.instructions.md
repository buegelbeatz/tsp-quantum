---
name: "Container-expert / Dockers"
description: "Docker — Enterprise Container Runtime Specification"
layer: digital-generic-team
---
# Docker — Enterprise Container Runtime Specification

**Priority:** 3 (last resort — use only when Podman and Singularity are unavailable)
**Official documentation:** https://docs.docker.com/

---

## 1. Overview

Docker is the most widely adopted container runtime and is available on most developer workstations.
It requires a background daemon (`dockerd`) running as root, which makes it the lowest-priority option in this project.
Use Docker only when neither Podman nor Singularity is available.

---

## 2. Required Version

Docker Engine `>= 24.0` is REQUIRED.
Docker Compose plugin `>= 2.0` is REQUIRED (replaces the legacy `docker-compose` standalone binary).

Check installed versions:

```sh
docker --version
docker compose version
```

---

## 3. Detection

Detection MUST verify both binary availability and daemon reachability:

```sh
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  CONTAINER_TOOL=docker
fi
```

> A running Docker daemon (`dockerd`) is required. If `docker info` fails, Docker cannot be used.

---

## 4. Standard Usage Patterns

### Pull an image
```sh
docker pull python:3.12-slim
```

### Run a container (remove after exit)
```sh
docker run --rm -v "$(pwd)":/workspace -w /workspace python:3.12-slim python script.py
```

### Run with environment variables from `.env`
```sh
docker run --rm --env-file .env -v "$(pwd)":/workspace -w /workspace python:3.12-slim python script.py
```

### Build an image
```sh
docker build -t myapp:latest .
```

### Execute in a running container
```sh
docker exec -it <container-id> bash
```

---

## 5. Compose Support

Use the Docker Compose plugin (not the legacy standalone binary):

```sh
docker compose up -d
docker compose down
```

---

## 6. Security and Compliance

| Property | Value |
|---|---|
| Runs as root | Daemon runs as root by default |
| Daemon required | Yes (`dockerd`) |
| Image standard | OCI / Docker v2 |
| Network isolation | Yes (bridge networking) |
| Rootless mode available | Yes (requires explicit setup) |
| Secrets injection | Via `--secret` flag or `--env-file` |

- MUST NOT run containers with `--privileged` unless absolutely required and explicitly documented.
- MUST NOT expose the Docker socket (`/var/run/docker.sock`) to containers without strong justification — this is equivalent to root access on the host.
- SHOULD enable rootless Docker where supported to reduce privilege exposure.
- MUST NOT bind-mount sensitive host directories (`/etc`, `/root`, `/var`) without justified cause.
- SHOULD use read-only volume mounts (`:ro`) where write access is not needed.

---

## 7. Rootless Docker

Docker supports rootless mode to run the daemon and containers without root:

```sh
dockerd-rootless-setuptool.sh install
```

See: https://docs.docker.com/engine/security/rootless/

When available, rootless Docker SHOULD be preferred over the root daemon.

---

## 8. Context and Registry

Docker defaults to `docker.io`. Always use fully qualified image names for reproducibility:

```sh
docker pull docker.io/library/python:3.12-slim
```

Use `docker context` to manage multiple Docker endpoints:

```sh
docker context ls
docker context use <context-name>
```

---

## 9. References

| Resource | URL |
|---|---|
| Official documentation | https://docs.docker.com/ |
| CLI reference | https://docs.docker.com/reference/cli/docker/ |
| Dockerfile reference | https://docs.docker.com/reference/dockerfile/ |
| Docker Compose reference | https://docs.docker.com/reference/compose-file/ |
| Rootless Docker guide | https://docs.docker.com/engine/security/rootless/ |
| Docker security best practices | https://docs.docker.com/engine/security/ |
| OCI image specification | https://github.com/opencontainers/image-spec |
