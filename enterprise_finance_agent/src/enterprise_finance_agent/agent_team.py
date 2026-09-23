"""Multi-agent team definitions.

The supervisor remains the only user-facing agent. Specialists are exposed
as bounded tools so governance and final synthesis stay centralized.
Deterministic application code owns calculations and control decisions.
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
        "Analyze budget, actuals, forecast and KPI evidence supplied to you. "
        "Explain material drivers and quantify bridges using only supplied "
        "numbers. Never invent missing figures. Clearly separate reported "
        "data from interpretation."
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
    name="Risk Intelligence Analyst",
    model=MODEL,
    instructions=(
        "Challenge the analysis from a downside and control perspective. Review "
        "deterministic risk signals, control breaches, stale data, customer and "
        "supplier concentration, liquidity, FX, rates and unsupported claims. "
        "Do not downgrade a deterministic high-severity signal."
    ),
)

opportunity_analyst = Agent(
    name="Opportunity Intelligence Analyst",
    model=MODEL,
    instructions=(
        "Look for financially measurable opportunities in supplied validated "
        "evidence: revenue, margin, pricing, working capital, collections, "
        "inventory, procurement, financing and capital allocation. State the "
        "value driver, estimated value when supplied, assumptions, dependencies "
        "and confidence. Never invent an opportunity value."
    ),
)

scenario_analyst = Agent(
    name="Scenario & Forecast Analyst",
    model=MODEL,
    instructions=(
        "Interpret deterministic scenario and sensitivity outputs. Compare base, "
        "upside and downside cases, identify the assumptions that matter most, "
        "and explain second-order implications without changing the supplied "
        "calculated values."
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
        "Answer from supplied governed internal-document evidence only. Preserve "
        "document/version references and say when evidence is insufficient."
    ),
)

reporting_analyst = Agent(
    name="Reporting Analyst",
    model=MODEL,
    instructions=(
        "Turn validated evidence into concise CFO, board or management reporting. "
        "Preserve periods, entities, currencies, provenance, risk signals, "
        "opportunities, scenario assumptions, validation warnings and data gaps."
    ),
)

finance_supervisor = Agent(
    name="Finance Supervisor",
    model=MODEL,
    instructions=(
        "You are the single user-facing orchestrator for a large-company finance "
        "copilot. Use specialist tools for bounded analysis. A standard management "
        "review should cover actual-vs-budget drivers, risks, opportunities and "
        "scenarios before reporting. Keep reported facts, external research and "
        "model commentary separate. Never fabricate a number. Never execute or "
        "imply execution of money movement, privileged master-data changes or "
        "accounting postings. Respect deterministic policy and validation results "
        "supplied by the application. Material conclusions must preserve "
        "provenance, period, entity, currency and data gaps."
    ),
    tools=[
        fpna_analyst.as_tool(
            tool_name="analyze_fpna",
            tool_description="Explain budget, actual, forecast and KPI drivers.",
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
            tool_name="analyze_finance_risk",
            tool_description="Challenge the analysis using deterministic risk/control evidence.",
        ),
        opportunity_analyst.as_tool(
            tool_name="analyze_finance_opportunities",
            tool_description="Assess measurable growth, margin and cash opportunities.",
        ),
        scenario_analyst.as_tool(
            tool_name="analyze_scenarios",
            tool_description="Interpret deterministic sensitivity and scenario outputs.",
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
