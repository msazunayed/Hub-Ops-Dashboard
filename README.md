# Hub Operations Dashboard

An Excel dashboard that tracks daily parcel flow, delivery performance and backlog for a sort hub (sample data: *Northgate Sort Hub, NGH-01*). Paste in the day's exports and the whole workbook, including charts, refreshes itself.

> **Sample data is randomly simulated** and for illustration only.

## What it reports

| Metric | Definition |
|---|---|
| Parcels received | Parcels scanned in at the hub that day (`Parcels` sheet) |
| Out for delivery | Parcels loaded on vans that day (every `Attempts` row for that date) |
| Attempt rate | Attempted / Out for delivery (attempted = out for delivery minus `Not attempted`) |
| Delivery SLA % | Parcels delivered on or before their due date / parcels delivered that day |
| First-attempt delivery rate | Delivered on attempt 1 / parcels on attempt 1 |
| Closing backlog | All parcels received up to the day minus all delivered up to the day |

**Due date** = received date + SLA business days (Mon to Fri, `WORKDAY`). The hub operates Mon to Sat.

## Workbook layout

| Sheet | Purpose |
|---|---|
| `Summary` | The dashboard: KPI tiles, performance snapshot (report day / 7 days / 30 days), zone table, exception table, alerts, four charts. Service and Zone drop-downs (B3, F3) re-cut every number and chart. |
| `Daily Data` | Calculated rolling window of the last 30 operating days (Mon to Sat) ending on the report date. Do not type here. |
| `Parcels` | Input: one row per received parcel (columns A to E). SLA days and due date are formulas. |
| `Attempts` | Input: one row per delivery attempt event (columns A to E). Lookup columns F to I are formulas. |
| `Assumptions` | Hub name and code, targets, report date override, SLA days per service level, metric definitions. |
| `How To Use` | In-workbook refresh instructions and data rules. |

## Daily refresh (about 1 minute)

1. Export yesterday's inbound scans and delivery-attempt events from your hub system.
2. Paste new rows at the bottom of `Parcels` (columns A to E: ID, received date, service, zone, weight).
3. Paste new rows at the bottom of `Attempts` (columns A to E: ID, date, attempt no, outcome, failure reason).
4. Open `Summary`. The window rolls forward to the latest date automatically.

## Configuration (`Assumptions`)

| Setting | Cell | Current |
|---|---|---|
| Report date override (blank = latest data) | B5 | blank |
| Delivery SLA target | B7 | 95% |
| Attempt rate target | B8 | 97% |
| First-attempt delivery target | B9 | 88% |
| Backlog alert (days of average intake) | B10 | 1.5 |
| SLA business days: Express / Standard / Economy | B16:B18 | 1 / 3 / 5 |

Status cells on `Summary` turn green, amber or red against these targets.

## Colour conventions

- **Blue text on yellow fill**: input you can change
- **Blue text**: pasted raw data
- **Black text**: formula, leave alone
- **Green text**: link to another sheet

## Data rules (keep it accurate)

- Parcel IDs must be numeric and in **ascending order** (lookups use binary search).
- Every parcel in `Attempts` must already exist in `Parcels`, so load parcels before their attempts.
- `Outcome` must be exactly `Delivered`, `Failed` or `Not attempted`.
- `Service` and `Zone` must match the drop-down lists (Services: Express, Standard, Economy. Zones: North, South, East, West, Central).
- `Parcels` must hold **every parcel received and not yet delivered**, otherwise the backlog figure is wrong.

## Capacity

15,000 parcels and 17,000 attempt rows. To go beyond that, copy the formula rows down and extend the named ranges (`Formulas > Name Manager`: `P_*` for Parcels, `A_*` for Attempts).

## Named ranges

`P_ID`, `P_Date`, `P_Svc`, `P_Zone`, `P_Due` (Parcels) · `A_ID`, `A_Date`, `A_No`, `A_Out`, `A_Reason`, `A_Svc`, `A_Zone`, `A_OT` (Attempts) · `SLA_Target`, `Att_Target`, `FA_Target`, `ReportDate`, `SvcCrit`, `ZoneCrit` (Assumptions)


## Generate charts

Rebuilds the four dashboard charts as PNG files from the workbook data.

```
pip install -r requirements.txt
python charts.py
```

Charts are saved to the `charts/` folder. Options:

```
python charts.py --service Express --zone North
python charts.py --report-date 2026-10-10
python charts.py --out my_charts
python charts.py path/to/other_workbook.xlsx
```
