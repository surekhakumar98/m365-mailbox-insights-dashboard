# Exchange Online Mailbox Analytics Dashboard — Power BI Build Guide
*(No DAX required — everything below uses drag-and-drop fields, built-in
summarization, and pre-computed columns from the Python/SQL layer.)*

## 1. Data Model

Import these 4 tables and build the following relationships (Model view):

| Table | Grain | Role |
|---|---|---|
| `Mailboxes` | 1 row per mailbox | Snapshot facts (size, quota, activity) |
| `MailFlow` | 1 row per mailbox per day | Daily traffic, now includes a pre-computed `SpamRatePct` column per row |
| `Departments` | 1 row per department | Lookup |
| `Licenses` | 1 row per license SKU | Lookup (includes `MonthlyCostUSD`) |

**Relationships (all 1-to-many, single direction, from lookup → detail):**
- `Departments[DepartmentID]` → `Mailboxes[DepartmentID]`
- `Licenses[LicenseSKU]` → `Mailboxes[LicenseSKU]`
- `Mailboxes[MailboxID]` → `MailFlow[MailboxID]`

Once these relationships exist, Power BI automatically "knows" how to roll numbers
up or down between tables — e.g. dragging `Department` and `MailboxSizeGB` onto
the same chart just works, because of the relationship, not a formula.

You don't need a separate date table for this build — `MailFlow[Date]` is enough
for a simple date slicer. (A date table only matters once you want things like
"same period last year" comparisons, which this project doesn't need.)

## 2. Everything is drag-and-drop — here's how each number gets built

Every number below comes from dragging a field into a visual and choosing how
Power BI should summarize it (right-click the field in the well → **Summarize by**).
No formulas.

| What you want to show | Field to drag | Summarize by |
|---|---|---|
| Total Mailboxes | `Mailboxes[MailboxID]` | Count (Distinct) |
| Active / Inactive split | `Mailboxes[IsActive]` (as legend) + `MailboxID` (as value) | Count |
| Average Mailbox Size | `Mailboxes[MailboxSizeGB]` | Average |
| Total Storage Used | `Mailboxes[MailboxSizeGB]` | Sum |
| Total Quota | `Mailboxes[QuotaGB]` | Sum |
| Avg % Quota Used | `Mailboxes[PercentQuotaUsed]` | Average |
| Total Emails Sent / Received | `MailFlow[EmailsSent]` / `[EmailsReceived]` | Sum |
| Avg Daily Spam Rate | `MailFlow[SpamRatePct]` | Average |
| Total Failed Emails | `MailFlow[FailedEmails]` | Sum |
| Monthly License Cost | `Licenses[MonthlyCostUSD]` dragged next to `Mailboxes[MailboxID]` (Count) grouped by license | Sum works because of the relationship |

**Two things that would normally need a formula, but don't here** because they
were pre-computed upstream in Python/SQL instead:
- **`PercentQuotaUsed`** (per mailbox) — computed once in `analysis.py` /
  `mailboxes.csv`, so Power BI just averages or buckets an existing column.
- **`SpamRatePct`** (per mailbox-day) — same idea, computed in `mail_flow.csv`
  so Power BI never has to divide two sums itself.

This is a good general pattern: **push ratio/derived math upstream into
Python or SQL, and let Power BI just aggregate plain columns.** It keeps the
Power BI file simple and easy to hand off to someone who's never touched DAX.

## 3. Percent-of-total values (Active %, Quota %) — no formula needed

For anything that's "this slice as a % of the whole" (like % Active Mailboxes,
or license mix %), you don't need a calculation at all:

1. Build the visual normally (e.g. a bar of mailbox count by `IsActive`).
2. Right-click the value in the visual (or use the field's context menu) →
   **Show value as → Percent of grand total**.

Power BI computes the percentage for you, live, based on whatever filters are
currently applied.

## 4. The one "wasted spend" number — solved in Python, not Power BI

"Estimated wasted spend on inactive-mailbox licenses" needs `IsActive = False`
filtered *and* a cost multiplied by 12 for an annual figure. Rather than write
that in Power BI, it's already sitting in `data/kpi_summary.csv` (renamed
`Summary Metrics` in the workbook) as ready-made rows: `monthly_wasted_spend_usd`
and `annual_wasted_spend_usd`. Just drag those two rows straight into cards —
they're plain numbers, already calculated.

If you want it to react to slicers (e.g. only inactive mailboxes in one country),
build it as a simple visual instead: a table/card filtered to `IsActive = False`,
summing `Licenses[MonthlyCostUSD]` — filtering + summing, still no formula.

## 5. Recommended Pages & Visuals

### Page 1 — Overview
- **Cards** (top row): Total Mailboxes, % Active (via Percent of grand total),
  Average Mailbox Size, Total Storage Used, Avg Spam Rate, Monthly Wasted Spend
  (from Summary Metrics)
- **Donut chart**: Mailbox count by `IsActive`
- **Stacked bar**: Mailbox count by `LicenseName`, cost as tooltip
- **Line chart**: `EmailsSent` and `EmailsReceived` (Sum) over `MailFlow[Date]`

### Page 2 — Storage & Utilization
- **Bar chart**: `MailboxSizeGB` (Sum) by `Department`
- **Bar chart**: `MailboxSizeGB` (Sum) by `Country`
- **Bar chart**: mailbox count by a quota bucket — add one grouping column in
  Power Query (Transform Data → Add Column → Conditional Column) on
  `PercentQuotaUsed`: 0-25%, 25-50%, 50-75%, 75-85%, 85-100%. This is Power
  Query, not DAX — a simple if/then rule, no formulas.
- **Table**: Top 20 mailboxes sorted by `MailboxSizeGB` descending, with data
  bars (conditional formatting) on `PercentQuotaUsed`

### Page 3 — Mail Flow & Security
- **Line chart**: `SpamRatePct` (Average) and `FailedEmails` (Sum) over `Date`
- **Cards**: overall Avg Spam Rate, Total Failed Emails
- **Matrix**: `Department` (rows) × `EmailsSent`/`EmailsReceived` (Sum) — drill
  down to individual mailboxes

### Page 4 — License & Cost
- **Table**: inactive mailboxes — `MailboxID`, `Department`, `Country`,
  `LicenseName`, `DaysSinceLastLogon` — filtered to `IsActive = False`, sorted
  by days descending
- **Card**: Annual Wasted Spend (from Summary Metrics)
- **Bar chart**: `MonthlyCostUSD` (Sum) by `LicenseName`, split by `IsActive`

## 6. Slicers (apply across all pages)
- Department
- Country
- License SKU
- Date range
- Mailbox Type (User / Shared / Room / Equipment)

## 7. Formatting Notes
- Consistent color palette (matches `/charts` mockups: blue/green/orange/red)
- Format percentage fields (Field → right-click → Format → Percentage, 1 decimal)
- Conditional formatting (red >85% quota, amber 70–85%, green <70%) via the
  visual's **Format → Conditional formatting** pane — a built-in feature, no
  formula required
- Set report page size to 16:9

## 8. Refresh & Deployment
- Import mode + scheduled refresh in the Power BI Service if pulling from SQL
  Server (`01_schema_and_load.sql`)
- For production, swap the synthetic CSVs for a real extract (PowerShell
  `Get-MailboxStatistics`, `Get-Mailbox`, `Get-MessageTrace`, or the Microsoft
  Graph Reports API) landing into the same table shapes and pre-computed
  columns used here — the report requires no rework since nothing depends on
  custom formulas.
