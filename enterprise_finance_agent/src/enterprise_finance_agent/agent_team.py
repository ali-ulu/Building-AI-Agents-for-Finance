"""Multi-agent team definitions.

The supervisor remains the only user-facing agent. Specialists are exposed
as bounded tools so governance and final synthesis stay centralized.
Data access will be added through narrow adapter tools in the next slice.
"""

from __future__ import annotations

import os

from agents import Agent


MODEL = os.getenv("FINANCE_AGENT_MODEL")
if not MODEL:
    raise RuntimeError(
        "Set FINANCE_AGENT_MODEL to the approved model for this environment."
    )


fpna_analyst = Agent(
    name="FP&A Analyst",
    model=MODEL,
    instructions=(
        "Analyze budget, actuals, forecast, KPI and scenario evidence supplied "
        "to you. Explain material drivers and quantify bridges. Never invent "
        "missing figures. Clearly separate reported data from interpretation."
    ),
)

accounting_analyst = Agent(
    name="Accounting & Close Analyst",
    model=MODEL,
    instructions=(
        "Analyze accounting and close evidence supplied to you: trial-balance "
        "movements, reconciliations, close exceptions and policy context. "
        "Do not claim a posting was made. Drafts must be labeled as drafts."
    ),
)

treasury_analyst = Agent(
    name="Treasury & Liquidity Analyst",
    model=MODEL,
    instructions=(
        "Analyze cash, liquidity, debt, covenant, interest-rate and FX evidence "
        "supplied to you. Identify concentration and timing risks. Do not "
        "initiate or imply execution of a payment, transfer or bank instruction."
    ),
)

risk_analyst = Agent(
    name="Risk & Controls Analyst",
    model=MODEL,
    instructions=(
        "Review supplied finance evidence for control breaches, policy issues, "
        "segregation-of-duties concerns, stale data and unsupported claims. "
        "Prefer deterministic findings when they are supplied."
    ),
)

research_analyst = Agent(
    name="External Research Analyst",
    model=MODEL,
    instructions=(
        "Analyze supplied external market and company research. Track source "
        "dates, distinguish external evidence from internal books and records, "
        "and flag facts that need freshness verification."
    ),
)

knowledge_analyst = Agent(
    name="Internal Knowledge Analyst",
    model=MODEL,
    instructions=(
        "Answer from supplied governed internal-document evidence only. Quote "
        "policy meaning accurately, preserve document/version references, and "
        "say when the evidence is insufficient."
    ),
)

reporting_analyst = Agent(
    name="Reporting Analyst",
    model=MODEL,
    instructions=(
        "Turn validated evidence into concise CFO, board or management reporting. "
        "Preserve periods, entities, currencies, provenance, validation warnings "
        "and data gaps. Never smooth over a failed control."
    ),
)

finance_supervisor = Agent(
    name="Finance Supervisor",
    model=MODEL,
    instructions=(
        "You are the single user-facing orchestrator for a large-company finance "
        "copilot. Use specialist tools for bounded analysis. Keep reported facts, "
        "external research and model commentary separate. Never fabricate a "
        "number. Never execute or imply execution of money movement, privileged "
        "master-data changes or accounting postings. Respect deterministic policy "
        "and validation results supplied by the application. Material conclusions "
        "must preserve provenance, period, entity, currency and data gaps."
    ),
    tools=[
        fpna_analyst.as_tool(
            tool_name="analyze_fpna",
            tool_description="Analyze budget, actuals, forecasts, KPIs and scenarios.",
        ),
        accounting_analyst.as_tool(
            tool_name="analyze_accounting_close",
            tool_description="Analyze accounting, reconciliations and close evidence.",
        ),
        treasury_analyst.as_tool(
            tool_name="analyze_treasury_liquidity",
            tool_description="Analyze cash, liquidity, debt, rates and FX evidence.",
        ),
        risk_analyst.as_tool(
            tool_name="review_finance_controls",
            tool_description="Review evidence and findings for finance/control risk.",
        ),
        research_analyst.as_tool(
            tool_name="analyze_external_research",
            tool_description="Analyze dated external market/company research.",
        ),
        knowledge_analyst.as_tool(
            tool_name="analyze_internal_knowledge",
            tool_description="Interpret governed internal policy/document evidence.",
        ),
        reporting_analyst.as_tool(
            tool_name="prepare_management_report",
            tool_description="Prepare a CFO/board-ready report from validated evidence.",
        ),
    ],
)
