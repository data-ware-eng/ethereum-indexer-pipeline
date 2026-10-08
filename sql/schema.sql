-- Create Customers Dimension Table
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    us_state VARCHAR(2) NOT NULL,
    risk_level VARCHAR(20) DEFAULT 'LOW'
);

-- Create Accounts Dimension Table
CREATE TABLE IF NOT EXISTS dim_accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    customer_id INT NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    balance_usd NUMERIC(15, 2) DEFAULT 0.00,
    opened_date DATE NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);

-- Create Transactions Fact Table
CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_id VARCHAR(100) PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    customer_id INT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    transaction_timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_accounts(account_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
);