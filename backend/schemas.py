"""Pydantic schemas for API request/response."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

# Currency is a 3-letter ISO 4217 code (e.g. "CNY", "USD", "EUR").
# Supported currencies are determined dynamically by the exchange-rate table.
_CURRENCY_RE = r'^[A-Z]{3}$'


class AccountCategory(str, Enum):
    cash = "cash"
    investment = "investment"
    insurance = "insurance"
    future_cash = "future_cash"


class Balance(BaseModel):
    currency: str = Field(pattern=_CURRENCY_RE)
    amount: float
    annual_rate: float = 0


class SubAccount(BaseModel):
    label: str
    amount: float


class InsPayoutEntry(BaseModel):
    label: str              # 如：大学、深造、有成关爱金、满期金
    annual_amount: float    # 每年领取金额
    years: int              # 领取年数


class Account(BaseModel):
    id: str
    name: str
    category: AccountCategory
    institution: str = ""
    balances: list[Balance] = []
    notes: str = ""
    sub_accounts: list[SubAccount] = []
    annual_rate: float = 0
    exclude_from_total: bool = False    # 不计入资产总额
    # Insurance fields
    ins_premium: float = 0          # 年交保费
    ins_total_periods: int = 0      # 总期数
    ins_paid_periods: int = 0       # 已交期数
    ins_start_year: int = 0         # 第几年开始领
    ins_rate: float = 0             # 年利率
    ins_annual_payout: float = 0    # 每年领取金额（按利率或统一金额）
    ins_payout_schedule: list[InsPayoutEntry] = []  # 分段领取计划
    ins_start_date: str = ""       # 保险开始日期（首次交费日）
    ins_birth_date: str = ""       # 保险人出生日期
    ins_end_date: str = ""         # 保单终止日期（如保至70周岁对应的日期）
    sort_order: int = 0


class AccountCreate(BaseModel):
    id: str
    name: str
    category: AccountCategory
    institution: str = ""
    balances: list[Balance] = []
    notes: str = ""
    sub_accounts: list[SubAccount] = []
    annual_rate: float = 0
    exclude_from_total: bool = False
    ins_premium: float = 0
    ins_total_periods: int = 0
    ins_paid_periods: int = 0
    ins_start_year: int = 0
    ins_rate: float = 0
    ins_annual_payout: float = 0
    ins_payout_schedule: list[InsPayoutEntry] = []
    ins_start_date: str = ""
    ins_birth_date: str = ""
    ins_end_date: str = ""
    sort_order: int = 0


class AccountUpdate(BaseModel):
    name: str | None = None
    category: AccountCategory | None = None
    institution: str | None = None
    balances: list[Balance] | None = None
    notes: str | None = None
    sub_accounts: list[SubAccount] | None = None
    annual_rate: float | None = None
    exclude_from_total: bool | None = None
    ins_premium: float | None = None
    ins_total_periods: int | None = None
    ins_paid_periods: int | None = None
    ins_start_year: int | None = None
    ins_rate: float | None = None
    ins_annual_payout: float | None = None
    ins_payout_schedule: list[InsPayoutEntry] | None = None
    ins_start_date: str | None = None
    ins_birth_date: str | None = None
    ins_end_date: str | None = None
    sort_order: int | None = None


class VestingEntry(BaseModel):
    date: str
    shares: int
    status: str = "pending"


class Holding(BaseModel):
    id: str
    account_id: str
    ticker: str
    name: str = ""
    shares: int = 0
    avg_cost_price: float = 0
    current_price: float = 0
    currency: str = Field(default="USD", pattern=_CURRENCY_RE)
    vested_shares: int = 0
    unvested_shares: int = 0
    vesting_schedule: list[VestingEntry] = []


class HoldingCreate(BaseModel):
    id: str
    account_id: str
    ticker: str
    name: str = ""
    shares: int = 0
    avg_cost_price: float = 0
    current_price: float = 0
    currency: str = Field(default="USD", pattern=_CURRENCY_RE)
    vested_shares: int = 0
    unvested_shares: int = 0
    vesting_schedule: list[VestingEntry] = []


class HoldingUpdate(BaseModel):
    account_id: str | None = None
    ticker: str | None = None
    name: str | None = None
    shares: int | None = None
    avg_cost_price: float | None = None
    current_price: float | None = None
    currency: str | None = Field(default=None, pattern=_CURRENCY_RE)
    vested_shares: int | None = None
    unvested_shares: int | None = None
    vesting_schedule: list[VestingEntry] | None = None


class TransactionType(str, Enum):
    deposit = "deposit"
    withdraw = "withdraw"
    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    interest = "interest"
    pnl = "pnl"


class Transaction(BaseModel):
    id: str
    account_id: str
    type: TransactionType
    date: str
    amount: float
    currency: str = Field(default="CNY", pattern=_CURRENCY_RE)
    quantity: int | None = None
    price: float | None = None
    pnl: float | None = None
    notes: str = ""


class TransactionCreate(BaseModel):
    id: str
    account_id: str
    type: TransactionType
    date: str
    amount: float
    currency: str = Field(default="CNY", pattern=_CURRENCY_RE)
    quantity: int | None = None
    price: float | None = None
    pnl: float | None = None
    notes: str = ""


class TransactionUpdate(BaseModel):
    account_id: str | None = None
    type: TransactionType | None = None
    date: str | None = None
    amount: float | None = None
    currency: str | None = Field(default=None, pattern=_CURRENCY_RE)
    quantity: int | None = None
    price: float | None = None
    pnl: float | None = None
    notes: str | None = None


class Deposit(BaseModel):
    id: str
    account_id: str
    amount: float
    rate: float
    start_date: str
    maturity_date: str
    interest: float = 0


class DepositCreate(BaseModel):
    id: str
    account_id: str
    amount: float
    rate: float
    start_date: str
    maturity_date: str
    interest: float = 0


class DepositUpdate(BaseModel):
    account_id: str | None = None
    amount: float | None = None
    rate: float | None = None
    start_date: str | None = None
    maturity_date: str | None = None
    interest: float | None = None


class ExchangeRate(BaseModel):
    currency: str = Field(pattern=_CURRENCY_RE)
    rate_to_cny: float
    date: str = Field(default_factory=lambda: date.today().isoformat())


class FundFlowType(str, Enum):
    deposit = "deposit"
    withdraw = "withdraw"


class FundFlow(BaseModel):
    id: str
    account_id: str
    type: FundFlowType
    currency: str = Field(pattern=_CURRENCY_RE)
    amount: float
    rate_at_time: float
    date: str
    notes: str = ""


class FundFlowCreate(BaseModel):
    id: str
    account_id: str
    type: FundFlowType
    currency: str = Field(pattern=_CURRENCY_RE)
    amount: float
    rate_at_time: float
    date: str
    notes: str = ""


class FundFlowUpdate(BaseModel):
    account_id: str | None = None
    type: FundFlowType | None = None
    currency: str | None = Field(default=None, pattern=_CURRENCY_RE)
    amount: float | None = None
    rate_at_time: float | None = None
    date: str | None = None
    notes: str | None = None


class WatchlistItem(BaseModel):
    id: str
    ticker: str
    name: str = ""


class WatchlistItemCreate(BaseModel):
    id: str
    ticker: str
    name: str = ""


class WatchlistItemUpdate(BaseModel):
    ticker: str | None = None
    name: str | None = None


# ── AI Assistant ─────────────────────────────────────────────

class AiConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"


class AiConfigUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[dict] | None = None  # assistant tool_calls
    tool_call_id: str | None = None  # tool response


class Conversation(BaseModel):
    id: str
    title: str = "新对话"
    messages: list[ChatMessage] = []
    created_at: str = ""
    updated_at: str = ""


class ConversationCreate(BaseModel):
    title: str = "新对话"


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


# ── Import Mapping (AI-driven) ───────────────────────────────

class ColumnMapping(BaseModel):
    """Maps a single Excel column to a target field."""
    column_index: int
    column_header: str
    target_field: str          # EasyFund field name or "skip"
    transform: str | None = None   # "regex:pattern", "int", "float", "date:format", "currency_code"
    transform_group: int | None = None


class CellReference(BaseModel):
    """A specific cell with a standalone value (e.g., exchange rate)."""
    cell_ref: str              # e.g., "H2"
    purpose: str
    target_type: str           # "exchange_rate"
    target_field: str
    currency: str | None = None


class CategoryRule(BaseModel):
    """Maps raw cell values to EasyFund categories."""
    raw_value: str
    category: str              # cash, investment, insurance, future_cash


class SectionDetection(BaseModel):
    """For sheets with multiple logical sections."""
    section_marker_column: int
    section_type: str          # "account", "transaction", "deposit"
    rules: str


class SheetMapping(BaseModel):
    """Mapping configuration for a single sheet."""
    sheet_name: str
    target_types: list[str]    # e.g., ["account", "holding", "exchange_rate"]
    header_row: int = 0
    data_start_row: int = 1
    column_mappings: list[ColumnMapping] = []
    cell_references: list[CellReference] = []
    category_rules: list[CategoryRule] = []
    section_detection: SectionDetection | None = None
    skip_conditions: list[str] = []  # e.g., ["category_raw == '资产总值'"]


class ImportMappingSchema(BaseModel):
    """Complete mapping schema for an entire workbook."""
    sheets: list[SheetMapping]
    confidence: float = 0.0
    notes: list[str] = []
    detected_language: str = "zh"


class ImportConfirmRequest(BaseModel):
    session_id: str
    mapping: ImportMappingSchema
