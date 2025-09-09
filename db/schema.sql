-- Schema for persistent accounts and transactions
CREATE DATABASE IF NOT EXISTS farisight CHARACTER
SET
    utf8mb4 COLLATE utf8mb4_unicode_ci;

USE farisight;

-- Corporate accounts (one row per account & currency)
CREATE TABLE
    IF NOT EXISTS accounts (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        ACCOUNT_NO VARCHAR(32) NOT NULL,
        CUSTOMER_ID VARCHAR(64) NOT NULL,
        ACCOUNT_CCY VARCHAR(3) NOT NULL,
        BALANCE DECIMAL(18, 2) NOT NULL DEFAULT 0.00,
        CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UPDATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_account (ACCOUNT_NO),
        KEY idx_customer (CUSTOMER_ID)
    ) ENGINE = InnoDB;

-- Transactions ledger
CREATE TABLE
    IF NOT EXISTS transactions (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        TRN_REF_NO VARCHAR(64) NOT NULL,
        ACCOUNT_NO VARCHAR(32) NOT NULL,
        CUSTOMER_ID VARCHAR(64) NOT NULL,
        TRN_DATE DATETIME NOT NULL,
        TRN_DESC VARCHAR(255) NULL,
        DRCR_INDICATOR ENUM ('DR', 'CR') NOT NULL,
        TRN_AMOUNT DECIMAL(18, 2) NOT NULL,
        TRN_CCY VARCHAR(3) NOT NULL,
        ACCOUNT_CCY VARCHAR(3) NOT NULL,
        OPENING_BALANCE DECIMAL(18, 2) NOT NULL,
        CLOSING_BALANCE DECIMAL(18, 2) NOT NULL,
        RUNNING_BALANCE DECIMAL(18, 2) NOT NULL,
        -- New: transaction type
        TRN_TYPE ENUM (
            'TRANSFER',
            'DEPOSIT',
            'LOAN_PAYMENT',
            'BILL_PAYMENT'
        ) NOT NULL,
        -- New: bank charges
        -- Bank charges (0.00 if failed)
        BANK_CHARGES DECIMAL(18, 2) NOT NULL DEFAULT 0.00,
        -- Transaction status
        STATUS ENUM ('SUCCESS', 'FAILED') NOT NULL DEFAULT 'SUCCESS',
        CREDIT_ACCOUNT VARCHAR(32) NULL,
        CREDIT_ACCOUNT_CCY VARCHAR(3) NULL,
        CREATED_AT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_ref (TRN_REF_NO),
        KEY idx_account (ACCOUNT_NO),
        CONSTRAINT fk_trn_account FOREIGN KEY (ACCOUNT_NO) REFERENCES accounts (ACCOUNT_NO) ON UPDATE CASCADE ON DELETE RESTRICT
    ) ENGINE = InnoDB;

CREATE TABLE
    IF NOT EXISTS kpis (
        id INT AUTO_INCREMENT PRIMARY KEY,
        computed_at DATETIME NOT NULL,
        -- Existing aggregates
        total_transactions INT NOT NULL,
        total_amount_usd DECIMAL(18, 2) NOT NULL,
        total_amount_rm DECIMAL(18, 2) NOT NULL,
        dr_count INT NOT NULL,
        cr_count INT NOT NULL,
        txn_per_customer JSON NOT NULL,
        -- New: per transaction type counts
        transfer_count INT NOT NULL,
        deposit_count INT NOT NULL,
        loan_payment_count INT NOT NULL,
        bill_payment_count INT NOT NULL,
        -- New: bank charges aggregate
        total_bank_charges DECIMAL(18, 2) NOT NULL,
        -- New: success metrics
        success_count INT NOT NULL,
        -- New: failure metrics
        failed_txn_count INT NOT NULL,
        failure_rate DECIMAL(5, 2) NOT NULL -- percentage (0.00 to 100.00)
    ) ENGINE = InnoDB;

-- Optional: seed known customers with two accounts each (USD & RM)
USE farisight;

INSERT IGNORE INTO accounts (ACCOUNT_NO, CUSTOMER_ID, ACCOUNT_CCY, BALANCE)
VALUES
    ('700000000001', '223345', 'USD', 25000.00),
    ('700000000002', '223345', 'RM', 80000.00),
    ('700000000003', '445566', 'USD', 18000.00),
    ('700000000004', '445566', 'RM', 650000.00),
    ('700000000005', '786052', 'USD', 12000.00),
    ('700000000006', '786052', 'RM', 500000.00),
    ('700000000007', '78605200', 'USD', 90000.00),
    ('700000000008', '78605200', 'RM', 38000.00),
    ('700000000009', 'BFLUK012025', 'USD', 30000.00),
    ('700000000010', 'BFLUK012025', 'RM', 100000.00),
    ('700000000011', 'SIUAE2025', 'USD', 22000.00),
    ('700000000012', 'SIUAE2025', 'RM', 720000.00);