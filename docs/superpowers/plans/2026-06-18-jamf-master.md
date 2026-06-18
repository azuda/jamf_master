# jamf_master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Weekly read-only Jamf inventory audit that fetches all computers and mobile devices, checks required fields for missing/blank values, and writes a timestamped CSV log of devices with gaps.

**Architecture:** Single `run.py` script imports `jamf_client` for auth/HTTP, calls two paginated GET endpoints (one per device type with all needed sections), runs each device through a declarative field-check table, then writes a CSV to the path in `$LOG_FILE`. Pure logic functions live at module level (testable); `jamf_client` is imported inside `main()` so tests don't need a `.env`.

**Tech Stack:** Python 3.11+, `jamf_client` (local editable package at `~/Scripts/jamf_client`), `pytest`, Jamf Pro REST API v3 (computers) / v2 (mobile devices)

## Global Constraints

- Import `jamf_client` inside `main()` only — never at module level — so `tests/test_run.py` can import pure functions without triggering env-var validation
- Token dict shape: `{"t": str, "expiration": int}` — matches `jamf_client` convention
- Missing sentinel values: `None`, `""`, whitespace-only, `"None"` (Jamf unassigned site), `"-1"` (Jamf unassigned department/building ID)
- Log rotation: keep last 8 files (`tail -n +9`)
- All paths relative to project root; script must be run from project root (`./run.sh`)

---

## File Map

| File | Purpose |
|---|---|
| `run.py` | Pure logic functions + `main()`: GET inventory, check fields, write CSV |
| `run.sh` | Activate venv, set `$LOG_FILE`, rotate logs, run `run.py` |
| `requirements.txt` | `-e ../jamf_client` + `pytest` |
| `.env` | `CLIENT_ID`, `CLIENT_SECRET`, `JAMF_URL` (not committed) |
| `.env.example` | Template for the three env vars |
| `.gitignore` | Excludes `.env`, `debug/`, `logs/`, `.venv/`, `__pycache__/` |
| `tests/test_run.py` | Unit tests for `is_missing` and `get_missing_fields` |
| `logs/` | Timestamped CSV audit logs (created at runtime) |
| `debug/` | Raw API JSON responses `c.json`, `d.json` (created at runtime) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `run.sh`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Produces: working venv with `jamf_client` importable; `./run.sh` wired to run `run.py`

- [ ] **Step 1: Create `run.sh`**

```sh
#!/bin/sh

PROJECT="$PWD"
VENV="$PROJECT/.venv/bin/python3"

LOG_DIR="$PROJECT/logs"
timestamp=$(date '+%Y%m%d %H%M')
export LOG_FILE="$LOG_DIR/$timestamp.log"

mkdir -p "$LOG_DIR"
ls -1t "$LOG_DIR" | tail -n +9 | xargs -I {} rm -f "$LOG_DIR/{}"

echo "Script start @ $(date)"
$VENV -u run.py
echo "Script done @ $(date)"
```

- [ ] **Step 2: Create `requirements.txt`**

```
-e ../jamf_client
pytest
```

- [ ] **Step 3: Create `.env.example`**

```
CLIENT_ID=
CLIENT_SECRET=
JAMF_URL=https://yourinstance.jamfcloud.com
```

- [ ] **Step 4: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
debug/
logs/
.DS_Store
```

- [ ] **Step 5: Create `.env` from example and fill in credentials**

Copy `.env.example` to `.env` and populate `CLIENT_ID`, `CLIENT_SECRET`, `JAMF_URL` with the same values used in `~/Scripts/jamf_purchasing_import/.env`.

- [ ] **Step 6: Create venv and install dependencies**

```bash
cd ~/Scripts/jamf_master
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

- [ ] **Step 7: Verify `jamf_client` is importable**

```bash
.venv/bin/python3 -c "from jamf_client import get_token, make_session, jamf_get; print('ok')"
```

Expected output: `ok`

- [ ] **Step 8: Make `run.sh` executable**

```bash
chmod +x run.sh
```

- [ ] **Step 9: Commit scaffold**

```bash
git init
git add run.sh requirements.txt .env.example .gitignore
git commit -m "chore: project scaffold"
```

---

## Task 2: Core Field-Check Logic + Tests

**Files:**
- Create: `run.py` (pure functions only — no `main()` yet)
- Create: `tests/test_run.py`

**Interfaces:**
- Produces:
  - `is_missing(val: Any) -> bool`
  - `_ext_attr(name: str, entry: dict) -> str | None`
  - `COMPUTER_FIELDS: list[tuple[str, Callable]]`
  - `DEVICE_FIELDS: list[tuple[str, Callable]]`
  - `get_missing_fields(entry: dict, fields: list[tuple[str, Callable]]) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/__init__.py` (empty) and `tests/test_run.py`:

```python
# tests/test_run.py

from run import is_missing, get_missing_fields, COMPUTER_FIELDS, DEVICE_FIELDS


# ── is_missing ──────────────────────────────────────────────────────────────

def test_is_missing_none():
    assert is_missing(None) is True

def test_is_missing_empty_string():
    assert is_missing("") is True

def test_is_missing_whitespace():
    assert is_missing("   ") is True

def test_is_missing_jamf_none_site():
    assert is_missing("None") is True

def test_is_missing_jamf_minus_one():
    assert is_missing("-1") is True

def test_is_missing_valid_string():
    assert is_missing("Rundle College") is False

def test_is_missing_valid_price():
    assert is_missing("$999.00") is False


# ── get_missing_fields — computers ──────────────────────────────────────────

def _full_computer():
    return {
        "general": {"name": "RCSTU-ABC12", "site": {"name": "RCS"}},
        "hardware": {"serialNumber": "C02XXXXXXX"},
        "userAndLocation": {
            "username": "jsmith",
            "realName": "John Smith",
            "email": "jsmith@rundle.ab.ca",
            "position": "EGY2028",
            "departmentId": "3",
            "buildingId": "2",
        },
        "purchasing": {
            "poNumber": "PO-1234",
            "poDate": "2024-09-01",
            "vendor": "Apple",
            "purchasePrice": "$999.00",
        },
        "extensionAttributes": [
            {"name": "Rundle Device Report", "values": ["OS: 15.0\n\nUPTIME\n48"]},
        ],
    }

def test_computer_all_present():
    assert get_missing_fields(_full_computer(), COMPUTER_FIELDS) == []

def test_computer_missing_username():
    c = _full_computer()
    c["userAndLocation"]["username"] = ""
    assert get_missing_fields(c, COMPUTER_FIELDS) == ["username"]

def test_computer_jamf_site_sentinel():
    c = _full_computer()
    c["general"]["site"]["name"] = "None"
    assert "site" in get_missing_fields(c, COMPUTER_FIELDS)

def test_computer_jamf_department_sentinel():
    c = _full_computer()
    c["userAndLocation"]["departmentId"] = "-1"
    assert "department" in get_missing_fields(c, COMPUTER_FIELDS)

def test_computer_jamf_building_sentinel():
    c = _full_computer()
    c["userAndLocation"]["buildingId"] = "-1"
    assert "building" in get_missing_fields(c, COMPUTER_FIELDS)

def test_computer_missing_ext_attr_empty_values():
    c = _full_computer()
    c["extensionAttributes"] = [{"name": "Rundle Device Report", "values": []}]
    assert "rundleDeviceReport" in get_missing_fields(c, COMPUTER_FIELDS)

def test_computer_missing_ext_attr_absent():
    c = _full_computer()
    c["extensionAttributes"] = []
    assert "rundleDeviceReport" in get_missing_fields(c, COMPUTER_FIELDS)


# ── get_missing_fields — devices ─────────────────────────────────────────────

def _full_device():
    return {
        "general": {
            "name": "iPad-RCS-001",
            "assetTag": "RCS-001",
            "serialNumber": "DMPXXXXXXX",
            "site": {"name": "RCS"},
        },
        "userAndLocation": {
            "username": "jsmith",
            "realName": "John Smith",
            "emailAddress": "jsmith@rundle.ab.ca",
            "position": "EGY2028",
            "department": "Student",
            "building": "Main",
        },
        "purchasing": {
            "poNumber": "PO-5678",
            "poDate": "2024-09-01",
            "vendor": "Apple",
            "purchasePrice": "$499.00",
        },
    }

def test_device_all_present():
    assert get_missing_fields(_full_device(), DEVICE_FIELDS) == []

def test_device_missing_asset_tag():
    d = _full_device()
    d["general"]["assetTag"] = None
    assert get_missing_fields(d, DEVICE_FIELDS) == ["assetTag"]

def test_device_missing_email():
    d = _full_device()
    d["userAndLocation"]["emailAddress"] = ""
    assert "email" in get_missing_fields(d, DEVICE_FIELDS)

def test_device_multiple_missing():
    d = _full_device()
    d["general"]["assetTag"] = None
    d["purchasing"]["vendor"] = ""
    result = get_missing_fields(d, DEVICE_FIELDS)
    assert "assetTag" in result
    assert "vendor" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_run.py -v
```

Expected: `ModuleNotFoundError: No module named 'run'` or `ImportError` — confirms tests are wired but nothing is implemented yet.

- [ ] **Step 3: Create `run.py` with pure logic only**

```python
# run.py

"""
- get all computers and mobile devices from jamf
- check required fields for missing/blank values
- write csv log of devices with missing fields to $LOG_FILE
"""

import csv
import json
import os

# ==================================================================================

JAMF_MISSING = {"None", "-1"}


def is_missing(val):
    if val is None:
        return True
    if isinstance(val, str) and (not val.strip() or val.strip() in JAMF_MISSING):
        return True
    return False


def _ext_attr(name, entry):
    for ea in entry.get("extensionAttributes", []):
        if ea.get("name") == name:
            vals = ea.get("values", [])
            return vals[0] if vals else None
    return None


COMPUTER_FIELDS = [
    ("name",               lambda c: c["general"]["name"]),
    ("site",               lambda c: c["general"]["site"]["name"]),
    ("username",           lambda c: c["userAndLocation"]["username"]),
    ("fullName",           lambda c: c["userAndLocation"]["realName"]),
    ("email",              lambda c: c["userAndLocation"]["email"]),
    ("position",           lambda c: c["userAndLocation"]["position"]),
    ("department",         lambda c: c["userAndLocation"]["departmentId"]),
    ("building",           lambda c: c["userAndLocation"]["buildingId"]),
    ("poNumber",           lambda c: c["purchasing"]["poNumber"]),
    ("poDate",             lambda c: c["purchasing"]["poDate"]),
    ("vendor",             lambda c: c["purchasing"]["vendor"]),
    ("purchasePrice",      lambda c: c["purchasing"]["purchasePrice"]),
    ("rundleDeviceReport", lambda c: _ext_attr("Rundle Device Report", c)),
]

DEVICE_FIELDS = [
    ("name",          lambda d: d["general"]["name"]),
    ("assetTag",      lambda d: d["general"]["assetTag"]),
    ("site",          lambda d: d["general"]["site"]["name"]),
    ("username",      lambda d: d["userAndLocation"]["username"]),
    ("fullName",      lambda d: d["userAndLocation"]["realName"]),
    ("email",         lambda d: d["userAndLocation"]["emailAddress"]),
    ("position",      lambda d: d["userAndLocation"]["position"]),
    ("department",    lambda d: d["userAndLocation"]["department"]),
    ("building",      lambda d: d["userAndLocation"]["building"]),
    ("poNumber",      lambda d: d["purchasing"]["poNumber"]),
    ("poDate",        lambda d: d["purchasing"]["poDate"]),
    ("vendor",        lambda d: d["purchasing"]["vendor"]),
    ("purchasePrice", lambda d: d["purchasing"]["purchasePrice"]),
]


def get_missing_fields(entry, fields):
    missing = []
    for label, extractor in fields:
        try:
            val = extractor(entry)
        except (KeyError, TypeError):
            val = None
        if is_missing(val):
            missing.append(label)
    return missing

# ==================================================================================

if __name__ == "__main__":
    pass  # main() added in Task 3
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_run.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add run.py tests/
git commit -m "feat: core field-check logic with tests"
```

---

## Task 3: `main()` — API Integration + CSV Log

**Files:**
- Modify: `run.py` — replace the `if __name__ == "__main__": pass` block with a full `main()` + invocation

**Interfaces:**
- Consumes: `is_missing`, `COMPUTER_FIELDS`, `DEVICE_FIELDS`, `get_missing_fields` from Task 2
- Consumes: `get_token`, `invalidate_token`, `make_session`, `jamf_get` from `jamf_client`
- Produces: `logs/<YYYYMMDD HHMM>.log` (CSV), `debug/c.json`, `debug/d.json`, stdout summary

- [ ] **Step 1: Replace the stub block in `run.py` with `main()`**

Replace the final block of `run.py` (the `if __name__ == "__main__": pass` stub) with:

```python
# ==================================================================================

def main():
    import time
    from jamf_client import get_token, invalidate_token, make_session, jamf_get

    log_file = os.environ.get("LOG_FILE")

    access_token, expires_in = get_token()
    token = {"t": access_token, "expiration": int(time.time()) + expires_in}
    session = make_session()

    computers = jamf_get(
        "/api/v3/computers-inventory"
        "?section=GENERAL&section=HARDWARE&section=USER_AND_LOCATION"
        "&section=PURCHASING&section=EXTENSION_ATTRIBUTES"
        "&page=0&page-size=2000&sort=id%3Aasc",
        token, session,
    ).json()["results"]

    devices = jamf_get(
        "/api/v2/mobile-devices/detail"
        "?section=GENERAL&section=USER_AND_LOCATION&section=PURCHASING"
        "&page=0&page-size=2000&sort=mobileDeviceId%3Aasc",
        token, session,
    ).json()["results"]

    os.makedirs("debug", exist_ok=True)
    with open("debug/c.json", "w") as f:
        json.dump(computers, f, indent=2)
    with open("debug/d.json", "w") as f:
        json.dump(devices, f, indent=2)

    rows = []
    for c in computers:
        missing = get_missing_fields(c, COMPUTER_FIELDS)
        if missing:
            rows.append({
                "type": "computer",
                "id": c["id"],
                "name": c["general"]["name"],
                "serial_number": c.get("hardware", {}).get("serialNumber", ""),
                "missing_fields": ";".join(missing),
            })

    for d in devices:
        missing = get_missing_fields(d, DEVICE_FIELDS)
        if missing:
            rows.append({
                "type": "mobile_device",
                "id": d["mobileDeviceId"],
                "name": d["general"]["name"],
                "serial_number": d.get("general", {}).get("serialNumber", ""),
                "missing_fields": ";".join(missing),
            })

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["type", "id", "name", "serial_number", "missing_fields"]
            )
            writer.writeheader()
            writer.writerows(rows)

    c_missing = sum(1 for r in rows if r["type"] == "computer")
    d_missing = sum(1 for r in rows if r["type"] == "mobile_device")
    print(f"Computers: {len(computers)} total, {c_missing} with missing fields")
    print(f"Devices: {len(devices)} total, {d_missing} with missing fields")

    invalidate_token(access_token)


# ==================================================================================

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Confirm existing tests still pass**

```bash
.venv/bin/pytest tests/test_run.py -v
```

Expected: all tests `PASSED` — `main()` is not imported at module level so tests are unaffected.

- [ ] **Step 3: Run the script end-to-end**

```bash
./run.sh
```

Expected terminal output (numbers will vary):
```
Script start @ Wed Jun 18 10:30:00 MDT 2026
Computers: 450 total, 3 with missing fields
Devices: 200 total, 5 with missing fields
Script done @ Wed Jun 18 10:30:12 MDT 2026
```

- [ ] **Step 4: Verify debug output**

```bash
python3 -c "import json; d=json.load(open('debug/c.json')); print(list(d[0].keys()))"
```

Expected: `['id', 'general', 'hardware', 'userAndLocation', 'purchasing', 'extensionAttributes']` (all requested sections present)

- [ ] **Step 5: Verify log file**

```bash
ls logs/
```

Expected: one `.log` file with a timestamp name (e.g. `20260618 1030.log`)

```bash
head -5 logs/*.log
```

Expected: CSV with header row followed by rows for any devices with missing fields:
```
type,id,name,serial_number,missing_fields
computer,1234,RCSTU-ABC12,C02XXXXXXX,username;email
```

If all devices are fully populated, the log will have only the header row — that is correct behaviour.

- [ ] **Step 6: Verify log rotation (run twice more and check only 8 logs kept)**

```bash
./run.sh && ./run.sh
ls logs/ | wc -l
```

Expected: `3` (three runs so far, all kept since we're under the limit of 8)

- [ ] **Step 7: Commit**

```bash
git add run.py
git commit -m "feat: main() with api integration and csv audit log"
```
