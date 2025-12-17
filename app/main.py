from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.database import engine, get_db, SessionLocal
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Financial Ledger API",
    description="Double-entry bookkeeping REST API with ACID transactions",
    version="1.0.0"
)

class AccountCreate(BaseModel):
    user_id: str
    account_type: str = "checking"
    currency: str = "USD"

class AccountResponse(BaseModel):
    id: str
    user_id: str
    account_type: str
    currency: str
    status: str
    balance: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class LedgerEntryResponse(BaseModel):
    id: str
    account_id: str
    transaction_id: str
    entry_type: str
    amount: str
    created_at: datetime
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: str
    type: str
    source_account_id: Optional[str]
    destination_account_id: Optional[str]
    amount: str
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class TransferCreate(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None

class DepositCreate(BaseModel):
    account_id: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None

class WithdrawalCreate(BaseModel):
    account_id: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None

def get_account_balance(db: Session, account_id: str) -> Decimal:
    debit_sum = db.query(func.coalesce(func.sum(models.LedgerEntry.amount), 0)).filter(
        models.LedgerEntry.account_id == account_id,
        models.LedgerEntry.entry_type == models.EntryType.DEBIT
    ).scalar()
    
    credit_sum = db.query(func.coalesce(func.sum(models.LedgerEntry.amount), 0)).filter(
        models.LedgerEntry.account_id == account_id,
        models.LedgerEntry.entry_type == models.EntryType.CREDIT
    ).scalar()
    
    return Decimal(str(credit_sum)) - Decimal(str(debit_sum))

@app.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    try:
        new_account = models.Account(
            user_id=account.user_id,
            account_type=account.account_type,
            currency=account.currency,
            status=models.AccountStatus.ACTIVE
        )
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
        
        balance = get_account_balance(db, new_account.id)
        return AccountResponse(
            id=new_account.id,
            user_id=new_account.user_id,
            account_type=new_account.account_type,
            currency=new_account.currency,
            status=new_account.status,
            balance=str(balance),
            created_at=new_account.created_at,
            updated_at=new_account.updated_at
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating account: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    balance = get_account_balance(db, account.id)
    return AccountResponse(
        id=account.id,
        user_id=account.user_id,
        account_type=account.account_type,
        currency=account.currency,
        status=account.status,
        balance=str(balance),
        created_at=account.created_at,
        updated_at=account.updated_at
    )

@app.get("/accounts/{account_id}/ledger")
def get_account_ledger(account_id: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    entries = db.query(models.LedgerEntry).filter(
        models.LedgerEntry.account_id == account_id
    ).order_by(models.LedgerEntry.created_at).all()
    
    return {
        "account_id": account_id,
        "total_entries": len(entries),
        "entries": [{
            "id": e.id,
            "account_id": e.account_id,
            "transaction_id": e.transaction_id,
            "entry_type": e.entry_type,
            "amount": str(e.amount),
            "created_at": e.created_at
        } for e in entries]
    }

@app.post("/transfers", response_model=TransactionResponse, status_code=201)
def execute_transfer(transfer: TransferCreate, db: Session = Depends(get_db)):
    try:
        source = db.query(models.Account).filter(models.Account.id == transfer.source_account_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source account not found")
        
        destination = db.query(models.Account).filter(models.Account.id == transfer.destination_account_id).first()
        if not destination:
            raise HTTPException(status_code=404, detail="Destination account not found")
        
        source_balance = get_account_balance(db, source.id)
        if source_balance < transfer.amount:
            db.rollback()
            raise HTTPException(status_code=422, detail="Insufficient funds")
        
        tx = models.Transaction(
            type=models.TransactionType.TRANSFER,
            source_account_id=transfer.source_account_id,
            destination_account_id=transfer.destination_account_id,
            amount=transfer.amount,
            currency="USD",
            status=models.TransactionStatus.PENDING,
            description=transfer.description
        )
        db.add(tx)
        db.flush()
        
        debit_entry = models.LedgerEntry(
            account_id=transfer.source_account_id,
            transaction_id=tx.id,
            entry_type=models.EntryType.DEBIT,
            amount=transfer.amount
        )
        db.add(debit_entry)
        
        credit_entry = models.LedgerEntry(
            account_id=transfer.destination_account_id,
            transaction_id=tx.id,
            entry_type=models.EntryType.CREDIT,
            amount=transfer.amount
        )
        db.add(credit_entry)
        
        tx.status = models.TransactionStatus.COMPLETED
        
        db.commit()
        db.refresh(tx)
        
        return TransactionResponse(
            id=tx.id,
            type=tx.type,
            source_account_id=tx.source_account_id,
            destination_account_id=tx.destination_account_id,
            amount=str(tx.amount),
            currency=tx.currency,
            status=tx.status,
            description=tx.description,
            created_at=tx.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Transfer error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/deposits", response_model=TransactionResponse, status_code=201)
def execute_deposit(deposit: DepositCreate, db: Session = Depends(get_db)):
    try:
        account = db.query(models.Account).filter(models.Account.id == deposit.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        tx = models.Transaction(
            type=models.TransactionType.DEPOSIT,
            source_account_id=None,
            destination_account_id=deposit.account_id,
            amount=deposit.amount,
            currency="USD",
            status=models.TransactionStatus.PENDING,
            description=deposit.description or "Deposit"
        )
        db.add(tx)
        db.flush()
        
        credit_entry = models.LedgerEntry(
            account_id=deposit.account_id,
            transaction_id=tx.id,
            entry_type=models.EntryType.CREDIT,
            amount=deposit.amount
        )
        db.add(credit_entry)
        
        tx.status = models.TransactionStatus.COMPLETED
        
        db.commit()
        db.refresh(tx)
        
        return TransactionResponse(
            id=tx.id,
            type=tx.type,
            source_account_id=tx.source_account_id,
            destination_account_id=tx.destination_account_id,
            amount=str(tx.amount),
            currency=tx.currency,
            status=tx.status,
            description=tx.description,
            created_at=tx.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Deposit error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/withdrawals", response_model=TransactionResponse, status_code=201)
def execute_withdrawal(withdrawal: WithdrawalCreate, db: Session = Depends(get_db)):
    try:
        account = db.query(models.Account).filter(models.Account.id == withdrawal.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_balance = get_account_balance(db, account.id)
        if account_balance < withdrawal.amount:
            raise HTTPException(status_code=422, detail="Insufficient funds")
        
        tx = models.Transaction(
            type=models.TransactionType.WITHDRAWAL,
            source_account_id=withdrawal.account_id,
            destination_account_id=None,
            amount=withdrawal.amount,
            currency="USD",
            status=models.TransactionStatus.PENDING,
            description=withdrawal.description or "Withdrawal"
        )
        db.add(tx)
        db.flush()
        
        debit_entry = models.LedgerEntry(
            account_id=withdrawal.account_id,
            transaction_id=tx.id,
            entry_type=models.EntryType.DEBIT,
            amount=withdrawal.amount
        )
        db.add(debit_entry)
        
        tx.status = models.TransactionStatus.COMPLETED
        
        db.commit()
        db.refresh(tx)
        
        return TransactionResponse(
            id=tx.id,
            type=tx.type,
            source_account_id=tx.source_account_id,
            destination_account_id=tx.destination_account_id,
            amount=str(tx.amount),
            currency=tx.currency,
            status=tx.status,
            description=tx.description,
            created_at=tx.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Withdrawal error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
