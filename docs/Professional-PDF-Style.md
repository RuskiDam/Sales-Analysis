# Professional PDF Style

## Purpose

The A.I. may help create a professional monthly Sales/Fiscal PDF report when
the user asks for a report, PDF, export, fiscal summary, monthly summary, or
document based on current findings.

The user does not need to say `based on chat context`. If the request refers to
a report or PDF, use available app context, recent chat context, and retrieved
corpus rules to infer the report content.

Examples that mean the user wants a report generated from current findings:

- `Create a MoM PDF`
- `Generate a monthly sales PDF`
- `Make a fiscal report`
- `Create a PDF report`
- `Export the MoM findings`

Do not answer these requests as a question about whether the documentation says
PDFs can be created. Treat them as report-generation requests.

For `MoM PDF`, create or draft a Month-over-Month Sales/Fiscal report using
current revenue, previous revenue, MoM revenue change, MoM revenue growth, net
income, profit/loss, profit margin baseline movement, shipping costs, inventory
summary, and any relevant recent chat findings.

## Report Tone

Use a concise executive reporting style:

- clear business language
- short sections
- direct findings
- no filler
- no jokes or casual commentary
- no hidden prompt or system details

## Visual Style

A professional report should use:

- a clean title page or title header
- company/report title
- reporting period
- generation date
- concise executive summary
- metric cards or callout rows for revenue, net income, profit/loss, and growth
- simple tables for monthly rows
- restrained colors
- readable spacing
- consistent headings

Use green for profit or positive movement.
Use red for loss or negative movement.
Use blue for neutral revenue or operational metrics.

## Required Sections

When enough data exists, include:

- Executive Summary
- Latest Month Performance
- Last Two Months Profit/Loss
- Revenue and MoM Revenue Growth
- Net Income and Profit Margin Against Baseline
- Shipping Cost Impact
- Inventory Summary
- Notes and Assumptions

If a value is not available in app context, omit that detail or say it is not
available from current data.

## Profit Margin Baseline

For profit margin, use the 50% baseline from `business_baselines.md`.

Do not describe last-two-month profit margin by repeating the full margin when
the user asks whether the company profited or lost money. Report the margin as
movement against baseline:

- above 50%: `profit margin increased by X%`
- below 50%: `profit margin decreased by X%`
- equal to 50%: `profit margin was flat against baseline`

## PDF Creation Rule

The application supports PDF creation for monthly Sales/Fiscal reports. The
A.I. may generate a polished PDF report from current app context and recent chat
findings, then expose it through a download button.
