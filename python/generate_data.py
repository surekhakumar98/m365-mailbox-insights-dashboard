"""
Generate realistic synthetic Exchange Online mailbox & mail-flow data
for the Exchange Online Mailbox Analytics Dashboard project.

Outputs (CSV, later loaded into Excel + SQL):
  - mailboxes.csv       (1 row per mailbox - master dimension + facts)
  - mail_flow.csv       (daily email traffic per mailbox, 90 days)
  - licenses.csv        (license SKU lookup + cost)
  - departments.csv     (department/country lookup)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

rng = np.random.default_rng(42)

# ---------------------------------------------------------------
# 1. Lookup dimensions
# ---------------------------------------------------------------
departments = pd.DataFrame({
    "DepartmentID": range(1, 11),
    "Department": ["Sales", "Marketing", "Finance", "HR", "IT",
                   "Operations", "Legal", "Customer Support",
                   "Engineering", "Executive"],
})

countries = ["United States", "United Kingdom", "Germany", "India",
             "Canada", "Australia", "France", "Singapore"]

licenses = pd.DataFrame({
    "LicenseSKU": ["E1", "E3", "E5", "Business Basic", "Business Standard", "Exchange Online Plan 1"],
    "LicenseName": ["Microsoft 365 E1", "Microsoft 365 E3", "Microsoft 365 E5",
                     "Microsoft 365 Business Basic", "Microsoft 365 Business Standard",
                     "Exchange Online Plan 1"],
    "MonthlyCostUSD": [10.00, 23.00, 38.00, 6.00, 12.50, 4.00],
    "MailboxQuotaGB": [50, 100, 100, 50, 50, 50],
})

# ---------------------------------------------------------------
# 2. Mailboxes master table (N mailboxes)
# ---------------------------------------------------------------
N_MAILBOXES = 750

first_names = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
               "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica",
               "Thomas","Sarah","Charles","Karen","Daniel","Nancy","Matthew","Lisa",
               "Anthony","Betty","Mark","Margaret","Donald","Sandra","Priya","Wei",
               "Fatima","Hiroshi","Chen","Anjali","Liam","Olivia","Noah","Emma"]
last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
              "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
              "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
              "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Kumar",
              "Patel","Khan","Yamamoto","Zhang","Singh","Murphy","Kelly","Bell","Cook"]

mailbox_ids = [f"MBX{str(i).zfill(5)}" for i in range(1, N_MAILBOXES + 1)]
fn = rng.choice(first_names, N_MAILBOXES)
ln = rng.choice(last_names, N_MAILBOXES)
display_names = [f"{f} {l}" for f, l in zip(fn, ln)]
emails = [f"{f.lower()}.{l.lower()}{i}@contoso.com" for f, l, i in zip(fn, ln, range(N_MAILBOXES))]

dept_ids = rng.choice(departments["DepartmentID"], N_MAILBOXES,
                       p=[0.18, 0.10, 0.09, 0.06, 0.14, 0.12, 0.05, 0.13, 0.11, 0.02])
country_choice = rng.choice(countries, N_MAILBOXES,
                             p=[0.30, 0.15, 0.12, 0.18, 0.08, 0.06, 0.06, 0.05])

license_choice = rng.choice(licenses["LicenseSKU"], N_MAILBOXES,
                             p=[0.20, 0.35, 0.15, 0.10, 0.12, 0.08])
license_map = licenses.set_index("LicenseSKU")["MailboxQuotaGB"].to_dict()
quota_gb = [license_map[s] for s in license_choice]

# Mailbox size: right-skewed distribution (most mailboxes small, some huge)
size_gb = np.round(rng.gamma(shape=2.2, scale=6.5, size=N_MAILBOXES), 2)
size_gb = np.minimum(size_gb, np.array(quota_gb) * 0.98)  # can't exceed quota realistically
size_gb = np.maximum(size_gb, 0.05)

item_count = (size_gb * rng.uniform(180, 320, N_MAILBOXES)).astype(int)

# Mailbox type
mailbox_type = rng.choice(["User", "Shared", "Room", "Equipment"], N_MAILBOXES,
                           p=[0.88, 0.08, 0.03, 0.01])

# Created date (0.5 to 6 years ago)
today = datetime(2026, 7, 24)
days_ago_created = rng.integers(180, 2190, N_MAILBOXES)
created_date = [today - timedelta(days=int(d)) for d in days_ago_created]

# Last logon: most mailboxes recent, ~12% inactive (>90 days) to create realistic "inactive" insight
days_since_logon = rng.choice(
    [rng.integers(0, 30), rng.integers(30, 90), rng.integers(90, 365)],
    size=N_MAILBOXES, p=None
) if False else None
# simpler: mixture
inactive_flag_roll = rng.random(N_MAILBOXES)
days_since_logon = np.where(
    inactive_flag_roll < 0.75, rng.integers(0, 30, N_MAILBOXES),
    np.where(inactive_flag_roll < 0.90, rng.integers(30, 90, N_MAILBOXES),
             rng.integers(90, 400, N_MAILBOXES))
)
last_logon_date = [today - timedelta(days=int(d)) for d in days_since_logon]
is_active = days_since_logon <= 90

litigation_hold = rng.random(N_MAILBOXES) < 0.08
archive_enabled = rng.random(N_MAILBOXES) < 0.35

mailboxes = pd.DataFrame({
    "MailboxID": mailbox_ids,
    "DisplayName": display_names,
    "EmailAddress": emails,
    "DepartmentID": dept_ids,
    "Country": country_choice,
    "LicenseSKU": license_choice,
    "MailboxType": mailbox_type,
    "MailboxSizeGB": size_gb,
    "QuotaGB": quota_gb,
    "ItemCount": item_count,
    "CreatedDate": created_date,
    "LastLogonDate": last_logon_date,
    "DaysSinceLastLogon": days_since_logon,
    "IsActive": is_active,
    "LitigationHoldEnabled": litigation_hold,
    "ArchiveEnabled": archive_enabled,
})
mailboxes["PercentQuotaUsed"] = np.round(mailboxes["MailboxSizeGB"] / mailboxes["QuotaGB"] * 100, 1)

# ---------------------------------------------------------------
# 3. Daily mail flow (90 days) - aggregated per mailbox per day for user mailboxes
#    To keep file size sane, generate per-mailbox daily traffic only for a
#    representative sample driven by mailbox activity, then also produce an
#    org-wide daily summary table.
# ---------------------------------------------------------------
NUM_DAYS = 90
date_range = [today - timedelta(days=d) for d in range(NUM_DAYS)][::-1]

flow_rows = []
active_mailboxes = mailboxes[mailboxes["MailboxType"] == "User"].sample(
    n=min(300, (mailboxes["MailboxType"] == "User").sum()), random_state=1
)

for _, mb in active_mailboxes.iterrows():
    base_sent = rng.uniform(5, 40)
    base_received = rng.uniform(15, 120)
    activity_scale = 1.0 if mb["IsActive"] else rng.uniform(0.0, 0.15)
    for d in date_range:
        weekday = d.weekday()
        weekend_factor = 0.15 if weekday >= 5 else 1.0
        sent = max(0, int(rng.poisson(base_sent * weekend_factor * activity_scale)))
        received = max(0, int(rng.poisson(base_received * weekend_factor * activity_scale)))
        spam = max(0, int(rng.poisson(received * 0.06)))
        failed = max(0, int(rng.poisson((sent + received) * 0.01)))
        flow_rows.append((mb["MailboxID"], d.date().isoformat(), sent, received, spam, failed))

mail_flow = pd.DataFrame(flow_rows, columns=[
    "MailboxID", "Date", "EmailsSent", "EmailsReceived", "SpamDetected", "FailedEmails"
])

# ---------------------------------------------------------------
# Save all CSVs
# ---------------------------------------------------------------
departments.to_csv("/home/claude/exo_project/data/departments.csv", index=False)
licenses.to_csv("/home/claude/exo_project/data/licenses.csv", index=False)
mailboxes.to_csv("/home/claude/exo_project/data/mailboxes.csv", index=False)
mail_flow.to_csv("/home/claude/exo_project/data/mail_flow.csv", index=False)

print("Mailboxes:", mailboxes.shape)
print("Mail flow rows:", mail_flow.shape)
print("Departments:", departments.shape)
print("Licenses:", licenses.shape)
print(mailboxes.head(3).to_string())
