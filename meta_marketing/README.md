# PawPath Meta Marketing API

Python 3.12 application for Meta (Facebook) Ads account insights, campaign management, ad analysis, and daily reporting via the [Facebook Business SDK](https://github.com/facebook/facebook-python-business-sdk).

## Project structure

```
meta_marketing/
├── __main__.py          # CLI entry point
├── api/                 # Facebook SDK wrapper
│   └── meta_client.py
├── services/            # Business logic
│   ├── account_service.py
│   ├── campaign_service.py
│   └── ad_analysis_service.py
├── reports/             # Report builders + exporters
│   ├── daily_report.py
│   └── exporters.py
├── utils/               # Config, dates, metrics parsing
│   ├── config.py
│   ├── dates.py
│   └── metrics.py
└── requirements.txt
```

Reports are written to `data/meta_reports/` by default.

## Prerequisites

- Python 3.12+
- A Meta Business Manager account with an ad account
- A Meta app with Marketing API access
- A long-lived **System User** access token with `ads_read` and `ads_management` permissions

## Installation

From the PawPath repo root:

```bash
python3.12 -m venv .venv-meta
source .venv-meta/bin/activate
pip install -r meta_marketing/requirements.txt
```

## Environment setup

Add these variables to your root `.env` file (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `META_APP_ID` | Meta app ID |
| `META_APP_SECRET` | Meta app secret |
| `META_ACCESS_TOKEN` | Long-lived access token |
| `META_AD_ACCOUNT_ID` | Ad account ID (`act_123…` or numeric `123…`) |

### Getting credentials

1. Go to [Meta for Developers](https://developers.facebook.com/) → **My Apps** → create or select an app.
2. Add the **Marketing API** product.
3. In **Business Settings** → **System Users**, create a system user and generate a token with:
   - `ads_read`
   - `ads_management`
4. Assign the system user access to your ad account.
5. Copy the ad account ID from Ads Manager (format: `act_XXXXXXXXX`).

## Usage

All commands run from the repo root. **Progress logs** print to stderr with elapsed timestamps; **JSON results** print to stdout.

```bash
python -m meta_marketing <command>       # verbose progress (default)
python -m meta_marketing -q <command>    # JSON only, no progress logs
```

Example log output:

```
[0s] ━━ Meta Marketing — account overview ━━
[0s]   Initializing Meta API for act_123...
[0s] ▶ Meta API authentication
[1s] ✓ Meta API authentication (0.8s)
[1s] ▶ Fetch account insights (last_7d)
[2s] ✓ Fetch account insights (last_7d) (1.1s)
[2s]   Spend $120.50 | Impressions 15,000 | Clicks 320 | ...
[2s] Done
```

```bash
python -m meta_marketing <command>
```

### Account overview

Spend, impressions, clicks, CTR, CPC, CPM, purchases, and ROAS:

```bash
python -m meta_marketing account
python -m meta_marketing account --preset last_30d
python -m meta_marketing account --day 2026-06-13
```

### Campaign management

```bash
# List campaigns
python -m meta_marketing campaigns list

# Pause / resume
python -m meta_marketing campaigns pause 120330000000000000
python -m meta_marketing campaigns resume 120330000000000000

# Performance (single campaign or all)
python -m meta_marketing campaigns performance
python -m meta_marketing campaigns performance 120330000000000000 --preset last_7d
```

### Ad analysis

Identifies winning and losing ads vs account benchmarks and returns recommendations:

```bash
python -m meta_marketing ads analyze
python -m meta_marketing ads analyze --preset last_14d
```

### Daily report (JSON + CSV)

```bash
python -m meta_marketing report daily
python -m meta_marketing report daily --day 2026-06-13 --output-dir data/meta_reports
```

Output files:

- `data/meta_reports/meta_daily_YYYY-MM-DD.json`
- `data/meta_reports/meta_daily_YYYY-MM-DD.csv`

## Metrics

| Metric | Source |
|--------|--------|
| Spend | `spend` |
| Impressions | `impressions` |
| Clicks | `clicks` |
| CTR | `ctr` |
| CPC | `cpc` |
| CPM | `cpm` |
| Purchases | `actions` (purchase / omni_purchase) |
| ROAS | `purchase_roas` or purchase value ÷ spend |

## Scheduling daily reports

Example cron (runs at 6:00 AM UTC):

```cron
0 6 * * * cd /path/to/PawPath && .venv-meta/bin/python -m meta_marketing report daily >> logs/meta_report.log 2>&1
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| Missing env vars | Fill in all four `META_*` values in `.env` |
| `(#200) Requires ads_read permission` | Regenerate token with `ads_read` |
| `(#200) Requires ads_management permission` | Add `ads_management` for pause/resume |
| Empty insights | Account may have no spend on the selected date |
| Invalid ad account | Use `act_` prefix or numeric ID from Ads Manager |

## License

Internal PawPath tooling.
