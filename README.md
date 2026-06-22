# jamf_master

Audits Jamf Pro for devices with missing or blank required fields and outputs a CSV report.

## What it does

1. Fetches all computers and mobile devices from the Jamf Pro API
2. Checks each device for missing/blank values across fields like username, email, department, site, purchasing info, etc.
3. Writes a timestamped CSV log of offending devices to `logs/`

Raw API responses are saved to `debug/c.json` and `debug/d.json` for troubleshooting.

## Setup

Requires a `jamf_client` package installed from `../jamf_client`. Set credentials in `.env`.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```sh
./run.sh
```

Logs are written to `logs/<timestamp>.csv`. The last 8 logs are kept automatically.

To run manually with a custom log path:

```sh
LOG_FILE=output.csv python3 run.py
```

## CSV columns

| Column | Description |
|---|---|
| `type` | `computer` or `mobile_device` |
| `id` | Jamf device ID |
| `name` | Device display name |
| `serial_number` | Hardware serial number |
| `missing_fields` | Semicolon-separated list of blank fields |

## Tests

```sh
pytest
```
