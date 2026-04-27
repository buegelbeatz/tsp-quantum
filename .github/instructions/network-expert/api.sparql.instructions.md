---
name: "Network-expert / Api.sparqls"
description: "Enterprise Specification: SPARQL Protocol"
layer: digital-generic-team
---
# Enterprise Specification: SPARQL Protocol

## 1. Purpose

Defines querying of semantic data (RDF).

---

## 2. Description

SPARQL is a query language for RDF data.

Used in semantic web and knowledge graphs.

---

## 3. Typical Application Areas

- Knowledge graphs
- Semantic web
- Linked data

---

## 4. Possible Attack Vectors

- Query injection
- Data exposure
- Expensive queries

---

## 5. Enterprise Requirements

- Query limits REQUIRED
- Authentication REQUIRED
- Data access MUST be controlled

---

## 6. Example

```
SELECT ?name WHERE {
  ?person <hasName> ?name
}
```

---

## 7. Official References

- https://www.w3.org/TR/sparql11-query/

---

## 8. Summary

SPARQL is specialized for semantic data querying and not general-purpose APIs.