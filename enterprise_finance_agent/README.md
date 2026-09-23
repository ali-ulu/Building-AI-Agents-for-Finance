# Enterprise Finance Agent

Production-shaped foundation for a large-company finance copilot built from the strongest patterns already present in this repository.

## Goal

Build a read-first, auditable multi-agent finance system that can answer management questions, research evidence, validate calculations, explain variances, and prepare finance outputs without giving an LLM uncontrolled authority over money-moving actions.

The first production target is a **read-only CFO/FP&A copilot**. Any future write action must pass explicit policy and human-approval gates.

## Architecture

The system uses a **Finance Supervisor** as the single user-facing orchestrator. Specialist agents operate behind it as bounded workers:

- FP&A Analyst
- Accounting & Close Analyst
- Treasury & Liquidity Analyst
- Risk & Controls Analyst
- External Research Analyst
- Internal Knowledge Analyst
- Reporting Analyst
- Independent Validator

The manager pattern is intentionally preferred over free-form handoffs for core finance workflows. It gives one place to enforce policy, budgets, provenance, rate limits, and approval requirements.

## What we reuse from the book repository

- Chapter 2: working/episodic memory, evaluator-optimizer, sequential workflows
- Chapter 5: planner -> researcher -> validator -> synthesizer
- Chapter 7: manager + specialist agents and parallel execution
- Chapter 8: investment committee and adversarial review patterns
- Chapter 10: agentic RAG over internal finance documents
- Chapter 11: evaluation harness, drift, audit logs, model-risk reporting
- Chapter 12: observability, guardrails, cost control, retries, idempotency, circuit breakers, deployment/versioning

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Safety model

1. Read-only by default.
2. No payment, transfer, journal posting, vendor-master change, or bank instruction can be executed by an agent in the foundation release.
3. Deterministic code owns calculations, limits, reconciliations, approvals, and policy checks.
4. LLMs may summarize, classify, research, explain, plan, and draft.
5. Every material number must carry provenance and an as-of timestamp.
6. Missing data is surfaced, never silently estimated.
7. High-impact actions require segregation of duties and explicit human approval.

## Initial package

The package currently establishes the enterprise contracts:

- typed finance requests and evidence
- action/risk classification
- approval policy
- deterministic execution gate
- auditable orchestration result

The next implementation slice will add live data adapters and OpenAI Agents SDK specialists behind the same contracts.

## Run tests

```bash
cd enterprise_finance_agent
python -m pip install -e ".[dev]"
pytest
```
