from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"

class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"

class TransactionType(str, enum.Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class EntryType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    account_type = Column(Enum(AccountType), default=AccountType.CHECKING, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    ledger_entries = relationship("LedgerEntry", back_populates="account", cascade="all, delete-orphan")
    source_transactions = relationship("Transaction", foreign_keys="Transaction.source_account_id", back_populates="source_account")
    dest_transactions = relationship("Transaction", foreign_keys="Transaction.destination_account_id", back_populates="destination_account")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(Enum(TransactionType), nullable=False)
    source_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Numeric(19, 4), nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    source_account = relationship("Account", foreign_keys=[source_account_id], back_populates="source_transactions")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="dest_transactions")
    ledger_entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False, index=True)
    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(Numeric(19, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    account = relationship("Account", back_populates="ledger_entries")
    transaction = relationship("Transaction", back_populates="ledger_entries")
    
    def __repr__(self):
        return f"<LedgerEntry {self.id} - {self.entry_type} {self.amount}>"
