---
name: "Quality-expert / Versionings"
description: "Enterprise Specification: Software Versioning Standard"
layer: digital-generic-team
---
# Enterprise Specification: Software Versioning Standard

## 1. Purpose

This document defines the standardized approach to versioning software artifacts across the organization to ensure:

* Consistency across teams and systems
* Traceability of changes
* Compatibility management
* Reproducibility of builds
* Alignment with CI/CD and release governance

---

## 2. Scope

This specification applies to:

* All internally developed software
* APIs and services
* Libraries and shared components
* Infrastructure-as-Code artifacts
* Container images and deployable packages

---

## 3. Versioning Scheme

### 3.1 Standard: Semantic Versioning (SemVer)

All software artifacts MUST follow Semantic Versioning.

**Format:**

```
MAJOR.MINOR.PATCH
```

**Example:**

```
2.5.13
```

---

### 3.2 Version Components

| Component | Description                                             |
| --------- | ------------------------------------------------------- |
| MAJOR     | Breaking changes (incompatible API or behavior changes) |
| MINOR     | Backward-compatible feature additions                   |
| PATCH     | Backward-compatible bug fixes                           |

---

### 3.3 Extended Version Format

Pre-release and build metadata MAY be used:

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

**Examples:**

```
1.4.0-alpha.1
1.4.0-rc.2
1.4.0+20260325
1.4.0-beta.3+build.456
```

---

## 4. Versioning Rules

### 4.1 Increment Rules

* MAJOR MUST be incremented when:

  * Public APIs change incompatibly
  * Data formats change incompatibly

* MINOR MUST be incremented when:

  * New features are added
  * Backward compatibility is preserved

* PATCH MUST be incremented when:

  * Bugs are fixed
  * No functional changes are introduced

---

### 4.2 Immutability

* Released versions MUST be immutable
* Artifacts MUST NOT be modified after release
* Any change requires a new version

---

### 4.3 Pre-release Versions

Pre-release identifiers MUST be used for non-production builds:

| Identifier | Usage                     |
| ---------- | ------------------------- |
| alpha      | Early development         |
| beta       | Feature-complete, testing |
| rc         | Release candidate         |

---

### 4.4 Build Metadata

Build metadata SHOULD include:

* Build timestamp
* Commit hash
* CI pipeline ID

**Example:**

```
2.1.0+build.789.sha.abc123
```

---

## 5. Git Integration

### 5.1 Tagging

* Each release MUST be tagged in Git
* Tag format:

```
vMAJOR.MINOR.PATCH
```

**Example:**

```
v1.3.0
```

---

### 5.2 Branch Strategy Alignment

Versioning MUST align with branching strategy:

| Branch        | Version Behavior     |
| ------------- | -------------------- |
| main / master | Production releases  |
| develop       | Next MINOR version   |
| feature/*     | Pre-release versions |
| hotfix/*      | PATCH versions       |

---

### 5.3 Commit Traceability

Each version MUST be traceable to:

* Git commit hash
* Change log entry
* Build artifact

---

## 6. API Versioning

### 6.1 Public APIs

APIs MUST be versioned explicitly.

**Options:**

* URI-based:

  ```
  /api/v1/resource
  ```

* Header-based:

  ```
  Accept: application/vnd.company.v1+json
  ```

---

### 6.2 Backward Compatibility

* MINOR and PATCH releases MUST remain backward compatible
* Breaking changes REQUIRE MAJOR version increment

---

## 7. Artifact Versioning

### 7.1 Containers

Container images MUST be versioned:

```
service-name:1.4.2
service-name:1.4
service-name:latest
```

(Note: `latest` is discouraged for production use.)

---

### 7.2 Packages

* Python: version in `pyproject.toml`
* Node: version in `package.json`
* Java: version in `pom.xml`

---

## 8. Release Management

### 8.1 Release Types

| Type            | Version Impact |
| --------------- | -------------- |
| Major Release   | MAJOR          |
| Feature Release | MINOR          |
| Patch Release   | PATCH          |
| Hotfix          | PATCH          |

---

### 8.2 Change Log

Each release MUST include a changelog.

**Structure:**

```
## [1.4.0] - 2026-03-25

### Added
- Feature X

### Changed
- Behavior Y

### Fixed
- Bug Z
```

---

## 9. Compliance Requirements

* All services MUST follow this versioning standard
* CI/CD pipelines MUST enforce version validation
* Releases without valid versioning MUST be rejected
* Version conflicts MUST fail builds

---

## 10. Tooling Recommendations

Typical tooling includes:

* Git tags for version control
* CI/CD pipelines for automated versioning
* Dependency managers for version constraints
* Artifact repositories (e.g., Nexus, Artifactory)

---

## 11. Governance

* Architecture Board owns this standard
* Changes REQUIRE formal approval
* Periodic audits SHOULD be conducted

---

## 12. Exceptions

Any deviation from this standard MUST be:

* Documented
* Approved by Architecture Governance
* Time-bound

---

## 13. Summary

This specification ensures:

* Predictable version evolution
* Clear compatibility guarantees
* Full traceability from code to artifact
* Alignment across teams and systems
