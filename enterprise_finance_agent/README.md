# Enterprise Finance Agent

Production-shaped foundation for a large-company finance copilot built from the strongest patterns already present in this repository.

## Goal

Build a read-first, auditable multi-agent finance system that can answer management questions, research evidence, validate calculations, explain variances, surface risks and opportunities, run scenarios, and prepare finance outputs without giving an LLM uncontrolled authority over money-moving actions.

The first production target is a **read-only CFO/FP&A copilot**. Any future write action must pass explicit policy and human-approval gates.

## Architecture

The system uses a **Finance Supervisor** as the single user-facing orchestrator. Specialist agents operate behind it as bounded workers:

- FP&A Analyst
- Accounting & Close Analyst
- Treasury & Liquidity Analyst
- Opportunity Intelligence Analyst
- Risk Intelligence Analyst
- Scenario & Forecast Analyst
- External Research Analyst
- Internal Knowledge Analyst
- Reporting Analyst
- Independent Validator

The manager pattern is intentionally preferred over free-form handoffs for core finance workflows. It gives one place to enforce policy, budgets, provenance, rate limits, and approval requirements.

Domain-free chassis lives in `../governed_agent_core` (policy gate, orchestration, audit, auth scope, debate engine). Finance owns calculators, signal policy, prompts and reporting.

## First management workflow

```text
Actual vs Budget -> Root Cause -> Risk Scan -> Opportunity Scan
  -> Scenario -> Debate -> Validator -> CFO Report
```

Arithmetic lives in `calculators.py`. Finance-reviewed thresholds live in `config.py` and are shared by adapters and signal scans.

Important calculation rules:

- variance bridges may receive an independently reported headline variance; unexplained variance is headline minus explained drivers
- volume scenarios use revenue x volume change x contribution margin, never EBITDA as a revenue proxy
- non-zero volume scenarios without a revenue base fail explicitly
- opportunity signals carry overlap groups so working-capital or margin opportunities are not double counted
- CFO reporting shows both gross opportunity envelope and conservative de-duplicated envelope

## Audit

The governed core writes tamper-evident hash-chained JSONL audit events. Each event commits to the previous event hash. Local JSONL is not described as physically immutable; `verify_jsonl_audit_chain()` detects post-write alteration.

For stronger production retention, send the same events to an append-only/WORM-capable external audit store.

## Data adapters

Phase 1 adapters are read-only CSV adapters with typed evidence. AR concentration and risk scans use the same central `FinancePolicyConfig`, preventing threshold drift between ingestion and analysis.

## Regression gates

The test suite includes deterministic unit tests plus a finance-reviewed golden set covering:

- headline vs explained variance
- DSO cash release
- revenue-based volume scenario math
- FX sensitivity
- AR concentration
- opportunity overlap de-duplication
- adversarial debate escalation
- CFO validation
- authorization scope
- audit-chain tamper detection

GitHub Actions runs on finance/core changes for pushes and pull requests, and can also be started manually with `workflow_dispatch`.

## Safety model

1. Read-only by default.
2. No payment, transfer, journal posting, vendor-master change, or bank instruction can be executed by an agent in the foundation release.
3. Deterministic code owns calculations, limits, reconciliations, approvals, and policy checks.
4. LLMs may summarize, classify, research, explain, plan, challenge and draft.
5. Every material number must carry provenance and an as-of timestamp.
6. Missing data is surfaced, never silently estimated.
7. High-impact actions require segregation of duties and explicit human approval.

## Run the demo

```bash
cd enterprise_finance_agent
python -m pip install -e "../governed_agent_core" -e ".[dev,runtime]"
python examples/demo_cfo_pack.py
pytest -q
```
