# Multiagent Monolith-to-Microservices Migration Plan

## 1. Objective

Use a coordinated multiagent workflow to analyze the Spring Boot monolith, discover approximate business domains from source and database evidence, create reviewed module boundaries inside the existing monolith, enforce dependency rules, establish database ownership, replace direct implementation calls with internal APIs, and identify safe candidates for eventual independent microservice extraction.

Any groups produced by an existing analysis run are **provisional starting points**, not a target service count or automatically deployable microservices. The workflow must be free to merge redundant or overlapping groups, split groups when evidence supports distinct capabilities, and leave uncertain classes unassigned. The desired result is a defensible approximation of business domains, not a predetermined number of services.

The migration should progress through these stages:

```text
Java monolith
    -> Source and database discovery
    -> Provisional candidate groups
    -> Consolidated approximate business domains
    -> Reviewed module boundaries
    -> Modular monolith
    -> Enforced dependencies
    -> Single-owner data model
    -> Internal APIs and events
    -> Validated extraction candidates
    -> Independent microservices
```

## 2. Core Principles

1. Agents produce evidence and artifacts instead of making unsupported assumptions.
2. Agents do not independently decide that a candidate group is production-ready.
3. Every relationship must include provenance where possible.
4. Unknown classes, tables, and dependencies remain explicitly unknown.
5. Each implementation agent edits only its assigned scope.
6. The monolith must remain buildable after every migration step.
7. Database ownership must be resolved before process extraction.
8. Cross-module calls must use explicit contracts rather than repositories or entities.
9. Every migration step must have validation and rollback information.
10. Human approval is required before destructive or high-risk changes.

## 3. Multiagent Architecture

```text
Orchestrator
    |
    +--> Discovery Agent
    +--> Static Analysis Agent
    +--> Semantic Analysis Agent
    +--> LLM Role Classification Agent
    +--> Service Boundary Agent
    +--> LLM Cluster Merge Agent
    +--> LLM Ambiguity Resolution Agent
    +--> Database Ownership Agent
    +--> LLM Database Ownership Advisor
    +--> Dependency Rules Agent
    +--> API Contract Agent
    +--> LLM API Contract Advisor
    +--> LLM Domain Naming Agent
    +--> Migration Planning Agent
    +--> Module Boundary Agent
    +--> Data Migration Agent
    +--> API Migration Agent
    +--> Validation Agent
    +--> Report Agent
```

### 3.1 Orchestrator Agent

The orchestrator controls sequencing, shared state, approvals, conflicts, and validation.

Responsibilities:

- Provide the source repository or archive to analysis agents.
- Maintain the migration manifest.
- Start independent analysis agents in parallel.
- Merge their artifacts.
- Detect conflicting recommendations.
- Request human approval at architecture gates.
- Assign implementation tasks with explicit file scopes.
- Block later steps when validation fails.
- Maintain rollback information.

The orchestrator must not silently resolve disagreements between agents. Conflicts should be recorded for review.

## 4. Shared Artifacts

All agents communicate through versioned JSON and Markdown artifacts.

```text
migration/
  manifest.json
  source-inventory.json
  dependency-graph.json
  edge-evidence.json
  semantic-class-data.json
  llm-role-classifications.json
  cluster-merge-decisions.json
  ambiguity-decisions.json
  candidate-modules.json
  database-ownership.json
  database-ownership-advice.json
  dependency-rules.json
  architecture-violations.json
  api-contracts.json
  api-contract-advice.json
  migration-plan.json
  validation-report.json
  reports/
    baseline.html
    candidate-modules.html
    database-ownership.html
    dependency-violations.html
    migration-progress.html
    final-boundaries.html
```

Every artifact should include:

- Schema version
- Source revision or archive hash
- Generator agent
- Generation timestamp
- Configuration
- Confidence values
- Unresolved items
- Evidence references

## 5. Phase 1: Parallel Discovery

The following agents can run independently.

### 5.1 Discovery Agent

Scan the Spring Boot application and create the baseline inventory.

Extract:

- Packages
- Classes and interfaces
- Controllers
- Services and implementations
- Repositories
- Entities
- DTOs
- Mappers
- Configuration
- External clients
- Transaction annotations
- JPA annotations
- Database tables
- Existing module-like package structures

Output:

```text
source-inventory.json
discovery-report.md
```

This agent inventories the application but does not decide boundaries.

### 5.2 Static Analysis Agent

Build the class-level dependency graph.

Extract:

- Imports
- Field types
- Method calls
- Constructor calls
- Inheritance and interfaces
- Repository access
- Entity references
- Foreign-key relationships
- Transaction participation
- Incoming and outgoing dependencies

Example evidence record:

```json
{
  "source": "com.example.order.OrderService",
  "target": "com.example.payment.PaymentRepository",
  "type": "DIRECT_REPOSITORY_ACCESS",
  "source_file": "OrderService.java",
  "line": 42,
  "confidence": 0.96
}
```

Output:

```text
dependency-graph.json
edge-evidence.json
```

### 5.3 Semantic Analysis Agent

Create semantic descriptions and embeddings for classes, packages, preliminary clusters, and candidate service anchors.

Class description should include:

- Fully qualified class name
- Package name
- Role and annotations
- Fields and field types
- Method names and signatures
- Entity and repository references
- Transaction annotations
- Javadocs and comments

Example:

```text
Class: OrderService
Package: com.shop.order.service
Role: service
Annotations: @Service, @Transactional
Fields: OrderRepository, PaymentClient, InventoryService
Methods: createOrder, cancelOrder, calculateTotal
References: Order, OrderItem, Payment
```

Output:

```text
semantic-class-data.json
```

The agent may use an embedding model such as:

- `sentence-transformers/all-MiniLM-L6-v2`
- `BAAI/bge-small-en-v1.5`

Embeddings should be deterministic for a fixed model and input. Store the model name, version, and input text hash.

## 6. Phase 2: Candidate Boundary Synthesis

### 6.1 Service Boundary Agent

Treat any pre-existing groups (including groups from a prior analysis run) as provisional seeds only. Discover and refine candidate business domains using:

- Service anchors
- Semantic embeddings
- Package affinity
- Structural dependencies
- Transaction relationships
- Entity ownership
- Shared-class detection
- Initial Louvain clusters

Do not preserve redundant seed groups merely to match the original output, and do not optimize for a particular number of domains. Merge groups when multiple independent signals support one cohesive capability (for example, overlapping responsibilities, shared ownership of invariants and writes, strong internal cohesion, and no convincing independent boundary). Keep groups separate when evidence supports distinct capabilities, data ownership, invariants, or lifecycle, even if their names or implementation details are similar. Split a group when it contains separable capabilities with materially different ownership or dependency patterns. Where evidence is inconclusive, report alternative groupings or mark the boundary uncertain instead of forcing a merge or split.

For each candidate module, record:

- Candidate name
- Service anchor classes
- Controllers
- Repositories
- Entities
- DTOs
- External integrations
- Incoming dependencies
- Outgoing dependencies
- Transaction boundaries
- Database tables accessed
- Ambiguous classes
- Shared classes
- Confidence
- Source seed/cluster IDs and any merge or split decisions, with evidence
- Boundary uncertainties and plausible alternatives

Describe the result as an approximate business-domain map. Record the evidence and confidence behind each boundary; do not imply that discovered groups are final bounded contexts or independently deployable services.

Example:

```json
{
  "module": "order",
  "anchors": ["OrderService", "OrderServiceImpl"],
  "members": ["OrderController", "OrderRepository", "Order"],
  "confidence": 0.82,
  "ambiguous_classes": ["User"],
  "cross_module_dependencies": ["PaymentService"]
}
```

Classify each candidate group as:

- `BUSINESS_MODULE`
- `SHARED_KERNEL`
- `PLATFORM`
- `EXTERNAL_INTEGRATION`
- `UNCERTAIN`

### 6.2 Semantic Assignment

For a class $x$ and service anchor $s$, calculate semantic similarity:

$$
S_{semantic}(x,s) = \cos(\mathbf{e}_x, \mathbf{e}_s)
$$

Use semantic similarity together with structural evidence. It should not independently override strong database or transaction evidence.

A practical affinity model is:

$$
A(x,s) =
0.40R(x,s) +
0.20T(x,s) +
0.15P(x,s) +
0.15S_{semantic}(x,s) +
0.10N(x,s)
$$

Where:

- $R$ = reference and method-call affinity
- $T$ = transaction and data co-access affinity
- $P$ = persistence and entity affinity
- $S_{semantic}$ = embedding cosine similarity
- $N$ = package and name affinity

The coefficients are configuration values and must be recorded with the output.

### 6.4 LLM Role Classification Agent

Use an LLM to classify classes into implementation-independent roles rather than relying only on suffixes such as `*Service` or `*Repository`.

Allowed roles:

- `BUSINESS_SERVICE`
- `ENTITY`
- `REPOSITORY`
- `CONTROLLER`
- `DTO`
- `CONFIGURATION`
- `EXTERNAL_INTEGRATION`
- `SHARED_KERNEL`
- `CROSS_CUTTING`
- `UNKNOWN`

The prompt must include only extracted evidence such as class descriptions, annotations, fields, methods, references, and package names. The LLM must not invent relationships.

Required output:

```json
{
  "class_id": "com.example.order.OrderService",
  "role": "BUSINESS_SERVICE",
  "business_capabilities": ["order creation", "order cancellation"],
  "domain_terms": ["order", "payment"],
  "confidence": 0.91,
  "evidence": ["@Service", "createOrder", "OrderRepository"],
  "review_required": false
}
```

Output:

```text
llm-role-classifications.json
```

### 6.5 LLM Cluster Merge Agent

Use this agent after initial Louvain clustering and semantic embedding generation. Treat each preliminary cluster as a candidate group, including singleton clusters.

The prompt should include:

- Cluster members
- Service anchors
- Class roles
- Package paths
- Structural edges
- Entity and repository relationships
- Database tables
- Transaction boundaries
- Embedding similarity
- Existing Louvain cluster IDs

Allowed decisions:

- `MERGE`
- `KEEP_SEPARATE`
- `SHARED_DEPENDENCY`
- `SPLIT_CLUSTER`
- `REVIEW_REQUIRED`

Example output:

```json
{
  "left_cluster": 12,
  "right_cluster": 31,
  "decision": "KEEP_SEPARATE",
  "reason": "Payment is a distinct capability called by Order rather than a shared owner.",
  "confidence": 0.86,
  "evidence_ids": ["edge-104", "table-payment-1"],
  "review_required": false
}
```

The agent must not merge clusters solely because names are similar, nor keep them separate just because an earlier run emitted separate groups. Merge/split recommendations must combine semantic evidence with structural, transactional, package, responsibility, and data-ownership evidence. Record the rationale and evidence IDs for each decision; if the evidence conflicts, use `REVIEW_REQUIRED` rather than targeting a desired cluster count.

Output:

```text
cluster-merge-decisions.json
```

For merged cluster centroids:

$$
\mathbf{c}_k = \frac{1}{|C_k|}\sum_{x \in C_k}\mathbf{e}_x
$$

Use centroid similarity as evidence, not as an automatic merge rule.

### 6.6 LLM Ambiguity Resolution Agent

Use this agent only for classes with multiple strong candidate owners, shared entities, cross-module services, or conflicting package and dependency evidence.

Example input:

```text
Class: User
Candidates: User, Auth, Order
Evidence:
- Written by UserService
- Read by AuthService
- Read by OrderService
- User invariants are enforced in UserService
```

Required output:

```json
{
  "class_id": "User",
  "owner": "User",
  "consumers": ["Auth", "Order"],
  "decision": "ASSIGN_OWNER",
  "confidence": 0.88,
  "reason": "User owns writes and invariants; Auth and Order are consumers.",
  "review_required": false
}
```

Low-confidence decisions remain shared or go to human review.

Output:

```text
ambiguity-decisions.json
```

## 6.7 LLM Decision Policy

Use the following policy for all LLM decisions:

```text
High confidence + strong evidence
    -> Accept automatically

Medium confidence
    -> Accept provisionally and report

Low confidence or conflicting evidence
    -> Human review

No supporting evidence
    -> Keep separate or mark unknown
```

Every LLM result must record:

- Model name and version
- Prompt version
- Temperature and generation settings
- Input evidence IDs
- Raw response or response hash
- Parsed structured decision
- Confidence
- Review status

LLM output must be schema-validated before it affects candidate membership, ownership, or migration code.

### 6.3 Shared and Ambiguous Classes

Classes such as the following should not automatically belong to a business module:

```text
SecurityConfig
ApiResponse
BaseEntity
CommonMapper
AuditService
```

Classify them as `SHARED_KERNEL`, `PLATFORM`, or `CROSS_CUTTING`.

If a class has similar affinity to multiple modules, record it as ambiguous:

$$
|A(x,s_1) - A(x,s_2)| < \epsilon
$$

Ambiguous classes require human review or remain shared dependencies during the first migration stage.

## 7. Phase 3: Database Ownership Analysis

### 7.1 Database Ownership Agent

Build a table-access matrix using:

- `@Entity`
- `@Table`
- Repository interfaces
- JPQL queries
- Native SQL
- `JdbcTemplate`
- Entity relationships
- Migration files
- Foreign keys
- Transaction participants

Example:

| Table | Reading Modules | Writing Modules | Candidate Owner | Risk |
|---|---|---|---|---|
| `orders` | Order, Payment | Order, Payment | Order | High |
| `users` | User, Auth, Order | User, Auth | User/Auth review | High |
| `products` | Product, Cart, Order | Product | Product | Medium |

Classify each table as:

- Single-owner
- Multi-writer
- Shared reference data
- Cross-cutting/audit
- Unclear

Output:

```text
database-ownership.json
```

### 7.2 Ownership Decision Rules

Every business table should have one owner before microservice extraction.

The owner controls:

- Entity model
- Repository
- Writes
- Invariants
- Schema changes
- Transaction boundaries

For shared data, choose explicitly between:

- Owner API
- Published domain events
- Read-only projection
- Replicated read model
- Deliberately shared reference-data module

Do not create a generic shared database module that continues to own all data indirectly.

### 7.3 LLM Database Ownership Advisor

Use an LLM to interpret a table-access matrix when ownership is ambiguous or there are multiple writers. The LLM receives extracted writes, reads, entities, transactions, and invariants; it does not infer facts absent from the evidence.

Example output:

```json
{
  "table": "users",
  "owner": "user",
  "secondary_readers": ["auth", "order"],
  "ownership_strategy": "OWNER_API_PLUS_READ_MODEL",
  "risk": "HIGH",
  "reason": "User owns profile invariants; Auth should consume identity data without writing profile state.",
  "evidence_ids": ["write-user-4", "entity-user-1"],
  "review_required": true
}
```

Output:

```text
database-ownership-advice.json
```

## 8. Phase 4: Create Module Boundaries in the Monolith

### 8.1 Module Boundary Agent

Reorganize the code into explicit module packages while keeping one deployable application.

Example:

```text
com.example.ecommerce.order/
  api/
  application/
  domain/
  infrastructure/

com.example.ecommerce.payment/
  api/
  application/
  domain/
  infrastructure/
```

Recommended responsibilities:

- `api`: public controllers and module-facing interfaces
- `application`: use cases and transaction orchestration
- `domain`: entities and business rules
- `infrastructure`: repositories and external adapters

Migration sequence for each module:

1. Move service classes.
2. Move repositories.
3. Move entities where ownership is clear.
4. Move DTOs and mappers.
5. Define the module public API.
6. Mark unresolved cross-module access as migration work.
7. Compile and run focused validation.

Do not perform a large one-time rewrite. Move one module or cohesive slice at a time.

## 9. Phase 5: Enforce Dependency Rules

### 9.1 Dependency Rules Agent

Define allowed module dependencies:

```text
module.api -> module.application
module.application -> module.domain
module.infrastructure -> module.domain
module A -> module B public API only
```

Forbidden dependencies:

```text
module A -> module B repository
module A -> module B entity
module A -> module B private implementation
module A -> module B database table
controller -> another module repository
```

Possible enforcement mechanisms:

- ArchUnit rules
- Maven or Gradle dependency rules
- Package visibility
- Java module boundaries
- Static architecture checks in CI
- Code review rules

Track violations by severity:

- Direct repository access
- Direct entity access
- Cross-module transaction
- Cyclic dependency
- Shared mutable utility
- Direct database access

Output:

```text
dependency-rules.json
architecture-violations.json
```

Example rule:

```text
Order may call Payment's public API,
but Order may not import PaymentRepository or PaymentEntity.
```

## 10. Phase 6: Move Data Ownership

### 10.1 Data Migration Agent

For each business table:

1. Select the owning module.
2. Move the entity and repository into the owner module.
3. Replace external writes with the owner API.
4. Replace direct entity references with IDs or read models.
5. Move business invariants into the owner.
6. Add temporary compatibility adapters if necessary.
7. Monitor remaining direct SQL or repository usage.
8. Remove compatibility access after migration.

Example:

```text
Order owns orders and order_items.
Payment may request payment status,
but cannot update orders directly.
```

Every unauthorized write should become a tracked migration task.

## 11. Phase 7: Replace Direct Calls with Internal APIs

### 11.1 API Contract Agent

Convert cross-module implementation calls into explicit contracts.

Before:

```text
OrderService -> PaymentRepository
```

After:

```text
OrderApplicationService -> PaymentPort
PaymentApplicationService implements PaymentPort
```

Define contracts using:

- Commands
- Queries
- Results
- Domain events
- Integration events
- Explicit error types

Example:

```java
public interface PaymentPort {
    PaymentResult authorizePayment(AuthorizePaymentCommand command);
}
```

Rules:

- Do not expose entities across module boundaries.
- Pass IDs, immutable commands, and response DTOs.
- Keep transactions local where possible.
- Avoid returning repository objects.
- Define timeout and failure behavior, even for in-process calls.
- Record synchronous calls and events in the dependency graph.

Use events for workflows such as:

```text
OrderPlaced
PaymentAuthorized
InventoryReserved
OrderCancelled
```

Use synchronous APIs when the caller requires an immediate result.

Output:

```text
api-contracts.json
```

Example contract record:

```json
{
  "consumer": "order",
  "provider": "payment",
  "operation": "authorizePayment",
  "communication": "SYNCHRONOUS_PORT",
  "request": "AuthorizePaymentCommand",
  "response": "PaymentAuthorizationResult"
}
```

### 11.2 LLM API Contract Advisor

Use an LLM to recommend whether each cross-module dependency should become:

- Synchronous command
- Synchronous query
- Domain event
- Integration event
- Read model
- Shared value object

Example decision:

```json
{
  "consumer": "order",
  "provider": "payment",
  "operation": "authorizePayment",
  "communication": "SYNCHRONOUS_COMMAND",
  "reason": "Checkout requires an immediate authorization result.",
  "confidence": 0.90,
  "evidence_ids": ["call-order-payment-2"],
  "review_required": false
}
```

The advisor recommends contracts; the implementation agent creates them only after review.

Output:

```text
api-contract-advice.json
```

### 11.3 LLM Domain Naming Agent

Use an LLM to suggest human-readable names after membership and ownership are finalized. Names must never affect graph weights, class assignment, or table ownership.

Input:

```text
OrderService, OrderRepository, OrderController, Order, OrderItem
```

Possible output:

```json
{
  "name": "Order Management",
  "alternatives": ["Order Fulfillment"],
  "reason": "The group creates, updates, and manages orders and order items.",
  "confidence": 0.93
}
```

Output:

```text
domain-names.json
```

## 12. Phase 8: Migration Planning

### 12.1 Migration Planning Agent

Create an ordered migration plan. Each step must include:

- Module name
- Files to move
- Package changes
- Dependency violations
- Database risks
- API changes
- Required tests
- Rollback strategy
- Validation commands
- Extraction readiness

Example:

```json
{
  "step": 1,
  "module": "inventory",
  "goal": "Create internal inventory boundary",
  "risk": "LOW",
  "changes": [
    "Move InventoryRepository",
    "Expose InventoryPort",
    "Remove direct entity imports"
  ],
  "rollback": "Revert package move and adapter"
}
```

Prioritize modules with:

- Clear data ownership
- Low coupling
- Few cross-module transactions
- Stable APIs
- Low operational risk

## 13. Phase 9: Implementation Agents

Use separate implementation agents for separate bounded tasks.

### Module Boundary Agent

Creates packages and moves classes.

### Dependency Enforcement Agent

Adds architecture rules and CI checks.

### Data Ownership Agent

Moves repositories and entities, then removes unauthorized writes.

### API Migration Agent

Replaces direct implementation calls with ports, commands, queries, and events.

### Compatibility Agent

Creates temporary adapters so the application remains runnable during migration.

Each agent must edit only its assigned files and report all modified files.

## 14. Phase 10: Validation Agent

Run validation after every migration step.

Validate:

- Compilation
- Unit tests
- Integration tests
- Application startup
- Architecture rules
- Database access rules
- No cyclic dependencies
- No direct cross-module repository access
- No unauthorized table writes
- API contract compatibility
- Transaction boundary behavior

Output:

```text
validation-report.json
```

The orchestrator must block the next migration step if validation fails.

## 15. Phase 11: Reporting Agent

Generate human-readable reports:

```text
reports/
  baseline.html
  candidate-modules.html
  database-ownership.html
  dependency-violations.html
  migration-progress.html
  final-boundaries.html
```

The final report should show:

- Discovered approximate domain and its confidence
- Source candidate groups/clusters and their merge/split history
- Candidate module
- Final module
- Owned classes
- Owned tables
- Public APIs
- Incoming dependencies
- Outgoing dependencies
- Shared classes
- Cross-boundary classes
- Migration status
- Remaining violations
- Extraction readiness score

## 16. Execution Schedule

### Stage A: Parallel Analysis

Run concurrently:

```text
Discovery Agent
Static Analysis Agent
Semantic Analysis Agent
Database Ownership Agent
```

### Stage B: Boundary Synthesis

Run sequentially:

```text
LLM Role Classification Agent
Service Boundary Agent
LLM Cluster Merge Agent
LLM Ambiguity Resolution Agent
Dependency Rules Agent
LLM Database Ownership Advisor
API Contract Agent
LLM API Contract Advisor
LLM Domain Naming Agent
```

The LLM agents must run after the relevant evidence artifacts exist. They must not operate directly on raw source without the normalized evidence context produced by the discovery and static-analysis agents.

### Stage C: Human Review Gate

Review and approve:

- Candidate modules
- LLM role classifications with low confidence
- Cluster merge and split decisions
- Ambiguous class ownership
- Table ownership
- LLM database ownership recommendations
- Shared classes
- High-risk dependencies
- Cross-module transactions
- Proposed API contracts
- LLM API communication recommendations

Do not modify production code before this approval.

### Stage D: Modular Monolith Migration

Run one module at a time:

```text
Module Boundary Agent
Dependency Enforcement Agent
Data Ownership Agent
API Migration Agent
Compatibility Agent
Validation Agent
```

### Stage E: Microservice Extraction

Only after modular-monolith validation:

```text
Service Readiness Agent
Deployment Agent
Data Separation Agent
Contract Testing Agent
Operational Validation Agent
```

Extract one low-risk module first and observe it before extracting more modules.

## 16.1 LLM Safeguards

LLMs are advisory and evidence-bound. They must not:

- Invent dependencies, tables, transactions, or class ownership facts.
- Merge classes or clusters solely because their names are similar.
- Override strong database write or transaction evidence without review.
- Modify production code directly as part of classification.
- Make a final microservice extraction decision.
- Return free-form text as the only decision output.

Every decision must be structured JSON, schema-validated, and linked to evidence IDs. Unknown or unsupported decisions must be represented explicitly as `UNKNOWN` or `REVIEW_REQUIRED`.

### LLM evaluation

Evaluate LLM-assisted results across applications using:

- Manual agreement with known modules, where available
- Percentage of `REVIEW_REQUIRED` decisions
- Precision of role classifications
- Precision of cluster merges
- False merge rate
- False split rate
- Database-owner agreement
- API recommendation agreement
- Boundary stability across model versions and prompts
- Reduction in ambiguous classes without increased cross-module coupling

Run at least one baseline comparison:

```text
Deterministic rules only
  vs.
Deterministic evidence plus embeddings
  vs.
Deterministic evidence plus embeddings plus LLM review
```

Do not use the number of discovered domains as a target or a quality metric by itself. Compare domain-size distribution, singleton rate, cross-domain dependencies, modularity, evidence coverage, stability, and manual boundary quality; investigate both over-fragmentation and over-merging.

## 16.2 LLM Failure and Fallback Policy

If the LLM is unavailable, returns invalid JSON, exceeds a timeout, or produces low-confidence output:

1. Preserve the deterministic result.
2. Mark the affected decision as `REVIEW_REQUIRED`.
3. Do not silently apply a default merge or ownership decision.
4. Continue only when the orchestrator's policy permits provisional results.

This makes the migration reproducible without requiring an LLM for every run.

## 17. Service Readiness Criteria

A candidate module is ready for independent extraction only when:

- It has a coherent business capability.
- It owns its data or has an explicit data access strategy.
- It has no direct access to another module’s repositories or entities.
- Its cross-module dependencies use explicit APIs or events.
- Its transactions are local or deliberately distributed.
- It has stable API contracts.
- It can be built and tested independently.
- It has independent deployment configuration.
- It has operational monitoring and failure handling.
- Its rollback and data migration plans are documented.

## 18. Important Distinction

Groups produced by discovery should initially be treated as:

```text
Provisional candidate business domains or modular components
```

Their count may change as redundant groups are consolidated and evidence-based splits are made. Do not label them final bounded contexts or microservices until ownership, dependencies, APIs, and readiness have been reviewed.

They should not immediately be treated as production microservices.

The actual migration decision is based on:

- Cohesion
- Coupling
- Data ownership
- Transaction boundaries
- API stability
- Operational readiness
- Migration risk

A candidate with high cohesion but shared tables and cross-module transactions is not yet ready for independent deployment.

## 19. Final Success Criteria

The migration is successful when:

1. The monolith has explicit module boundaries.
2. Each business table has a documented owner.
3. Cross-module dependency violations are visible and decreasing.
4. Direct entity and repository access across modules is removed.
5. Internal APIs and events replace implementation-level calls.
6. The application remains buildable and runnable after each change.
7. Candidate modules have measurable extraction-readiness scores.
8. At least one low-risk module can be extracted independently with tested contracts.
9. The final report clearly distinguishes candidate modules, validated modules, and extracted microservices.
