import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from openpyxl import load_workbook

# Number of operating days (Mon to Sat) shown on the charts
WINDOW_DAYS = 30

# Default workbook: data/hub_ops_dashboard.xlsx next to this script
DEFAULT_WORKBOOK = str(Path(__file__).parent / "data" / "hub_ops_dashboard.xlsx")

# Chart colours
NAVY = "#1f3a5f"
TEAL = "#2a9d8f"
ORANGE = "#e76f51"
RED = "#c0392b"


#read the data
def read_data(workbook_path):
    # Read the raw input columns (A to E) from the Parcels and Attempts sheets
    parcels = pd.read_excel(workbook_path, sheet_name="Parcels", usecols="A:E")
    attempts = pd.read_excel(workbook_path, sheet_name="Attempts", usecols="A:E")

    # Use short, simple column names
    parcels.columns = ["id", "received", "service", "zone", "weight"]
    attempts.columns = ["id", "date", "attempt_no", "outcome", "reason"]

    # Drop empty rows and make sure dates have no time part
    parcels = parcels.dropna(subset=["id"]).copy()
    attempts = attempts.dropna(subset=["id"]).copy()
    parcels["received"] = pd.to_datetime(parcels["received"]).dt.normalize()
    attempts["date"] = pd.to_datetime(attempts["date"]).dt.normalize()

    # Read the targets and SLA days from the Assumptions sheet
    sheet = load_workbook(workbook_path, read_only=True)["Assumptions"]
    targets = {
        "sla": float(sheet["B7"].value),
        "attempt": float(sheet["B8"].value),
    }
    sla_days = {
        sheet["A16"].value: int(sheet["B16"].value),
        sheet["A17"].value: int(sheet["B17"].value),
        sheet["A18"].value: int(sheet["B18"].value),
    }
    return parcels, attempts, targets, sla_days


#prepare the data
def add_due_dates(parcels, sla_days):
    # Due date = received date + SLA working days (Mon to Fri)
    due_dates = []
    for _, parcel in parcels.iterrows():
        days_allowed = sla_days[parcel["service"]]
        due = np.busday_offset(parcel["received"].date(), days_allowed, roll="backward")
        due_dates.append(due)
    parcels["due"] = pd.to_datetime(due_dates)
    return parcels


def add_parcel_info_to_attempts(attempts, parcels):
    # Attach service, zone and due date to every attempt row
    info = parcels[["id", "service", "zone", "due"]]
    attempts = attempts.merge(info, on="id", how="left")

    # Every attempt must belong to a known parcel
    if attempts["service"].isna().any():
        raise ValueError("Some attempts have a parcel ID that is not in the Parcels sheet.")

    # An attempt is "on time" if the parcel was delivered on or before its due date
    delivered = attempts["outcome"] == "Delivered"
    on_time = attempts["date"] <= attempts["due"]
    attempts["on_time"] = delivered & on_time
    return attempts


def apply_filters(parcels, attempts, service, zone):
    # Keep only the chosen service and zone ("All" keeps everything)
    if service != "All":
        parcels = parcels[parcels["service"] == service]
        attempts = attempts[attempts["service"] == service]
    if zone != "All":
        parcels = parcels[parcels["zone"] == zone]
        attempts = attempts[attempts["zone"] == zone]
    return parcels, attempts


def get_window_days(report_date):
    # Walk backwards from the report date and collect 30 operating days (skip Sundays)
    days = []
    day = report_date
    while len(days) < WINDOW_DAYS:
        if day.weekday() != 6:  # 6 = Sunday
            days.append(day)
        day = day - pd.Timedelta(days=1)
    days.reverse()  # oldest day first
    return days


#build the daily table
def build_daily_table(parcels, attempts, days):
    rows = []
    for day in days:
        # Everything that happened on this day
        todays_parcels = parcels[parcels["received"] == day]
        todays_attempts = attempts[attempts["date"] == day]

        received = len(todays_parcels)
        out_for_delivery = len(todays_attempts)
        attempted = (todays_attempts["outcome"] != "Not attempted").sum()
        delivered = (todays_attempts["outcome"] == "Delivered").sum()
        on_time = todays_attempts["on_time"].sum()

        # Rates (use 0 when there is nothing to divide by)
        attempt_rate = attempted / out_for_delivery if out_for_delivery > 0 else 0
        sla_rate = on_time / delivered if delivered > 0 else 0

        # Backlog = all parcels received up to today - all parcels delivered up to today
        received_so_far = (parcels["received"] <= day).sum()
        delivered_so_far = ((attempts["date"] <= day) & (attempts["outcome"] == "Delivered")).sum()
        backlog = received_so_far - delivered_so_far

        rows.append(
            {
                "date": day,
                "received": received,
                "delivered": delivered,
                "attempt_rate": attempt_rate,
                "sla_rate": sla_rate,
                "backlog": backlog,
            }
        )
    return pd.DataFrame(rows)


#draw charts
def format_chart(ax, title, as_percent=False):
    # Shared look for all charts
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=NAVY)
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.tick_params(axis="y", labelsize=9)
    if as_percent:
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))


def set_date_labels(ax, table):
    # Show dates like "14 Sep" under each point
    labels = [date.strftime("%d %b") for date in table["date"]]
    ax.set_xticks(range(len(table)), labels)


def draw_received_vs_delivered(ax, table, targets):
    x = np.arange(len(table))
    width = 0.4
    ax.bar(x - width / 2, table["received"], width, label="Parcels Received", color=NAVY)
    ax.bar(x + width / 2, table["delivered"], width, label="Delivered", color=TEAL)
    set_date_labels(ax, table)
    format_chart(ax, "Parcels received vs delivered")
    ax.legend(frameon=False, fontsize=9)


def draw_backlog(ax, table, targets):
    x = np.arange(len(table))
    ax.bar(x, table["backlog"], 0.7, color=ORANGE)
    set_date_labels(ax, table)
    format_chart(ax, "Closing backlog (parcels)")


def draw_attempt_rate(ax, table, targets):
    x = np.arange(len(table))
    ax.plot(x, table["attempt_rate"], color=NAVY, marker="o", markersize=3, label="Attempt Rate")
    ax.plot(x, [targets["attempt"]] * len(table), color=RED, linestyle="--", label="Attempt Target")
    set_date_labels(ax, table)
    format_chart(ax, "Attempt rate vs target", as_percent=True)
    ax.legend(frameon=False, fontsize=9)


def draw_sla(ax, table, targets):
    x = np.arange(len(table))
    ax.plot(x, table["sla_rate"], color=TEAL, marker="o", markersize=3, label="Delivery SLA %")
    ax.plot(x, [targets["sla"]] * len(table), color=RED, linestyle="--", label="SLA Target")
    set_date_labels(ax, table)
    format_chart(ax, "Delivery SLA % vs target", as_percent=True)
    ax.legend(frameon=False, fontsize=9)


def save_charts(table, targets, out_folder, heading):
    out_folder.mkdir(parents=True, exist_ok=True)

    # File name and drawing function for each chart
    charts = [
        ("parcels_received_vs_delivered.png", draw_received_vs_delivered),
        ("closing_backlog.png", draw_backlog),
        ("attempt_rate_vs_target.png", draw_attempt_rate),
        ("delivery_sla_vs_target.png", draw_sla),
    ]

    # Save each chart as its own picture
    for file_name, draw in charts:
        fig, ax = plt.subplots(figsize=(8, 4))
        draw(ax, table, targets)
        fig.tight_layout()
        fig.savefig(out_folder / file_name, dpi=150)
        plt.close(fig)

    # Save all four charts together on one page
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    for ax, (file_name, draw) in zip(axes.flat, charts):
        draw(ax, table, targets)
    fig.suptitle(heading, x=0.01, ha="left", fontsize=15, fontweight="bold", color=NAVY)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_folder / "dashboard_charts.png", dpi=150)
    plt.close(fig)


#main
def main():
    parser = argparse.ArgumentParser(description="Generate the Hub Operations Dashboard charts from the workbook data.")
    parser.add_argument("workbook", nargs="?", default=DEFAULT_WORKBOOK, help="path to the workbook (default: data/hub_ops_dashboard.xlsx)")
    parser.add_argument("--out", default="charts", help="output folder (default: charts)")
    parser.add_argument("--service", default="All", choices=["All", "Express", "Standard", "Economy"])
    parser.add_argument("--zone", default="All", choices=["All", "North", "South", "East", "West", "Central"])
    parser.add_argument("--report-date", help="report date as YYYY-MM-DD (default: latest attempt date)")
    args = parser.parse_args()

    # 1. Read and prepare the data
    parcels, attempts, targets, sla_days = read_data(args.workbook)
    parcels = add_due_dates(parcels, sla_days)
    attempts = add_parcel_info_to_attempts(attempts, parcels)

    # 2. Pick the 30 days to show (the report date ignores the filters, like the workbook)
    if args.report_date:
        report_date = pd.Timestamp(args.report_date)
    else:
        report_date = attempts["date"].max()
    days = get_window_days(report_date)

    # Apply the service and zone filters after the report date is known
    parcels, attempts = apply_filters(parcels, attempts, args.service, args.zone)

    # 3. Build the daily numbers and draw the charts
    table = build_daily_table(parcels, attempts, days)
    heading = (
        f"Hub Operations: {days[0]:%d %b} to {days[-1]:%d %b %Y} "
        f"(Service: {args.service}, Zone: {args.zone})"
    )
    save_charts(table, targets, Path(args.out), heading)
    print(f"Saved 5 charts to {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
