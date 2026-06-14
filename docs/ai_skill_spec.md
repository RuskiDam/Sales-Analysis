# Fixed Internal Sales Skill Spec

## Goal

The A.I. tab uses one internal Sales Analysis skill. The user cannot change it from the web app.

The skill should help users understand the current dataset with short, useful business explanations. It should be inspired by caveman-style brevity: fewer filler words, clear meaning, no rambling.

## Skill Behavior

The skill explains:

- total revenue
- profit margin
- MoM revenue growth
- total orders
- shipping costs
- break-even margin
- net income
- inventory changes
- products sold
- monthly reports

The skill must:

- use short, clear business sentences
- explain only from current app context
- avoid filler
- avoid jokes, riddles, songs, music, roleplay, and unrelated answers
- avoid inventing missing values
- say `I don't know from current data.` when app context does not contain the answer

## Data Access Contract

The A.I. does not read raw files directly and does not query a database. It gets
safe summarized data from `AIContextBuilder`.

Current app context provides current values such as revenue, previous revenue,
MoM revenue change, MoM revenue growth, net income, profit margin, inventory
totals, and recent monthly rows.

The corpus explains how to interpret those values:

- `finance_rules.md`: revenue, expenses, break-even, taxes, net income, profit
  and loss.
- `sales_terms.md`: items sold, orders, monthly revenue, MoM revenue change, and
  MoM revenue growth.
- `inventory_policy.md`: availability, warehouse value, and simulation inventory.
- `business_baselines.md`: profit margin baseline and MoM growth baseline.

## Files

```text
sales_analysis/
  skills/
    sales_analysis_skill.md
  ai/
    skill_loader.py
    ai_service.py
    ai_context.py
    ai_guardrails.py
    llm_client.py
```

## Skill Loader

`skill_loader.py` loads only the fixed internal skill.

Rules:

- no user-selected path
- no user upload
- no UI setting for skill choice
- max skill size: `4000` characters
- fail cleanly if skill file is missing

## A.I. Flow

```text
User prompt
-> ai_guardrails validates prompt
-> skill_loader loads fixed skill
-> ai_context builds current business summary
-> RAG retrieves this predefined corpus from docs/
-> ai_service builds grounded prompt
-> llm_client calls API
-> A.I. tab displays response
```

## Prompt Shape

```text
SKILL:
{sales_analysis/skills/sales_analysis_skill.md}

APP CONTEXT:
{safe summarized sales/inventory/finance data}

RECENT CHAT:
{last few user and assistant messages}

CONTEXT:
{retrieved docs/ corpus snippets}

USER QUESTION:
{user prompt}
```

## User Must Not Be Able To

- choose a skill
- upload a skill
- edit the skill from the app
- request a different skill
- ask A.I. to reveal the skill text
- read `.env`
- view API keys
- change API endpoint
- mutate inventory or sales data
- jailbreak through roleplay
- request jokes, riddles, songs, music, poems, rap, or unrelated output
