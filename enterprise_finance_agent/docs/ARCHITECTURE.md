# Enterprise Finance Agent Architecture

## 1. Design objective

This is not an autonomous trading bot and not a general chatbot with finance prompts. It is a controlled finance operating layer for a large company.

The system should support questions such as:

- What drove EBITDA variance versus budget this month?
- What is our 13-week liquidity outlook?
- Which receivables create the largest cash-risk concentration?
- Where did working capital deteriorate and why?
- Which policy explains this accounting treatment?
- What changed in interest-rate, FX, supplier, or customer risk?
- Prepare a management pack with traceable numbers and data gaps.

## 2. Core topology

```text
User / Finance Team
        |
        v
+------------------------+
| Finance Supervisor     |
| intent + scope + RBAC  |
+-----------+------------+
            |
   +--------+--------+----------------+----------------+
   |                 |                |                |
   v                 v                v                v
 FP&A            Accounting       Treasury       Research/RAG
 Analyst          Analyst          Analyst         Analysts
   |                 |                |                |
   +-----------------+----------------+----------------+
                     |
                     v
             Deterministic Validator
                     |
                     v
               Reporting Agent
                     |
                     v
            Policy / Approval Gate
                     |
          +----------+----------+
          |                     |
       Read result          Action proposal
                                |
                           Human approval
```

The Finance Supervisor owns the user-facing answer. Specialists should normally be invoked as tools rather than taking over the conversation.

## 3. Specialist responsibilities

### Finance Supervisor

Owns intent classification, plan selection, specialist routing, budget limits, final synthesis, and user communication. It must not perform material finance calculations itself when a deterministic service is available.

### FP&A Analyst

Budget versus actuals, forecast updates, driver trees, scenario analysis, KPI bridges, business-unit performance, and management commentary.

### Accounting & Close Analyst

Trial-balance analysis, reconciliations, period-close exceptions, account movement explanations, draft journal support, and accounting-policy retrieval. Posting remains out of scope until an approval workflow exists.

### Treasury & Liquidity Analyst

Cash position, 13-week cash forecast, debt maturities, covenant headroom, interest exposure, FX exposure, bank concentration, and liquidity alerts.

### Risk & Controls Analyst

Policy checks, segregation-of-duties rules, threshold breaches, anomalous transactions, control exceptions, and escalation decisions.

### External Research Analyst

Market, rates, FX, peers, suppliers, customers, regulatory context, and current external evidence. External evidence is separated from internal books and records.

### Internal Knowledge Analyst

Agentic RAG across accounting manuals, treasury policies, contracts, board material, finance SOPs, and approved internal knowledge.

### Reporting Analyst

Produces CFO summaries, board packs, variance narratives, audit-ready evidence tables, and machine-readable structured outputs.

### Independent Validator

Checks completeness, arithmetic, cross-source consistency, period alignment, currency/unit consistency, stale data, unsupported claims, and required approvals. Deterministic rules run before any LLM judge.

## 4. Reuse map from this repository

| Existing material | Enterprise use |
| --- | --- |
| Chapter 2 working + episodic memory | session context and reviewed historical finance cases |
| Chapter 2 evaluator-optimizer | bounded revision loop |
| Chapter 5 planner/researcher | dependency-aware research DAG |
| Chapter 5 deterministic validator | hard financial/data-quality checks |
| Chapter 5 synthesizer | structured management memo |
| Chapter 7 manager + specialists | primary multi-agent orchestration |
| Chapter 7 parallel analysis | business-unit/company parallelism |
| Chapter 8 investment committee | high-stakes scenario review |
| Chapter 8 adversarial debate | challenge optimistic/pessimistic assumptions |
| Chapter 10 agentic RAG | internal policies and financial documents |
| Chapter 11 evaluation harness | regression gates, drift, model-risk evidence |
| Chapter 12 observability + guardrails | tracing, red-team, cost, reliability, deployment |

## 5. Data architecture

Agents never receive unrestricted database credentials. Tools expose narrow, typed queries.

Recommended adapter boundaries:

- General Ledger / ERP adapter
- Budget & Forecast adapter
- AR adapter
- AP adapter
- Treasury / Bank adapter
- Procurement adapter
- CRM / Revenue adapter
- HR cost adapter, when authorized
- Document/RAG adapter
- External Market Data adapter

Every returned datum should include, where applicable:

- source_system
- source_record_id
- as_of
- period
- entity
- currency
- unit
- extraction timestamp
- data-quality status

## 6. Control plane

### Access control

Authorization occurs before agent execution. The model does not decide what a user is allowed to see.

Minimum controls:

- SSO identity
- role-based permissions
- legal-entity and business-unit scope
- source-system entitlements
- row/field filtering
- PII and payroll restrictions
- environment separation

### Action classes

- READ: fetch, analyze, explain, compare
- DRAFT: create a proposed journal, forecast change, payment proposal, email, or report
- CONTROLLED_WRITE: update a low-risk system record after approval
- MONEY_MOVEMENT: payment, transfer, bank instruction
- PRIVILEGED_CHANGE: bank master, vendor master, accounting policy, access rights

Foundation permits READ and DRAFT only. CONTROLLED_WRITE and above are denied until workflow-specific approval controls exist.

### Approval

High-impact actions need:

- explicit approver identity
- action payload fingerprint
- amount/currency/entity scope
- expiry
- reason
- segregation-of-duties check
- immutable audit event

## 7. Validation order

Validation is deliberately layered:

1. Schema validation
2. Authorization/scope validation
3. Freshness and period checks
4. Currency/unit normalization
5. Arithmetic/reconciliation checks
6. Source/provenance completeness
7. Finance policy rules
8. Cross-source consistency
9. LLM qualitative review
10. Human approval where required

LLM review never replaces steps 1-8.

## 8. Memory

Use three separate memory classes:

- Working memory: one finance session/run
- Case memory: reviewed prior analyses and approved outcomes
- Knowledge memory: governed internal documents

Do not blend raw conversations into trusted finance knowledge. Promotion into case memory should require validation and an explicit review state.

## 9. Observability

Each run must record:

- request ID and user identity reference
- active agent/version
- prompt/config version
- tool calls
- data sources and timestamps
- latency
- token/cost metrics
- validation results
- approval decisions
- final output fingerprint
- errors/degradation path

Sensitive tool payloads should be redacted or hashed according to retention policy.

## 10. Reliability

Use:

- retry with bounded exponential backoff
- explicit timeouts
- idempotency keys for side-effecting tools
- circuit breakers
- cached reference data
- bounded concurrency
- fallback/degradation modes
- resumable checkpoints for long analyses

## 11. Delivery phases

### Phase A: CFO read-only copilot

Deliver read-only analysis over sample/adapted company data:
- P&L and balance-sheet variance
- cash/liquidity
- AR/AP working capital
- policy RAG
- management reporting
- deterministic validation and audit trail

### Phase B: Forecasting and scenario engine

Add:
- rolling forecast
- scenario assumptions
- sensitivity analysis
- challenge agents
- multi-entity consolidation

### Phase C: Controlled workflow actions

Add proposals for:
- journals
- forecast changes
- collections actions
- payment batches

All remain approval-gated.

### Phase D: Enterprise operations

Add:
- production connectors
- SSO/RBAC
- queueing and scheduling
- continuous evaluation
- drift monitoring
- incident response
- model/prompt release governance

## 12. Definition of done for the first production-grade slice

A finance answer is acceptable only when it:

- identifies period/entity/currency
- shows source provenance for material numbers
- distinguishes reported facts from model commentary
- exposes data gaps
- passes deterministic checks
- records an audit event
- can be reproduced from the same versioned inputs
