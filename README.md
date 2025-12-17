# Financial Ledger API

A robust REST API implementing double-entry bookkeeping for a mock banking application with ACID transactions, immutable ledger entries, and complete overdraft protection.

## Features

- ✅ **Double-Entry Bookkeeping** - Every transaction creates balanced debit/credit entries
- ✅ **ACID Transactions** - All DB operations are atomic with READ COMMITTED isolation
- ✅ **Immutable Ledger** - Append-only ledger entries for audit trail
- ✅ **Overdraft Protection** - No negative account balances allowed
- ✅ **On-Demand Balance Calculation** - Balances computed from ledger entries
- ✅ **Complete Transaction History** - Full audit trail per account
- ✅ **Proper Error Handling** - HTTP 400, 404, 422 status codes

## Tech Stack

- **Backend**: FastAPI 0.104.1
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0.23
- **Validation**: Pydantic 2.5.0
- **Server**: Uvicorn 0.24.0

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+

### Installation

```bash
# Clone repository
git clone https://github.com/manikantaoruganti/financial-ledger-api.git
cd financial-ledger-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
# Create PostgreSQL database and user:
# CREATE USER ledger_user WITH PASSWORD 'ledger_password';
# CREATE DATABASE financial_ledger OWNER ledger_user;

# Configure environment
cp .env .env.local
# Edit .env with your PostgreSQL credentials

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: **http://localhost:8000**

## API Endpoints

### Accounts

**Create Account**
```bash
POST /accounts
{
  "user_id": "user123",
  "account_type": "checking",
  "currency": "USD"
}
```

**Get Account Details**
```bash
GET /accounts/{accountId}
```

**Get Account Ledger**
```bash
GET /accounts/{accountId}/ledger
```

### Transfers

**Execute Transfer (Double-Entry)**
```bash
POST /transfers
{
  "source_account_id": "account-id-1",
  "destination_account_id": "account-id-2",
  "amount": "100.00",
  "description": "Payment"
}
```

### Deposits

**Execute Deposit**
```bash
POST /deposits
{
  "account_id": "account-id",
  "amount": "500.00",
  "description": "Initial deposit"
}
```

### Withdrawals

**Execute Withdrawal**
```bash
POST /withdrawals
{
  "account_id": "account-id",
  "amount": "100.00",
  "description": "Cash withdrawal"
}
```

## Data Models

### Account
- `id` (UUID, PK)
- `user_id` (String, indexed)
- `account_type` (Enum: checking, savings)
- `currency` (String)
- `status` (Enum: active, frozen, closed)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### Transaction
- `id` (UUID, PK)
- `type` (Enum: transfer, deposit, withdrawal)
- `source_account_id` (UUID, FK)
- `destination_account_id` (UUID, FK)
- `amount` (DECIMAL(19,4))
- `currency` (String)
- `status` (Enum: pending, completed, failed)
- `description` (String)
- `created_at` (DateTime)

### Ledger Entry (APPEND-ONLY)
- `id` (UUID, PK)
- `account_id` (UUID, FK, indexed)
- `transaction_id` (UUID, FK, indexed)
- `entry_type` (Enum: debit, credit)
- `amount` (DECIMAL(19,4))
- `created_at` (DateTime, indexed)

## Business Logic

### Double-Entry Bookkeeping
Every transaction creates exactly TWO balanced ledger entries:
- DEBIT on source account (money leaving)
- CREDIT on destination account (money arriving)
- Sum of amounts = 0 (balanced)

### ACID Transactions
All financial operations execute within a single database transaction:
- Ledger entry creation
- Transaction status update
- Balance verification
- **ALL OR NOTHING**: Either entire operation succeeds or entire operation rolls back

### Immutability
Ledger entries are APPEND-ONLY:
- Never modified after creation
- Never deleted
- Provides permanent, tamper-proof audit trail

### Overdraft Prevention
1. Calculate resulting balance from ledger entries
2. If result would be negative → REJECT with 422 status
3. Entire transaction is rolled back
4. Account balance never becomes negative

### Balance Calculation
```
Balance = SUM(CREDIT entries) - SUM(DEBIT entries)
```

Balance is ALWAYS computed dynamically from ledger, never cached.

## Error Handling

| Status Code | Scenario |
|---|---|
| 200 | Successful GET request |
| 201 | Successful POST (resource created) |
| 400 | Invalid input data |
| 404 | Resource not found |
| 422 | Business rule violation (insufficient funds) |
| 500 | Server error |

## Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## License

MIT

## Author

Manikanta Venkateswarlu Oruganti
