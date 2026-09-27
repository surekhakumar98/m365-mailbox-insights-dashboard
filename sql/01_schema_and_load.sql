/* =========================================================================
   Exchange Online Mailbox Analytics Dashboard
   01_schema_and_load.sql
   Purpose: Create the SQL Server schema for mailbox & mail-flow analytics
            and load data from the accompanying CSV files.
   ========================================================================= */

IF DB_ID('ExchangeOnlineAnalytics') IS NULL
    CREATE DATABASE ExchangeOnlineAnalytics;
GO
USE ExchangeOnlineAnalytics;
GO

-- -------------------------------------------------------------------------
-- Dimension: Departments
-- -------------------------------------------------------------------------
IF OBJECT_ID('dbo.Departments', 'U') IS NOT NULL DROP TABLE dbo.Departments;
CREATE TABLE dbo.Departments (
    DepartmentID    INT PRIMARY KEY,
    Department      NVARCHAR(100) NOT NULL
);

-- -------------------------------------------------------------------------
-- Dimension: Licenses
-- -------------------------------------------------------------------------
IF OBJECT_ID('dbo.Licenses', 'U') IS NOT NULL DROP TABLE dbo.Licenses;
CREATE TABLE dbo.Licenses (
    LicenseSKU       NVARCHAR(50) PRIMARY KEY,
    LicenseName      NVARCHAR(100) NOT NULL,
    MonthlyCostUSD   DECIMAL(10,2) NOT NULL,
    MailboxQuotaGB   INT NOT NULL
);

-- -------------------------------------------------------------------------
-- Fact/Dimension: Mailboxes  (one row per mailbox - current-state snapshot)
-- -------------------------------------------------------------------------
IF OBJECT_ID('dbo.Mailboxes', 'U') IS NOT NULL DROP TABLE dbo.Mailboxes;
CREATE TABLE dbo.Mailboxes (
    MailboxID              NVARCHAR(20) PRIMARY KEY,
    DisplayName             NVARCHAR(200) NOT NULL,
    EmailAddress            NVARCHAR(200) NOT NULL,
    DepartmentID            INT NOT NULL REFERENCES dbo.Departments(DepartmentID),
    Country                 NVARCHAR(100) NOT NULL,
    LicenseSKU              NVARCHAR(50) NOT NULL REFERENCES dbo.Licenses(LicenseSKU),
    MailboxType             NVARCHAR(20) NOT NULL,   -- User, Shared, Room, Equipment
    MailboxSizeGB           DECIMAL(10,2) NOT NULL,
    QuotaGB                 INT NOT NULL,
    ItemCount                INT NOT NULL,
    CreatedDate             DATE NOT NULL,
    LastLogonDate           DATE NOT NULL,
    DaysSinceLastLogon      INT NOT NULL,
    IsActive                BIT NOT NULL,
    LitigationHoldEnabled   BIT NOT NULL,
    ArchiveEnabled          BIT NOT NULL,
    PercentQuotaUsed        DECIMAL(5,1) NOT NULL
);

-- -------------------------------------------------------------------------
-- Fact: Mail Flow (daily grain per mailbox)
-- -------------------------------------------------------------------------
IF OBJECT_ID('dbo.MailFlow', 'U') IS NOT NULL DROP TABLE dbo.MailFlow;
CREATE TABLE dbo.MailFlow (
    MailFlowID       BIGINT IDENTITY(1,1) PRIMARY KEY,
    MailboxID        NVARCHAR(20) NOT NULL REFERENCES dbo.Mailboxes(MailboxID),
    FlowDate         DATE NOT NULL,
    EmailsSent       INT NOT NULL,
    EmailsReceived   INT NOT NULL,
    SpamDetected     INT NOT NULL,
    FailedEmails     INT NOT NULL
);
CREATE INDEX IX_MailFlow_Date ON dbo.MailFlow(FlowDate);
CREATE INDEX IX_MailFlow_Mailbox ON dbo.MailFlow(MailboxID);

/* -------------------------------------------------------------------------
   Bulk load from CSV (adjust file paths to your SQL Server host, and make
   sure the SQL Server service account has read access to the folder, or
   use BULK INSERT from a network share / Azure Blob w/ external data source).
   ------------------------------------------------------------------------- */
BULK INSERT dbo.Departments
FROM 'C:\ExchangeOnlineData\departments.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n');

BULK INSERT dbo.Licenses
FROM 'C:\ExchangeOnlineData\licenses.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n');

BULK INSERT dbo.Mailboxes
FROM 'C:\ExchangeOnlineData\mailboxes.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n');

-- MailFlow has no MailFlowID column in the CSV (identity), so specify columns:
BULK INSERT dbo.MailFlow
FROM 'C:\ExchangeOnlineData\mail_flow.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n');
GO
