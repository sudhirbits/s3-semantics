# ADR‑001: Authorization Architecture Overview

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

The system requires a scalable authorization model supporting:

* Backend API enforcement
* Fine‑grained UI control (menus, tabs, sections, actions, implementations)
* Multi‑tenant hierarchy (System → Tenant → Customer → Sub‑customer)
* Multiple clients (React Web, Flutter Mobile)
* Immediate effect of authorization changes without forced re‑login

## Decision

Adopt a **backend‑centric RBAC model with hierarchical permission overrides**, and expose **resolved permissions** to clients for UI behavior only.

## Principles

* JWT authenticates identity only
* Authorization is resolved server‑side
* Clients receive flattened permissions
* Deny by default
* Backend remains authoritative

## Consequences

* Clean separation of authn/authz
* Supports complex UI without role logic in clients
* Safe and auditable authorization model

***

# ADR‑002: Permission Model & Naming Standard

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Permissions must be compact, readable, stable, and usable across web and mobile clients.

## Decision

Permissions are represented as **compact string identifiers**, optionally carrying **conditions metadata**.

### Format

```
<type>:<domain>[.<subdomain>][.<resource>][.<action>]
```

### Type Prefixes

| Prefix | Meaning        |
| ------ | -------------- |
| `m`    | Menu           |
| `t`    | Tab            |
| `s`    | Section        |
| `a`    | Action         |
| `i`    | Implementation |

### Examples

* `m:bil`
* `t:bil.inv`
* `s:bil.inv.sum`
* `a:bil.inv.cr`
* `i:bil.inv.sum:A`

### Conditions (optional)

```json
{ "p": "a:bil.inv.ed", "c": { "status": ["D","S"], "owner": "self" } }
```

## Rules

* Missing permission = deny
* Explicit deny overrides allow
* Permission names are immutable once released (deprecate only)

## Consequences

* Stable API contract
* Compact transmission
* Cross‑platform consistency

***

# ADR‑003: Roles & System‑Level Permissions

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Roles provide coarse‑grained access and must remain stable and manageable.

## Decision

System roles define **baseline permissions** only.

### Characteristics

* Roles map to permissions with allow/deny
* Absence of permission = deny
* Roles do not encode UI hierarchy logic
* Roles do not contain tenant or customer logic

## Examples

* `CustomerAdmin`
* `CustomerUser`
* `ReadOnlyUser`

## Consequences

* Prevents role explosion
* Keeps RBAC simple and auditable

***

# ADR‑004: Hierarchical Permission Overrides

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Different tenants and customers require customized UI behavior without altering system roles.

## Decision

Support hierarchical overrides **by role name**, storing **only deltas**.

### Override Layers (low → high precedence)

1. System role permissions
2. Tenant overrides
3. Customer overrides
4. Sub‑customer overrides

### Override Rules

* Overrides apply only if permission is marked overridable
* System‑level deny with non‑overridable permission cannot be overridden
* Missing override inherits from parent
* Explicit deny overrides allow

## Governance

* Tenant overrides: System Admin
* Customer overrides: Tenant Admin

## Consequences

* Safe customization
* No privilege escalation
* Predictable inheritance

***

# ADR‑005: User‑Level Permissions

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Exceptional access is required without mutating role semantics.

## Decision

User permissions are **explicit**, **separate**, and applied last.

### Characteristics

* Users are not treated as roles
* User permissions can allow or deny
* Applied after all role‑based overrides
* Explicit deny always wins

## Use Cases

* Support access
* Break‑glass scenarios
* Temporary exceptions

## Consequences

* Clear audit trail
* No role contamination
* Simple mental model

***

# ADR‑006: Permission Resolution & Enforcement (Backend)

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Authorization must be deterministic, auditable, and enforceable.

## Decision

Permissions are fully resolved in backend and enforced at API boundaries.

### Resolution Algorithm

1. Start with deny
2. Apply system role permissions
3. Apply tenant overrides
4. Apply customer overrides
5. Apply sub‑customer overrides
6. Apply user permissions
7. Explicit deny overrides allow

### Enforcement

* Domain permissions enforced in FastAPI middleware/dependencies
* Conditions are informational for UI only
* Backend always re‑validates

### Debugging

Provide a **“permission explain” endpoint** to trace:

* Effective permission
* Source scope
* Override reason

## Consequences

* Strong security guarantees
* Easier debugging and audits

***

# ADR‑007: JWT, Caching & Invalidation Strategy

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Authorization changes must take effect immediately without re‑authentication.

## Decision

JWT carries identity only; permissions are resolved and cached server‑side.

### JWT Contents

* User ID
* Tenant / customer / sub‑customer IDs
* Role names (optional)
* No permissions

### Caching

* Cache resolved permissions per user
* Cache populated on demand
* Cache explicitly evicted on:
  * Role change
  * Override change
  * User permission change

### Invalidation

* Explicit eviction only
* No permission versioning in JWT
* No forced logout

## Consequences

* Immediate consistency
* Small JWT size
* Operational simplicity

***

# ADR‑008: Client‑Side Authorization (Web & Mobile)

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Multiple clients must behave consistently with minimal duplication.

## Decision

Clients consume resolved permissions and evaluate UI behavior locally.

### Client Contract

```json
{
  "permissions": [
    { "p": "m:bil" },
    { "p": "a:bil.inv.ed", "c": { "status": ["D","S"] } }
  ]
}
```

### Rules

* Missing permission = deny
* Explicit deny respected
* `can(permission, context)` used everywhere
* No role or override logic in clients

### Implementations

* React: Context + hooks
* Flutter: Service / Provider

### Prohibitions

* Clients must not enforce API security
* Clients must not infer permissions
* Clients must not diverge semantics

## Consequences

* Identical behavior across platforms
* Simple, testable UI logic
* Backend remains authoritative

# ADR‑009: Auditing, History & Explainability

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

Authorization behavior varies across system, tenant, customer, and user scopes.  
For security, compliance, and operational support, it must be possible to understand:

* **Who changed what**
* **When it was changed**
* **Why a user has (or does not have) a permission**

## Decision

All permission overrides and user‑level permission changes are **audited, versioned, and explainable**.

***

## Audit Requirements

### Logged Events

The system MUST log:

* Creation of role permission overrides
* Modification of overrides
* Deletion of overrides
* User direct permission changes

Each audit record includes:

* Actor (user / system)
* Scope (system / tenant / customer / sub‑customer / user)
* Role name (if applicable)
* Permission identifier
* Effect (allow / deny)
* Timestamp
* Reason / comment (optional but recommended)

***

## History Retention

* **Full history is retained**, not just last write
* Historical records are immutable
* Used for:
  * Compliance
  * Incident investigation
  * Change rollback (manual)

Retention duration is governed by organizational policy.

***

## Permission Explainability

### Requirement

The backend MUST expose a **“permission explain” debug endpoint** (restricted access).

### Purpose

Given:

* User
* Permission name

The endpoint returns:

* Final effective decision (allow / deny)
* Source scope (system / tenant / customer / sub‑customer / user)
* Role involved (if applicable)
* Override chain applied
* Reason for deny (if denied)

### Constraints

* Not exposed to regular end users
* Used by admins, support, and debugging tools

***

## Consequences

✅ Transparent authorization behavior  
✅ Easier support and debugging  
✅ Compliance‑ready audit trail  
✅ Reduced risk of silent privilege changes

***

# ADR‑010: Deferred & Future Considerations

**Status:** DRAFT  
**Date:** 2026‑06‑04

## Context

The authorization system is designed to be extensible without premature complexity.  
Certain capabilities are intentionally deferred.

***

## Deferred Capabilities (Explicitly Out of Scope)

### 1. Permission Catalog / Client‑ID Registry

A centralized permission catalog (with metadata such as category, description, overridability, client‑id mapping) is **not required initially**.

**Future use cases:**

* Validation of overrides
* Admin UI generation
* Documentation & tooling
* Static analysis

The current design allows this to be added without breaking changes.

***

### 2. Tenant‑Authored Conditions

Tenants and customers are **not allowed** to define or modify permission conditions.

* Conditions remain backend‑defined
* Overrides only allow allow/deny
* Prevents policy language complexity and security risks

***

### 3. Policy Authoring Language

No DSL or policy engine (e.g. Rego, CEL) is introduced at this stage.

* Authorization rules remain code‑defined
* JSON is used only as a transport and storage format

***

### 4. Offline Override Propagation (Mobile)

Mobile clients may cache permissions temporarily.

* Permissions are refreshed on login / app resume
* Real‑time push invalidation is not required
* Backend remains authoritative

***

## Non‑Goals (Explicit)

* Frontend‑enforced security
* Client‑side role resolution
* Dynamic permission inference
* Feature flags replacing permissions

***

## Design Guarantees for the Future

The current design ensures:

* New override scopes can be added
* Permission catalog can be introduced
* Conditions can evolve internally
* Additional clients can be supported

All without changing:

* Permission names
* Client contracts
* Core resolution semantics

***

## Consequences

✅ Prevents scope creep  
✅ Sets clear expectations  
✅ Keeps initial implementation focused  
✅ Preserves long‑term flexibility

# Authorization & Permissions – Developer Guidelines

**Status:** DRAFT  
**Applies to:** Backend (FastAPI), Web (React), Mobile (Flutter)  
**Derived from:** ADR‑001 → ADR‑010

***

## 1. Purpose

This document defines **how authorization is implemented and used** across backend APIs and client applications.

It is binding for:

* permission naming
* backend enforcement
* frontend and mobile usage
* override behavior
* auditing and explainability

If code conflicts with this document, **the code is incorrect**.

***

## 2. Core Principles (Non‑Negotiotiable)

1. **JWT authenticates identity only**
2. **Backend resolves permissions**
3. **Clients never infer permissions**
4. **Missing permission = deny**
5. **Explicit deny overrides allow**
6. **Conditions are for UI correctness only**
7. **Backend always enforces domain security**
8. **Permission names are immutable once released**

***

## 3. Permission Naming Standard (Authoritative)

### 3.1 Canonical Format

```
<type>:<domain>[.<subdomain>].<resource>[.<action>]
```

***

### 3.2 Global Rules

* **lower‑case only**
* **alphabetic characters only (`a–z`)**
* no special characters (except `:` and `.` separators)
* numbers are discouraged
* missing permission ⇒ deny
* once released, names are never renamed (only deprecated)

***

### 3.3 Components Explained

#### Type Prefix (exactly one)

| Prefix | Meaning        |
| ------ | -------------- |
| `m`    | Menu           |
| `t`    | Tab            |
| `s`    | Section        |
| `a`    | Action         |
| `i`    | Implementation |

***

#### Domain & Subdomain (Compact Codes)

* Domain and subdomain are **compact, stable codes**
* **1 or 2 subdomain segments allowed**
* More than 2 discouraged (not strictly enforced)

Examples:

```text
bil        (billing)
inv        (invoice)
pay        (payment)
usr        (user)
cfg        (config)
```

Combined:

```text
bil.inv
bil.pay
usr.pref
```

❌ Do NOT use verbose words like `billing`, `invoice`

***

#### Resource

* **Exactly one**
* Mandatory
* Compact code
* Represents the entity being acted on

Examples:

```text
inv
sum
cfg
```

***

#### Action (Optional)

* Must be from the documented list
* Or explicitly `other`

***

### 3.4 Standard Action Types (Compact)

| Meaning | Code    |
| ------- | ------- |
| view    | `v`     |
| create  | `cr`    |
| edit    | `ed`    |
| delete  | `del`   |
| execute | `x`     |
| enable  | `en`    |
| disable | `dis`   |
| other   | `other` |

✅ `other` is allowed for uncommon semantics.

***

### 3.5 Valid Examples

✅ Valid:

```text
m:bil
t:bil.inv
s:bil.inv.sum
a:bil.inv.cr
a:bil.inv.ed
a:bil.inv.exp.other
i:bil.inv.sum:default
```

❌ Invalid:

```text
a:billing.invoice.edit     (verbose)
a:bil.inv.sum.ed.extra     (multiple resources)
a:Bil.Inv.Ed               (upper case)
a:bil.inv.123              (numbers)
```

***

## 4. Permission Representation

Resolved permissions are sent to clients as:

```json
{
  "p": "a:bil.inv.ed",
  "c": {
    "status": ["draft", "sent"],
    "owner": "self"
  }
}
```

* `p` → permission name
* `c` → optional conditions (UI only)

***

## 5. Backend Authorization Model

### 5.1 Resolution Order (Low → High Priority)

1. System role permissions
2. Tenant overrides
3. Customer overrides
4. Sub‑customer overrides
5. User direct permissions

Rules:

* Start with deny
* Inherit unless overridden
* Explicit deny always wins
* Overrides apply only to overridable permissions

***

### 5.2 Backend Enforcement (FastAPI)

Permissions are enforced **only on backend APIs**.

```python
def require_permission(permission: str):
    def dependency(request: Request):
        perms = request.state.permissions
        if permission.lower() not in {
            p["p"].lower() for p in perms
        }:
            raise HTTPException(status_code=403)
    return dependency
```

Usage:

```python
@app.post("/invoices")
@Depends(require_permission("a:bil.inv.cr"))
def create_invoice():
    ...
```

✅ Backend enforcement is mandatory  
✅ UI permissions do not grant trust

***

### 5.3 Conditions Are Not Security

Backend must still enforce:

```python
if invoice.status == "paid":
    raise HTTPException(403)
```

Conditions exist **only** so UI behaves correctly.

***

## 6. JWT & Caching Rules

* JWT contains **identity only**
* No permissions in JWT
* Permissions are resolved server‑side
* Cached per user
* Cache invalidated via **explicit eviction**
* No forced logout

***

## 7. Client‑Side Authorization Contract

Clients receive **resolved permissions only**:

```json
{
  "permissions": [
    { "p": "m:bil" },
    {
      "p": "a:bil.inv.ed",
      "c": { "status": ["draft", "sent"] }
    }
  ]
}
```

Rules:

* Missing permission = deny
* Clients do not know roles
* Clients do not know overrides
* Clients do not enforce security

***

## 8. Client‑Side Permission Evaluation

### 8.1 Normalization Rule (MANDATORY)

> **Clients must normalize to lower‑case on both sides.**

Never assume naming conventions are respected.

***

### 8.2 React (Context‑Based)

```js
const normalize = (s) => s?.toLowerCase();

function can(permissionName, context = {}) {
  const name = normalize(permissionName);

  const perm = permissions.find(
    p => normalize(p.p) === name
  );

  if (!perm) return false;
  if (!perm.c) return true;

  return Object.entries(perm.c).every(([key, allowed]) => {
    const value = context[key];

    if (allowed === "self") {
      return value === context.userId;
    }

    return allowed
      .map(normalize)
      .includes(normalize(value));
  });
}
```

Usage:

```jsx
{can("m:bil") && <BillingMenu />}

<Button
  disabled={!can("a:bil.inv.ed", {
    status: invoice.status,
    userId
  })}
>
  Edit
</Button>
```

***

### 8.3 Flutter

```dart
String normalize(String? s) => s?.toLowerCase() ?? "";

bool can(String permissionName, Map<String, dynamic> context) {
  final name = normalize(permissionName);

  final perm = permissions.firstWhere(
    (p) => normalize(p.name) == name,
    orElse: () => null,
  );

  if (perm == null) return false;
  if (perm.conditions == null) return true;

  return perm.conditions!.entries.every((e) {
    if (e.value == "self") {
      return context[e.key] == context["userId"];
    }

    return e.value
        .map((v) => normalize(v))
        .contains(normalize(context[e.key]));
  });
}
```

***

## 9. Overrides, Auditing & Explainability

* All overrides are audited
* Full history is retained
* Actor, scope, permission, and effect are logged
* A restricted **permission explain** endpoint exists for:
  * debugging
  * support
  * audits

***

## 10. What Developers MUST NOT Do

❌ Put permissions in JWT  
❌ Check roles in UI  
❌ Infer permissions from data  
❌ Trust client permission checks  
❌ Rename permissions  
❌ Let tenants author conditions  
❌ Replace permissions with feature flags

***

## 11. Future‑Safe by Design

This model allows future addition of:

* permission catalog
* admin tooling
* new clients
* richer backend‑defined conditions

Without breaking:

* permission names
* client contracts
* security guarantees

***

## Final Reminder

> **Authorization is a backend responsibility.  
> UI permissions describe behavior, not trust.**

# 1. Data Model

## 1.1 Core Concepts (Canonical)

### Permission Entry (atomic)

This is the smallest unit everywhere.

```json
{
  "p": "a:bil.inv.ed",
  "e": "a",                 // "a" = allow, "d" = deny
  "c": {                    // optional
    "status": ["draft", "sent"],
    "owner": "self"
  }
}
```

Rules:

* `p` is mandatory
* `e` defaults to deny if missing
* `c` is optional and backend‑defined
* conditions are **never merged**, only carried from the winning entry

***

## 1.2 System Role Permissions

**Table / Document**

```
role_permissions_system
```

```json
{
  "role": "customeradmin",
  "permissions": [
    { "p": "m:bil", "e": "a" },
    { "p": "t:bil.inv", "e": "a" },
    { "p": "a:bil.inv.cr", "e": "a" },
    { "p": "a:bil.inv.del", "e": "d" }
  ]
}
```

Notes:

* System baseline
* May include explicit denies
* Missing = deny

***

## 1.3 Role Overrides (Tenant / Customer / Sub‑customer)

**Single table / collection** with scope.

```json
{
  "scope_type": "customer",        // tenant | customer | subcustomer
  "scope_id": "cust-123",
  "role": "customeradmin",
  "overrides": [
    { "p": "a:bil.inv.del", "e": "a" },
    { "p": "s:bil.inv.sum", "e": "d" }
  ]
}
```

Rules:

* Overrides contain **only deltas**
* Permission must be overridable (enforced elsewhere)
* Overrides replace previous value, not merge

***

## 1.4 User Direct Permissions

**Separate and explicit**

```json
{
  "user_id": "user-42",
  "permissions": [
    { "p": "a:bil.inv.del", "e": "d" }
  ]
}
```

Rules:

* Applied last
* Explicit deny always wins
* No role semantics here

***

## 1.5 Effective Permission Map (Internal)

During resolution, normalize into a map:

```python
{
  "a:bil.inv.ed": {
    "effect": "allow",
    "conditions": {...},
    "source": "system|tenant|customer|subcustomer|user"
  }
}
```

This map is **never stored**, only computed.

***

# 2. Permission Resolution & Merging Logic

## 2.1 High‑Level Algorithm

1. Start with empty permission map (implicit deny)
2. Apply **system role permissions**
3. Apply **tenant overrides**
4. Apply **customer overrides**
5. Apply **sub‑customer overrides**
6. Apply **user permissions**
7. Flatten to final allow‑only list for clients

***

## 2.2 Helper: Normalize Permission Name

```python
def norm(p: str) -> str:
    return p.lower()
```

Normalization is mandatory.

***

## 2.3 Core Merge Function

This is the **heart of the system**.

```python
def apply_permissions(
    target: dict,
    entries: list,
    source: str
):
    for entry in entries:
        p = norm(entry["p"])
        effect = entry.get("e", "d")
        conditions = entry.get("c")

        # explicit deny always wins
        if effect == "d":
            target[p] = {
                "effect": "deny",
                "conditions": None,
                "source": source
            }
            continue

        # allow only if not already denied
        if p not in target or target[p]["effect"] != "deny":
            target[p] = {
                "effect": "allow",
                "conditions": conditions,
                "source": source
            }
```

Key properties:

* deny overwrites everything
* allow never overwrites deny
* conditions are carried from the winning layer only

***

## 2.4 Full Resolution Example

```python
def resolve_permissions(
    role_permissions,
    tenant_overrides,
    customer_overrides,
    subcustomer_overrides,
    user_permissions
):
    resolved = {}

    apply_permissions(resolved, role_permissions, "system")
    apply_permissions(resolved, tenant_overrides, "tenant")
    apply_permissions(resolved, customer_overrides, "customer")
    apply_permissions(resolved, subcustomer_overrides, "subcustomer")
    apply_permissions(resolved, user_permissions, "user")

    return resolved
```

***

## 2.5 Flatten for Client Consumption

Clients must receive **allow‑only** permissions.

```python
def flatten_for_client(resolved: dict) -> list:
    result = []

    for p, data in resolved.items():
        if data["effect"] == "allow":
            entry = { "p": p }
            if data["conditions"]:
                entry["c"] = data["conditions"]
            result.append(entry)

    return result
```

Output:

```json
[
  { "p": "m:bil" },
  {
    "p": "a:bil.inv.ed",
    "c": { "status": ["draft", "sent"] }
  }
]
```

***

## 3. Allowable Override Enforcement (Critical)

This happens **before merging**.

```python
def is_override_allowed(permission: str) -> bool:
    # future: consult catalog
    return permission in OVERRIDABLE_PERMISSIONS
```

If:

* system effect = deny
* allowOverride = false

→ ignore override silently (but audit it).

***

## 4. Auditing Hooks (Where to Log)

Log whenever:

* override is created / updated / deleted
* user permission changes
* override is rejected due to non‑overridable permission

Resolution itself does **not** log (too noisy).

***

## 5. Complexity & Performance

* Resolution is **O(n)** per layer
* Typical permission count is small (<500)
* Safe to compute on cache miss
* Cache per user, explicit eviction on change

***

## 6. Key Guarantees (Why This Is Safe)

✅ Deterministic  
✅ Deny‑by‑default  
✅ Explicit deny precedence  
✅ No client trust  
✅ No role explosion  
✅ Conditions never weaken security

***

## 7. What NOT to Do in Merging

❌ Merge conditions across layers  
❌ Let allow override deny  
❌ Emit denies to client  
❌ Skip normalization  
❌ Infer missing permissions

***