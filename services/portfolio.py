"""
Vostok Web Terminal – Portfolio, Dividends & Account Service
=============================================================
Connects to T-Bank Invest API for account info, positions, dividend calendar,
and sandbox operations.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from t_tech.invest import (
    Client,
    CandleInterval,
    InstrumentIdType,
    InstrumentStatus,
    MoneyValue,
)
from t_tech.invest.utils import now

# ---------------------------------------------------------------------------
# Target Account
# ---------------------------------------------------------------------------
TARGET_ACCOUNT_ID = "2274582154"


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

@st.cache_data(ttl=55, show_spinner=False)
def fetch_portfolio(_token: str) -> dict:
    """
    Fetch portfolio positions, cash, P&L, and recent operations.

    Returns a dict:
        total_value, total_pnl, day_pnl, cash, positions (list), operations (list)
    """
    with Client(_token) as client:
        # Resolve account
        account_id = _resolve_account(client)
        if not account_id:
            return _empty_portfolio("No accounts found")

        # Fetch portfolio
        port = client.operations.get_portfolio(account_id=account_id)

        # Fetch last prices + prev-day closes for each position
        last_prices: Dict[str, float] = {}
        prev_prices: Dict[str, float] = {}
        ticker_names: Dict[str, str] = {}

        for pos in port.positions:
            try:
                inst = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                    id=pos.instrument_uid,
                )
                if not inst or not inst.instrument:
                    continue
                figi = inst.instrument.figi
                ticker = inst.instrument.ticker
                ticker_names[pos.instrument_uid] = ticker

                # Current price
                pr = client.market_data.get_last_prices(
                    figi=[figi],
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE,
                )
                if pr.last_prices:
                    lp = pr.last_prices[0].price
                    last_prices[pos.instrument_uid] = float(lp.units) + float(lp.nano) / 1e9

                # Prev-day close
                try:
                    cdls = list(
                        client.get_all_candles(
                            instrument_id=figi,
                            from_=datetime.now(timezone.utc) - timedelta(days=3),
                            to=datetime.now(timezone.utc),
                            interval=CandleInterval.CANDLE_INTERVAL_DAY,
                        )
                    )
                    if len(cdls) >= 2:
                        prev_prices[pos.instrument_uid] = (
                            float(cdls[-2].close.units) + float(cdls[-2].close.nano) / 1e9
                        )
                except Exception:
                    pass
            except Exception:
                continue

        # Compute positions
        positions_out: List[dict] = []
        total_value = 0.0
        total_pnl = 0.0
        total_day_pnl = 0.0
        cash_balance = 0.0

        for pos in port.positions:
            if pos.instrument_type == "currency":
                cash_balance += float(pos.quantity.units)
                continue

            qty = float(pos.quantity.units)
            avg = float(pos.average_position_price.units) + float(pos.average_position_price.nano) / 1e9
            last = last_prices.get(pos.instrument_uid, avg)
            prev = prev_prices.get(pos.instrument_uid, last)

            value = qty * last
            pnl = (last - avg) * qty
            pnl_pct = (pnl / (avg * qty)) * 100 if avg * qty > 0 else 0
            day_pnl = (last - prev) * qty
            day_pnl_pct = ((last - prev) / prev) * 100 if prev > 0 else 0

            total_value += value
            total_pnl += pnl
            total_day_pnl += day_pnl

            positions_out.append({
                "ticker": ticker_names.get(pos.instrument_uid, pos.instrument_uid[:8]),
                "qty": qty,
                "avg_price": avg,
                "last_price": last,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "day_pnl": day_pnl,
                "day_pnl_pct": day_pnl_pct,
            })

        # Recent operations (last 30 days)
        ops_out: List[dict] = []
        try:
            ops = client.operations.get_operations(
                account_id=account_id,
                from_=datetime.now(timezone.utc) - timedelta(days=30),
                to=datetime.now(timezone.utc),
            )
            for op in ops.operations[:20]:
                op_amt = 0.0
                if hasattr(op, "payment"):
                    op_amt = float(op.payment.units) + float(op.payment.nano) / 1e9
                elif hasattr(op, "amount"):
                    op_amt = float(op.amount.units) + float(op.amount.nano) / 1e9
                ops_out.append({
                    "date": op.date.strftime("%Y-%m-%d %H:%M") if op.date else "",
                    "ticker": ticker_names.get(op.instrument_uid, op.instrument_uid[:8]),
                    "type": op.operation_type.name.replace("_", " ").title(),
                    "qty": float(op.quantity.units) if hasattr(op.quantity, "units") else 0,
                    "price": (
                        float(op.price.units) + float(op.price.nano) / 1e9
                        if hasattr(op.price, "units") else 0
                    ),
                    "amount": op_amt,
                })
        except Exception:
            pass

        return {
            "total_value": total_value,
            "total_pnl": total_pnl,
            "day_pnl": total_day_pnl,
            "cash": cash_balance,
            "positions": positions_out,
            "operations": ops_out,
            "account_id": account_id,
            "ticker_names": ticker_names,
        }


# ---------------------------------------------------------------------------
# Dividend Calendar
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_dividends(
    _token: str,
    _tickers_tuple: tuple,
    portfolio_positions: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    Fetch upcoming dividends (next 6 months) for all tickers.
    Cross-references with portfolio to compute expected payout.
    """
    tickers = dict(_tickers_tuple)
    portfolio = portfolio_positions or {}
    events: List[dict] = []
    current = datetime.now(tz=timezone.utc)
    horizon = current + timedelta(days=180)

    with Client(_token) as client:
        for i, (ticker, uid) in enumerate(tickers.items()):
            if i > 0:
                time.sleep(0.2)  # Rate-limit safety
            try:
                resp = client.instruments.get_dividends(
                    instrument_id=uid,
                    from_=current,
                    to=horizon,
                )
                for div in resp.dividends:
                    if not hasattr(div, "record_date") or not div.record_date:
                        continue
                    rd = div.record_date
                    if rd.tzinfo is None:
                        rd = rd.replace(tzinfo=timezone.utc)
                    days_left = (rd - current).days
                    if days_left < 0 or days_left > 180:
                        continue

                    dps = 0.0
                    if hasattr(div, "dividend_net") and div.dividend_net:
                        dps = float(div.dividend_net.units) + float(div.dividend_net.nano) / 1e9

                    shares_owned = portfolio.get(ticker, {}).get("qty", 0)
                    payout = shares_owned * dps

                    events.append({
                        "ticker": ticker,
                        "date": rd,
                        "div_per_share": dps,
                        "shares_owned": shares_owned,
                        "expected_payout": payout,
                        "days_left": days_left,
                    })
            except Exception as exc:
                err = str(exc)
                if "RESOURCE_EXHAUSTED" in err:
                    time.sleep(3)
                continue

    events.sort(key=lambda e: e["date"])
    return events


# ---------------------------------------------------------------------------
# Sandbox Operations
# ---------------------------------------------------------------------------

def sandbox_init(_token: str) -> str:
    """Create a sandbox account, return its ID."""
    with Client(_token) as client:
        resp = client.sandbox.open_sandbox_account(name="VostokWeb")
        return resp.account_id


def sandbox_deposit(_token: str, account_id: str, amount: int = 100_000):
    """Deposit virtual RUB into sandbox account."""
    with Client(_token) as client:
        client.sandbox.sandbox_pay_in(
            account_id=account_id,
            amount=MoneyValue(units=amount, nano=0, currency="rub"),
        )


def sandbox_buy(
    _token: str, account_id: str, uid: str, lots: int
) -> str:
    """Place a sandbox market BUY order, return order ID."""
    from t_tech.invest import OrderDirection, OrderType

    with Client(_token) as client:
        resp = client.sandbox.post_sandbox_order(
            account_id=account_id,
            instrument_id=uid,
            quantity=lots,
            direction=OrderDirection.ORDER_DIRECTION_BUY,
            order_type=OrderType.ORDER_TYPE_MARKET,
        )
        return resp.order_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_account(client: Client) -> Optional[str]:
    """Find the target account, falling back to first available."""
    try:
        resp = client.users.get_accounts()
        # Try the specific target account first
        for acc in resp.accounts:
            if acc.id == TARGET_ACCOUNT_ID:
                return acc.id
        # Fallback: first brokerage account
        for acc in resp.accounts:
            atype = getattr(acc, "account_type", None)
            if atype and "BROKER" in str(atype.name).upper():
                return acc.id
        # Fallback: first account
        if resp.accounts:
            return resp.accounts[0].id
    except Exception:
        pass
    return None


def _empty_portfolio(error: str = "") -> dict:
    return {
        "total_value": 0.0,
        "total_pnl": 0.0,
        "day_pnl": 0.0,
        "cash": 0.0,
        "positions": [],
        "operations": [],
        "account_id": "",
        "error": error,
    }
