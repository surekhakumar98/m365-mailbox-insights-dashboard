/* =========================================================================
   Exchange Online Mailbox Analytics Dashboard
   02_kpi_queries.sql
   Purpose: KPI and analytical queries powering the Power BI dashboard.
            Each query maps to one or more KPIs from the project spec.
   ========================================================================= */
USE ExchangeOnlineAnalytics;
GO

-- 1. Total Mailboxes -------------------------------------------------------
SELECT COUNT(*) AS TotalMailboxes
FROM dbo.Mailboxes;

-- 2. Active vs Inactive Mailboxes ------------------------------------------
SELECT
    IsActive,
    COUNT(*) AS MailboxCount,
    CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS DECIMAL(5,1)) AS PctOfTotal
FROM dbo.Mailboxes
GROUP BY IsActive;

-- 3. Average Mailbox Size (overall and by department) ---------------------
SELECT ROUND(AVG(MailboxSizeGB), 2) AS AvgMailboxSizeGB
FROM dbo.Mailboxes;

SELECT
    d.Department,
    ROUND(AVG(m.MailboxSizeGB), 2) AS AvgMailboxSizeGB,
    COUNT(*) AS MailboxCount
FROM dbo.Mailboxes m
JOIN dbo.Departments d ON d.DepartmentID = m.DepartmentID
GROUP BY d.Department
ORDER BY AvgMailboxSizeGB DESC;

-- 4. Total Storage Utilization ----------------------------------------------
SELECT
    ROUND(SUM(MailboxSizeGB), 2) AS TotalStorageUsedGB,
    ROUND(SUM(QuotaGB), 2) AS TotalQuotaGB,
    ROUND(SUM(MailboxSizeGB) * 100.0 / SUM(QuotaGB), 1) AS PctQuotaUsedOverall
FROM dbo.Mailboxes;

-- 5. License Distribution ---------------------------------------------------
SELECT
    l.LicenseName,
    COUNT(*) AS MailboxCount,
    CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS DECIMAL(5,1)) AS PctOfTotal,
    ROUND(COUNT(*) * l.MonthlyCostUSD, 2) AS MonthlyCostUSD
FROM dbo.Mailboxes m
JOIN dbo.Licenses l ON l.LicenseSKU = m.LicenseSKU
GROUP BY l.LicenseName, l.MonthlyCostUSD
ORDER BY MailboxCount DESC;

-- 5b. Wasted license spend on inactive mailboxes (cost-optimization insight)
SELECT
    l.LicenseName,
    COUNT(*) AS InactiveMailboxesWithLicense,
    ROUND(COUNT(*) * l.MonthlyCostUSD, 2) AS MonthlyWastedSpendUSD,
    ROUND(COUNT(*) * l.MonthlyCostUSD * 12, 2) AS AnnualWastedSpendUSD
FROM dbo.Mailboxes m
JOIN dbo.Licenses l ON l.LicenseSKU = m.LicenseSKU
WHERE m.IsActive = 0
GROUP BY l.LicenseName, l.MonthlyCostUSD
ORDER BY MonthlyWastedSpendUSD DESC;

-- 6. Daily Email Traffic (org-wide) -----------------------------------------
SELECT
    FlowDate,
    SUM(EmailsSent) AS TotalSent,
    SUM(EmailsReceived) AS TotalReceived,
    SUM(SpamDetected) AS TotalSpam,
    SUM(FailedEmails) AS TotalFailed
FROM dbo.MailFlow
GROUP BY FlowDate
ORDER BY FlowDate;

-- 7. Spam Detection Rate ------------------------------------------------------
SELECT
    ROUND(SUM(SpamDetected) * 100.0 / NULLIF(SUM(EmailsReceived), 0), 2) AS SpamRatePct
FROM dbo.MailFlow;

-- 8. Failed Email Count (overall & trend) --------------------------------------
SELECT SUM(FailedEmails) AS TotalFailedEmails
FROM dbo.MailFlow;

SELECT
    FlowDate,
    SUM(FailedEmails) AS FailedEmails
FROM dbo.MailFlow
GROUP BY FlowDate
ORDER BY FlowDate;

-- 9. Department-wise Storage Usage --------------------------------------------
SELECT
    d.Department,
    COUNT(*) AS MailboxCount,
    ROUND(SUM(m.MailboxSizeGB), 2) AS TotalStorageGB,
    ROUND(AVG(m.MailboxSizeGB), 2) AS AvgStorageGB,
    ROUND(SUM(m.MailboxSizeGB) * 100.0 / SUM(SUM(m.MailboxSizeGB)) OVER (), 1) AS PctOfTotalStorage
FROM dbo.Mailboxes m
JOIN dbo.Departments d ON d.DepartmentID = m.DepartmentID
GROUP BY d.Department
ORDER BY TotalStorageGB DESC;

-- 10. Storage by Country -------------------------------------------------------
SELECT
    Country,
    COUNT(*) AS MailboxCount,
    ROUND(SUM(MailboxSizeGB), 2) AS TotalStorageGB,
    ROUND(AVG(MailboxSizeGB), 2) AS AvgStorageGB
FROM dbo.Mailboxes
GROUP BY Country
ORDER BY TotalStorageGB DESC;

-- 11. Mailboxes nearing quota (>85% used) - proactive alert list --------------
SELECT
    MailboxID, DisplayName, EmailAddress, MailboxSizeGB, QuotaGB, PercentQuotaUsed
FROM dbo.Mailboxes
WHERE PercentQuotaUsed >= 85
ORDER BY PercentQuotaUsed DESC;

-- 12. Inactive mailboxes detail list (for license reclamation) ----------------
SELECT
    m.MailboxID, m.DisplayName, d.Department, m.Country,
    m.LicenseSKU, m.DaysSinceLastLogon, m.LastLogonDate
FROM dbo.Mailboxes m
JOIN dbo.Departments d ON d.DepartmentID = m.DepartmentID
WHERE m.IsActive = 0
ORDER BY m.DaysSinceLastLogon DESC;

-- 13. Top 20 largest mailboxes ---------------------------------------------------
SELECT TOP 20
    MailboxID, DisplayName, MailboxType, MailboxSizeGB, QuotaGB, PercentQuotaUsed
FROM dbo.Mailboxes
ORDER BY MailboxSizeGB DESC;

-- 14. Monthly mail traffic trend (rollup for trend visuals) -----------------
SELECT
    DATEFROMPARTS(YEAR(FlowDate), MONTH(FlowDate), 1) AS MonthStart,
    SUM(EmailsSent) AS TotalSent,
    SUM(EmailsReceived) AS TotalReceived,
    SUM(SpamDetected) AS TotalSpam,
    SUM(FailedEmails) AS TotalFailed
FROM dbo.MailFlow
GROUP BY DATEFROMPARTS(YEAR(FlowDate), MONTH(FlowDate), 1)
ORDER BY MonthStart;
