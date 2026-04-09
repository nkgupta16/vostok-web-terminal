"""
Vostok Web Terminal – T-Bank API & Market Data Service
======================================================
Handles all T-Bank Invest API interactions: fetching candles, lot sizes,
share instrument lists, and computing per-ticker analytics.
"""

import json
import os
from datetime import timedelta
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from t_tech.invest import Client, CandleInterval, InstrumentStatus
from t_tech.invest.utils import now

from services.indicators import (
    prepare_candle_data,
    calculate_indicators,
    check_buy_signal,
    calculate_confidence_score,
    calculate_squeeze_score,
    get_signal_label,
    BB_BUFFER,
    ATR_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Full MOEX Universe (from MOEX_Dip_Scanner gui_config.json)
# ---------------------------------------------------------------------------
DEFAULT_TICKERS: Dict[str, str] = {
    "SBER": "e6123145-9665-43e0-8413-cd61b8aa9b13",
    "GAZP": "962e2a95-02a9-4171-abd7-aa198dbe643a",
    "LKOH": "02cfdf61-6298-4c0f-a9ca-9cabc82afaf3",
    "GMKN": "509edd0c-129c-4ee2-934d-7f6246126da1",
    "NVTK": "0da66728-6c30-44c4-9264-df8fac2467ee",
    "ROSN": "fd417230-19cf-4e7b-9623-f7c9ca18ec6b",
    "VTBR": "8e2b0325-0292-4654-8a18-4f63ed3b0e09",
    "SNGSP": "a797f14a-8513-4b84-b15e-a3b98dc4cc00",
    "AFLT": "1c69e020-f3b1-455c-affa-45f8b8049234",
    "SFIN": "55371b1f-8f7c-4c12-9d93-386fae5ec12a",
    "HNFG": "2fa1d15e-236c-4e4e-8155-f740badfece6",
    "BELU": "974077c4-d893-4058-9314-8f1b64a444b8",
    "WUSH": "b993e814-9986-4434-ae88-b086066714a0",
    "BSPB": "1e19953d-01c6-4ecd-a5f4-53ae3ed44029",
    "VSEH": "538a1b13-df23-4449-8302-e8adbc25daf4",
    "BAZA": "6eeb0c40-1a7f-4b57-aeee-a3dbb3846b80",
    "POSI": "de08affe-4fbd-454e-9fd1-46a81b23f870",
    "FESH": "11bc2246-6fde-4478-93f1-4ab90ceb4a51",
    "EUTR": "02b2ea14-3c4b-47e8-9548-45a8dbcc8f8a",
    "X5": "0964acd0-e2cb-4810-a177-ef4ad8856ff0",
    "MVID": "cf1c6158-a303-43ac-89eb-9b1db8f96043",
    "OZON": "75e003c2-ca14-4980-8d7b-e82ec6b6ffe1",
    "ETLN": "b9dff600-4ca6-4fa9-ba91-df2126548ccc",
    "MBNK": "459a1a0a-0253-465a-bd4e-afaaf5e670b0",
    "MAGN": "7132b1c9-ee26-4464-b5b5-1046264b61d9",
    "MOEX": "5e1c2634-afc4-4e50-ad6d-f78fc14a539a",
    "MSNG": "98fc1318-6990-4147-b0d1-b10999326461",
    "NLMK": "161eb0d0-aaac-4451-b374-f5d0eeb1b508",
    "GLRX": "51be1fe4-9fe1-4626-9400-6cd1fb6286c5",
    "PLZL": "10620843-28ce-44e8-80c2-f26ceb1bd3e1",
    "PMSB": "4d8209f9-3b75-437d-ad5f-2906d56f27e9",
    "PMSBP": "80a39145-b2f7-46f5-9ef0-1478baafb0a6",
    "RUAL": "f866872b-8f68-4b6e-930f-749fe9aa79c0",
    "RENI": "a57d3a52-63d5-417b-b66d-c6114587f0ea",
    "MRKU": "1b64e38a-49ad-4f4d-a4d3-b34184899352",
    "RAGR": "9b9a584e-448f-40da-9ba8-353b44ad697a",
    "RNFT": "c7485564-ed92-45fd-a724-1214aa202904",
    "SBERP": "c190ff1f-1447-4227-b543-316332699ca5",
    "SNGS": "1ffe1bff-d7b7-4b04-b482-34dc9cc0a4ba",
    "TGKA": "d74daf58-22c3-4e44-8ada-471e404fb795",
    "TATN": "88468f6c-c67a-4fb4-a006-53eed803883c",
    "TATNP": "efdb54d3-2f92-44da-b7a3-8849e96039f6",
    "PHOR": "9978b56f-782a-4a80-a4b1-a48cbecfd194",
    "UGLD": "48bd9002-43be-4528-abf4-dc8135ad4550",
    "YDEX": "7de75794-a27f-4d81-a39b-492345813822",
    "LEAS": "ab29b599-4cb4-4b57-9c17-02b140708bf7",
    "LENT": "5f1e6b0a-4413-489c-b336-40b43730eaf5",
    "IRAO": "2dfbc1fd-b92a-436e-b011-928c79e805f2",
    "TRNFP": "653d47e9-dbd4-407a-a1c3-47f897df4694",
    "FLOT": "21423d2d-9009-4d37-9325-883b368d13ae",
    "AFKS": "53b67587-96eb-4b41-8e0c-d2e3c0bdd234",
    "HEAD": "3fe80143-1313-42eb-9884-5d68b39e265e",
    "SGZH": "7bedd86b-478d-4742-a28c-29d27f8dbc7d",
    "SMLT": "4d813ab1-8bc9-4670-89ea-12bfbab6017d",
    "ASTR": "aae786d8-e8f4-4428-91bb-cffa39ad01e4",
    "TGKB": "ba9b6eb4-614c-4be8-bdba-dd86cdfece64",
    "TGKBP": "45609688-b63e-42dd-88a0-9d30c423c5e5",
    "NSVZ": "88c3b1dd-cf86-48b6-b479-464ce1149472",
    "RBCM": "45fb6af4-9076-4268-b038-ab7f37d15ab2",
    "BANE": "0a55e045-e9a6-42d2-ac55-29674634af2f",
    "BANEP": "a5776620-1e2f-47ea-bbd6-06d8e4a236d8",
    "GTRK": "9e69afb6-4561-4fc2-b63b-b181e3f9ecdc",
    "FEES": "88e130e8-5b68-4b05-b9ae-baf32f5a3f21",
    "TTLK": "76721c1c-52a9-4b45-987e-d075f651f1b1",
    "DATA": "0b9afb23-280f-4fda-a7ad-816994959c6b",
    "FIXR": "8be64b53-a46b-451c-8152-1c871f122d5b",
    "MRKZ": "05dbfebd-6bc4-4645-8f21-dcf05476999d",
    "PIKK": "03d5e771-fc10-438e-8892-85a40733612d",
    "DOMRF": "aac2b935-3d94-4030-83a1-f7acdd9b05a5",
    "CHMF": "fa6aae10-b8d5-48c8-bbfd-d320d925d096",
    "VKCO": "b71bd174-c72c-41b0-a66f-5f9073e0d1f5",
    "MTLR": "eb4ba863-e85f-4f80-8c29-f2627938ee58",
    "MTLRP": "c1a3c440-f51c-4a75-a400-42a2a74f5f2b",
    "GCHE": "231e5e27-9956-47e7-ad50-6e802e4a92ed",
    "AQUA": "b83ab195-dcd2-4d44-b9bf-27fa294f19a0",
    "SELG": "0d28c01b-f841-4e89-9c92-0ee23d12883a",
}

CANDLES_COUNT = 50  # Daily candles to fetch for dashboard
SQUEEZE_CANDLES = 150  # More data needed for reliable squeeze percentiles

# ---------------------------------------------------------------------------
# Ticker Persistence (JSON file for user customizations)
# ---------------------------------------------------------------------------
_TICKER_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ticker_config.json")


def save_tickers(tickers: Dict[str, str]):
    """Persist the ticker map to a local JSON file."""
    with open(_TICKER_CONFIG_PATH, "w") as f:
        json.dump(tickers, f, indent=2)


def load_tickers() -> Dict[str, str]:
    """Load tickers from local config, falling back to defaults."""
    if os.path.exists(_TICKER_CONFIG_PATH):
        try:
            with open(_TICKER_CONFIG_PATH) as f:
                data = json.load(f)
            if data:
                return data
        except Exception:
            pass
    return dict(DEFAULT_TICKERS)


def get_tickers() -> Dict[str, str]:
    """Return the ticker → UID map (from session state or persisted config)."""
    if "tickers" not in st.session_state:
        st.session_state["tickers"] = load_tickers()
    return st.session_state["tickers"]


def get_selected_tickers() -> list:
    """Return the list of currently selected (enabled) ticker symbols."""
    all_tickers = get_tickers()
    if "selected_tickers" not in st.session_state:
        st.session_state["selected_tickers"] = list(all_tickers.keys())
    return st.session_state["selected_tickers"]


def fetch_all_moex_shares(token: str) -> Dict[str, dict]:
    """Fetch all MOEX shares from T-Bank API for the ticker manager."""
    results: Dict[str, dict] = {}
    try:
        with Client(token) as client:
            resp = client.instruments.shares(
                instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
            )
            for share in resp.instruments:
                if share.exchange == "MOEX" or share.exchange == "MOEX_EVENING_WEEKEND":
                    results[share.ticker] = {
                        "uid": share.uid,
                        "name": share.name,
                        "lot": getattr(share, "lot", 1) or 1,
                        "figi": share.figi,
                    }
    except Exception:
        pass
    return results


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_lot_sizes(client: Client, tickers: Dict[str, str]) -> Dict[str, int]:
    """Fetch MOEX lot sizes for given tickers."""
    lot_sizes: Dict[str, int] = {}
    try:
        resp = client.instruments.shares(
            instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
        )
        for share in resp.instruments:
            if share.ticker in tickers:
                lot_sizes[share.ticker] = getattr(share, "lot", 1) or 1
    except Exception:
        for t in tickers:
            lot_sizes[t] = 1
    return lot_sizes


def fetch_candles(
    client: Client, uid: str, days: int = CANDLES_COUNT
) -> Optional[list]:
    """Fetch last *days* daily candles for an instrument UID."""
    try:
        candles = list(
            client.get_all_candles(
                instrument_id=uid,
                from_=now() - timedelta(days=days + 10),
                to=now(),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            )
        )
        if len(candles) > days:
            candles = candles[-days:]
        return candles
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Full Market Scan
# ---------------------------------------------------------------------------

@st.cache_data(ttl=55, show_spinner=False)
def scan_market(_token: str, _tickers_tuple: tuple) -> Dict[str, dict]:
    """
    Full market scan: fetch candles, compute indicators, and score each ticker.

    Returns a dict keyed by ticker with analytics payload.
    """
    tickers = dict(_tickers_tuple)
    results: Dict[str, dict] = {}

    with Client(_token) as client:
        lot_sizes = fetch_lot_sizes(client, tickers)

        for ticker, uid in tickers.items():
            try:
                candles = fetch_candles(client, uid, CANDLES_COUNT)
                if not candles or len(candles) < 2:
                    continue

                df = prepare_candle_data(candles)
                df = calculate_indicators(df)

                latest = df.iloc[-1]
                previous = df.iloc[-2]

                price = float(latest["close"])
                rsi = float(latest["RSI"])
                bb_lower = float(latest["BB_LOWER"])
                bb_upper = float(latest["BB_UPPER"])
                macd_hist = float(latest["MACD_HISTOGRAM"])
                prev_hist = float(previous["MACD_HISTOGRAM"])
                vol = float(latest["volume"])

                # Volume ratio vs 10d average
                if len(df) >= 10:
                    avg_vol = float(df["volume"].iloc[-11:-1].mean())
                    vol_ratio = (vol / avg_vol) * 100 if avg_vol > 0 else 100.0
                else:
                    vol_ratio = 100.0

                # Derived metrics
                price_to_bb = ((price - bb_lower) / bb_lower) * 100 if bb_lower else 0
                macd_change = (
                    ((macd_hist - prev_hist) / abs(prev_hist)) * 100
                    if prev_hist != 0
                    else 0.0
                )

                signal, _ = check_buy_signal(df, bb_buffer=BB_BUFFER)

                confidence = calculate_confidence_score(
                    rsi=rsi,
                    price=price,
                    bb_lower=bb_lower,
                    bb_upper=bb_upper,
                    volume_ratio=vol_ratio,
                    macd_hist=macd_hist,
                    macd_change=macd_change,
                )

                label = get_signal_label(confidence, signal)

                results[ticker] = {
                    "price": price,
                    "rsi": rsi,
                    "bb_lower": bb_lower,
                    "bb_upper": bb_upper,
                    "bb_middle": float(latest["BB_MIDDLE"]),
                    "macd_hist": macd_hist,
                    "macd_change": macd_change,
                    "volume_ratio": vol_ratio,
                    "price_to_bb": price_to_bb,
                    "signal": signal,
                    "confidence": confidence,
                    "label": label,
                    "lot_size": lot_sizes.get(ticker, 1),
                    "df": df,  # full DataFrame for charting
                }
            except Exception:
                continue

    return results


# ---------------------------------------------------------------------------
# Squeeze Scan — uses more history for accurate percentiles
# ---------------------------------------------------------------------------

@st.cache_data(ttl=55, show_spinner=False)
def scan_squeeze(_token: str, _tickers_tuple: tuple) -> Dict[str, dict]:
    """Scan all tickers for volatility squeeze metrics."""
    tickers = dict(_tickers_tuple)
    results: Dict[str, dict] = {}

    with Client(_token) as client:
        to_time = now()
        from_time = to_time - timedelta(days=SQUEEZE_CANDLES + 30)

        for ticker, uid in tickers.items():
            try:
                # Use get_all_candles for reliable pagination
                candles = list(
                    client.get_all_candles(
                        instrument_id=uid,
                        from_=from_time,
                        to=to_time,
                        interval=CandleInterval.CANDLE_INTERVAL_DAY,
                    )
                )
                if len(candles) < 30:
                    continue

                df = prepare_candle_data(candles)
                df = calculate_indicators(df)
                metrics = calculate_squeeze_score(df, ATR_THRESHOLD)

                results[ticker] = {
                    "price": float(df.iloc[-1]["close"]),
                    "metrics": metrics,
                }
            except Exception:
                continue

    return results
