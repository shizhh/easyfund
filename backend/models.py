"""Tortoise ORM models for EasyFund."""

from tortoise import fields, models


class Account(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    name = fields.CharField(max_length=200)
    category = fields.CharField(max_length=20)
    institution = fields.CharField(max_length=200, default="")
    balances = fields.JSONField(default=list)
    notes = fields.TextField(default="")
    sub_accounts = fields.JSONField(default=list)
    annual_rate = fields.FloatField(default=0)
    exclude_from_total = fields.BooleanField(default=False)
    ins_premium = fields.FloatField(default=0)
    ins_total_periods = fields.IntField(default=0)
    ins_paid_periods = fields.IntField(default=0)
    ins_start_year = fields.IntField(default=0)
    ins_rate = fields.FloatField(default=0)
    ins_annual_payout = fields.FloatField(default=0)
    ins_payout_schedule = fields.JSONField(default=list)
    ins_start_date = fields.CharField(max_length=20, default="")
    ins_birth_date = fields.CharField(max_length=20, default="")
    ins_end_date = fields.CharField(max_length=20, default="")
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "accounts"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "institution": self.institution, "balances": self.balances or [],
            "notes": self.notes, "sub_accounts": self.sub_accounts or [],
            "annual_rate": self.annual_rate, "exclude_from_total": self.exclude_from_total,
            "ins_premium": self.ins_premium, "ins_total_periods": self.ins_total_periods,
            "ins_paid_periods": self.ins_paid_periods, "ins_start_year": self.ins_start_year,
            "ins_rate": self.ins_rate, "ins_annual_payout": self.ins_annual_payout,
            "ins_payout_schedule": self.ins_payout_schedule or [],
            "ins_start_date": self.ins_start_date, "ins_birth_date": self.ins_birth_date,
            "ins_end_date": self.ins_end_date, "sort_order": self.sort_order,
        }


class Holding(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    account = fields.ForeignKeyField("models.Account", related_name="holdings", on_delete=fields.CASCADE)
    ticker = fields.CharField(max_length=20, default="")
    name = fields.CharField(max_length=200, default="")
    shares = fields.IntField(default=0)
    avg_cost_price = fields.FloatField(default=0)
    current_price = fields.FloatField(default=0)
    currency = fields.CharField(max_length=5, default="USD")
    vested_shares = fields.IntField(default=0)
    unvested_shares = fields.IntField(default=0)
    vesting_schedule = fields.JSONField(default=list)

    class Meta:
        table = "holdings"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "account_id": self.account_id,
            "ticker": self.ticker, "name": self.name, "shares": self.shares,
            "avg_cost_price": self.avg_cost_price, "current_price": self.current_price,
            "currency": self.currency, "vested_shares": self.vested_shares,
            "unvested_shares": self.unvested_shares,
            "vesting_schedule": self.vesting_schedule or [],
        }


class Transaction(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    account = fields.ForeignKeyField("models.Account", related_name="transactions", on_delete=fields.CASCADE)
    type = fields.CharField(max_length=20)
    date = fields.CharField(max_length=20)
    amount = fields.FloatField()
    currency = fields.CharField(max_length=5, default="CNY")
    quantity = fields.IntField(null=True)
    price = fields.FloatField(null=True)
    pnl = fields.FloatField(null=True)
    notes = fields.TextField(default="")

    class Meta:
        table = "transactions"

    def to_dict(self) -> dict:
        d = {"id": self.id, "account_id": self.account_id, "type": self.type,
             "date": self.date, "amount": self.amount, "currency": self.currency, "notes": self.notes}
        if self.quantity is not None: d["quantity"] = self.quantity
        if self.price is not None: d["price"] = self.price
        if self.pnl is not None: d["pnl"] = self.pnl
        return d


class Deposit(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    account = fields.ForeignKeyField("models.Account", related_name="deposits", on_delete=fields.CASCADE)
    amount = fields.FloatField()
    rate = fields.FloatField()
    start_date = fields.CharField(max_length=20, default="")
    maturity_date = fields.CharField(max_length=20, default="")
    interest = fields.FloatField(default=0)

    class Meta:
        table = "deposits"

    def to_dict(self) -> dict:
        return {"id": self.id, "account_id": self.account_id, "amount": self.amount,
                "rate": self.rate, "start_date": self.start_date,
                "maturity_date": self.maturity_date, "interest": self.interest}


class FundFlow(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    account = fields.ForeignKeyField("models.Account", related_name="fund_flows", on_delete=fields.CASCADE)
    type = fields.CharField(max_length=20)
    currency = fields.CharField(max_length=5)
    amount = fields.FloatField()
    rate_at_time = fields.FloatField()
    date = fields.CharField(max_length=20)
    notes = fields.TextField(default="")

    class Meta:
        table = "fund_flows"

    def to_dict(self) -> dict:
        return {"id": self.id, "account_id": self.account_id, "type": self.type,
                "currency": self.currency, "amount": self.amount,
                "rate_at_time": self.rate_at_time, "date": self.date, "notes": self.notes}


class ExchangeRate(models.Model):
    currency = fields.CharField(max_length=5, pk=True)
    rate_to_cny = fields.FloatField()
    date = fields.CharField(max_length=20, default="")
    source = fields.CharField(max_length=20, default="")

    class Meta:
        table = "exchange_rates"

    def to_dict(self) -> dict:
        return {"currency": self.currency, "rate_to_cny": self.rate_to_cny,
                "date": self.date, "source": self.source}


class WatchlistItem(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    ticker = fields.CharField(max_length=20)
    name = fields.CharField(max_length=200, default="")

    class Meta:
        table = "watchlist"

    def to_dict(self) -> dict:
        return {"id": self.id, "ticker": self.ticker, "name": self.name}


class PriceSnapshot(models.Model):
    id = fields.IntField(pk=True)
    ticker = fields.CharField(max_length=20)
    price = fields.FloatField()
    currency = fields.CharField(max_length=5, default="USD")
    date = fields.CharField(max_length=20)

    class Meta:
        table = "price_snapshots"

    def to_dict(self) -> dict:
        return {"ticker": self.ticker, "price": self.price,
                "currency": self.currency, "date": self.date}


class Conversation(models.Model):
    id = fields.CharField(max_length=100, pk=True)
    title = fields.CharField(max_length=200, default="新对话")
    messages = fields.JSONField(default=list)
    created_at = fields.CharField(max_length=40, default="")
    updated_at = fields.CharField(max_length=40, default="")

    class Meta:
        table = "conversations"

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title,
                "messages": self.messages or [], "created_at": self.created_at,
                "updated_at": self.updated_at}
