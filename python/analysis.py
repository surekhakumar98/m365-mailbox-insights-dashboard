"""
Exchange Online Mailbox Analytics - Python analysis layer.
Reads the generated CSVs, computes KPIs (matching the SQL queries),
and produces chart images for the Power BI-style dashboard mockup / report.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams.update({
    "figure.dpi": 130,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

DATA = "/home/claude/exo_project/data"
CHARTS = "/home/claude/exo_project/charts"

mailboxes = pd.read_csv(f"{DATA}/mailboxes.csv", parse_dates=["CreatedDate", "LastLogonDate"])
mail_flow = pd.read_csv(f"{DATA}/mail_flow.csv", parse_dates=["Date"])
departments = pd.read_csv(f"{DATA}/departments.csv")
licenses = pd.read_csv(f"{DATA}/licenses.csv")

mailboxes = mailboxes.merge(departments, on="DepartmentID", how="left")
mailboxes = mailboxes.merge(licenses, on="LicenseSKU", how="left")

# ---------------------------------------------------------------
# KPI CALCULATIONS
# ---------------------------------------------------------------
kpi = {}
kpi["total_mailboxes"] = len(mailboxes)
kpi["active_mailboxes"] = int(mailboxes["IsActive"].sum())
kpi["inactive_mailboxes"] = kpi["total_mailboxes"] - kpi["active_mailboxes"]
kpi["pct_active"] = round(kpi["active_mailboxes"] / kpi["total_mailboxes"] * 100, 1)
kpi["avg_mailbox_size_gb"] = round(mailboxes["MailboxSizeGB"].mean(), 2)
kpi["total_storage_gb"] = round(mailboxes["MailboxSizeGB"].sum(), 1)
kpi["total_quota_gb"] = int(mailboxes["QuotaGB"].sum())
kpi["pct_quota_used"] = round(kpi["total_storage_gb"] / kpi["total_quota_gb"] * 100, 1)

total_sent = mail_flow["EmailsSent"].sum()
total_received = mail_flow["EmailsReceived"].sum()
total_spam = mail_flow["SpamDetected"].sum()
total_failed = mail_flow["FailedEmails"].sum()
kpi["total_sent"] = int(total_sent)
kpi["total_received"] = int(total_received)
kpi["spam_rate_pct"] = round(total_spam / total_received * 100, 2)
kpi["total_failed"] = int(total_failed)

inactive_cost = mailboxes.loc[~mailboxes["IsActive"], "MonthlyCostUSD"].sum()
kpi["monthly_wasted_spend_usd"] = round(inactive_cost, 2)
kpi["annual_wasted_spend_usd"] = round(inactive_cost * 12, 2)

print("=== KEY KPI SUMMARY ===")
for k, v in kpi.items():
    print(f"{k}: {v}")

# ---------------------------------------------------------------
# CHART 1: Active vs Inactive Mailboxes (donut)
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5, 5))
vals = [kpi["active_mailboxes"], kpi["inactive_mailboxes"]]
colors = ["#2E7D32", "#C62828"]
wedges, _, autotexts = ax.pie(
    vals, labels=["Active", "Inactive"], autopct="%1.1f%%",
    colors=colors, startangle=90, wedgeprops={"width": 0.4}
)
ax.set_title(f"Active vs Inactive Mailboxes\n(Total: {kpi['total_mailboxes']:,})")
plt.tight_layout()
plt.savefig(f"{CHARTS}/01_active_vs_inactive.png")
plt.close()

# ---------------------------------------------------------------
# CHART 2: License Distribution
# ---------------------------------------------------------------
lic_dist = mailboxes.groupby("LicenseName").size().sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.barh(lic_dist.index, lic_dist.values, color="#1565C0")
ax.set_xlabel("Mailbox Count")
ax.set_title("License Distribution Across Mailboxes")
for bar in bars:
    w = bar.get_width()
    ax.text(w + 3, bar.get_y() + bar.get_height()/2, f"{int(w)}", va="center", fontsize=9)
plt.tight_layout()
plt.savefig(f"{CHARTS}/02_license_distribution.png")
plt.close()

# ---------------------------------------------------------------
# CHART 3: Department-wise Storage Usage
# ---------------------------------------------------------------
dept_storage = mailboxes.groupby("Department")["MailboxSizeGB"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(dept_storage.index, dept_storage.values, color="#EF6C00")
ax.set_ylabel("Total Storage (GB)")
ax.set_title("Storage Usage by Department")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.savefig(f"{CHARTS}/03_storage_by_department.png")
plt.close()

# ---------------------------------------------------------------
# CHART 4: Storage by Country
# ---------------------------------------------------------------
country_storage = mailboxes.groupby("Country")["MailboxSizeGB"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(country_storage.index, country_storage.values, color="#6A1B9A")
ax.set_ylabel("Total Storage (GB)")
ax.set_title("Storage Usage by Country")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.savefig(f"{CHARTS}/04_storage_by_country.png")
plt.close()

# ---------------------------------------------------------------
# CHART 5: Daily Email Traffic Trend (90 days)
# ---------------------------------------------------------------
daily = mail_flow.groupby("Date").agg(
    Sent=("EmailsSent", "sum"),
    Received=("EmailsReceived", "sum"),
    Spam=("SpamDetected", "sum"),
    Failed=("FailedEmails", "sum"),
).reset_index()

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(daily["Date"], daily["Sent"], label="Sent", color="#1565C0", linewidth=1.4)
ax.plot(daily["Date"], daily["Received"], label="Received", color="#2E7D32", linewidth=1.4)
ax.set_title("Daily Email Traffic (Last 90 Days)")
ax.set_ylabel("Email Count")
ax.legend()
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig(f"{CHARTS}/05_daily_traffic_trend.png")
plt.close()

# ---------------------------------------------------------------
# CHART 6: Spam & Failed Emails Trend
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(daily["Date"], daily["Spam"], label="Spam Detected", color="#C62828", linewidth=1.4)
ax.plot(daily["Date"], daily["Failed"], label="Failed Emails", color="#F9A825", linewidth=1.4)
ax.set_title("Spam Detection & Failed Emails (Last 90 Days)")
ax.set_ylabel("Email Count")
ax.legend()
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig(f"{CHARTS}/06_spam_failed_trend.png")
plt.close()

# ---------------------------------------------------------------
# CHART 7: Mailbox Size Distribution (histogram)
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.hist(mailboxes["MailboxSizeGB"], bins=30, color="#00838F", edgecolor="white")
ax.set_xlabel("Mailbox Size (GB)")
ax.set_ylabel("Number of Mailboxes")
ax.set_title("Mailbox Size Distribution")
plt.tight_layout()
plt.savefig(f"{CHARTS}/07_mailbox_size_distribution.png")
plt.close()

# ---------------------------------------------------------------
# CHART 8: Quota Utilization Buckets
# ---------------------------------------------------------------
bins = [0, 25, 50, 75, 85, 100]
labels = ["0-25%", "25-50%", "50-75%", "75-85%", "85-100%"]
mailboxes["QuotaBucket"] = pd.cut(mailboxes["PercentQuotaUsed"], bins=bins, labels=labels, include_lowest=True)
bucket_counts = mailboxes["QuotaBucket"].value_counts().reindex(labels)
fig, ax = plt.subplots(figsize=(7, 4.5))
colors_grad = ["#2E7D32", "#66BB6A", "#FDD835", "#FB8C00", "#C62828"]
bars = ax.bar(bucket_counts.index, bucket_counts.values, color=colors_grad)
ax.set_ylabel("Number of Mailboxes")
ax.set_title("Mailbox Quota Utilization Buckets")
plt.tight_layout()
plt.savefig(f"{CHARTS}/08_quota_utilization_buckets.png")
plt.close()

# ---------------------------------------------------------------
# Export a KPI summary CSV for easy reference / Power BI card visuals
# ---------------------------------------------------------------
kpi_df = pd.DataFrame(list(kpi.items()), columns=["KPI", "Value"])
kpi_df.to_csv(f"{DATA}/kpi_summary.csv", index=False)

print("\nAll charts saved to", CHARTS)
print("KPI summary saved to", f"{DATA}/kpi_summary.csv")
