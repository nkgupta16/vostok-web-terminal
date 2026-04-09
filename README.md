# 🚀 Vostok Web Terminal

**Professional-grade MOEX Quantitative Trading Dashboard** — Streamlit Web Application for 24/7 deployment on Streamlit Community Cloud.

Migrated from the [MOEX_Dip_Scanner](../MOEX_Dip_Scanner/) PyQt6 v3.2.0 desktop terminal.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📈 Dashboard** | Quantitative Confidence Scoring (0-100%) with weighted RSI/BB/Volume/MACD signals |
| **💥 Squeeze** | Pre-pump volatility squeeze detection via BB Width percentile, OBV slope, ATR ratio |
| **💼 Portfolio** | Real-time portfolio with positions, P&L, Day P&L, and recent operations |
| **📅 Dividends** | Cross-references held tickers with upcoming dividends — Expected Payout & Yield % |
| **🎮 Sandbox** | T-Bank SandboxClient for paper trading — virtual deposits and BUY execution |
| **🧠 Strategy** | Equity Curve and Drawdown charts for "Dip" and "Squeeze" strategy backtests |

## 🏗️ Architecture

```
Vostok_Web_Terminal/
├── app.py                  # Main Streamlit UI & Navigation
├── services/
│   ├── auth.py             # Triple-Layer Credential System
│   ├── indicators.py       # Pure math engine (no Streamlit dependency)
│   ├── market.py           # T-Bank API & data fetching
│   └── portfolio.py        # Dividend & Account logic + Sandbox
├── .streamlit/
│   └── config.toml         # Dark theme, layout settings
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔑 Triple-Layer Credential System

The token is resolved with this priority:

1. **Manual Override** — paste into the sidebar password field
2. **Local `.env`** — `INVEST_TOKEN=your_token_here`
3. **Streamlit Cloud Secrets** — Dashboard → Settings → Secrets

## 🚀 Deployment on Streamlit Community Cloud

### Step 1: Push to Private GitHub Repo

```bash
cd Vostok_Web_Terminal
git init
git add .
git commit -m "Initial: Vostok Web Terminal"
git remote add origin https://github.com/YOUR_USER/vostok-web-terminal.git
git push -u origin main
```

### Step 2: Connect on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"New app"**
3. Select your **private repo** → branch: `main` → file: `app.py`

### Step 3: Add INVEST_TOKEN Secret

1. In the Streamlit app dashboard, click **"Settings"** (⚙️)
2. Go to **"Secrets"** tab
3. Paste:

```toml
INVEST_TOKEN = "your_tbank_api_token_here"
```

4. Click **Save** → the app will automatically restart

> ⚠️ The T-Bank SDK requires a custom PyPI index. Add this to `packages.txt` or use the install command in the requirements comment.

### Step 4: Install T-Bank SDK

The `t-tech-investments` package requires a custom index. On Streamlit Cloud, create a `packages.txt` if needed, or install via:

```
# In requirements.txt (already included as a comment):
# pip install t-tech-investments --index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

For Streamlit Cloud, you may need to add a `setup.sh`:
```bash
#!/bin/bash
pip install t-tech-investments --index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

## 🖥️ Local Development

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install t-tech-investments --index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple

# Configure token
copy .env.example .env
# Edit .env and add your INVEST_TOKEN

# Run
streamlit run app.py
```

## 🎨 Theme

- **Layout:** Wide mode (forced via `set_page_config`)
- **Color Palette:** Electric Blue `#00e5ff` accent on dark `#0a0e12` background
- **Fonts:** Inter (UI) + JetBrains Mono (data/monospace)
- **Auto-Scan:** Toggle in sidebar with 30s/60s/120s/300s intervals

## ⚠️ Safety

- **No real orders** — all execution buttons route to the Sandbox Service
- `indicators.py` has zero Streamlit imports — can be tested independently
- Token is never logged or displayed in the UI

## 📄 License

Private project — all rights reserved.
