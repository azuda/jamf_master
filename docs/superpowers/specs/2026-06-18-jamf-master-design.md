# jamf_master — Design Spec

**Date:** 2026-06-18
**Status:** Approved

## Problem

No systematic way to catch devices in the Jamf inventory that are missing key fields (name, site, user info, purchasing data, extension attribute). Issues are discovered ad-hoc and fixed manually with no audit trail.

## Goal

Weekly read-only audit of all Jamf computers and mobile devices. Flag any device with missing required fields and write the results to a timestamped CSV log for human review and future automated remediation.

## Out of Scope

- Patching missing fields (logging only; patching to be built in a future iteration)
- Alerting or notifications
- Pagination beyond 2000 devices per type

---

## Structure

```
jamf_master/
  run.py            # main script
  run.sh            # venv activation, log path, log rotation
  requirements.txt  # jamf_client editable install
  .env              # CLIENT_ID, CLIENT_SECRET, JAMF_URL
  .env.example
  .gitignore
  logs/             # timestamped CSV audit logs
  debug/            # raw API JSON responses (c.json, d.json)
```

---

## API Calls

Two GET requests, one per device type, each with all required sections in a single call.

**Computers** (`/api/v3/computers-inventory`):
```
?section=GENERAL&section=HARDWARE&section=USER_AND_LOCATION
&section=PURCHASING&section=EXTENSION_ATTRIBUTES
&page=0&page-size=2000&sort=id:asc
```

**Mobile devices** (`/api/v2/mobile-devices/detail`):
```
?section=GENERAL&section=USER_AND_LOCATION&section=PURCHASING
&page=0&page-size=2000&sort=mobileDeviceId:asc
```

HARDWARE is included for computers to get `hardware.serialNumber`. Mobile device serial number is at `general.serialNumber`.

---

## Audited Fields

### Computers

| Label | API path |
|---|---|
| `name` | `general.name` |
| `site` | `general.site.name` |
| `username` | `userAndLocation.username` |
| `fullName` | `userAndLocation.realName` |
| `email` | `userAndLocation.email` |
| `position` | `userAndLocation.position` |
| `department` | `userAndLocation.departmentId` |
| `building` | `userAndLocation.buildingId` |
| `poNumber` | `purchasing.poNumber` |
| `poDate` | `purchasing.poDate` |
| `vendor` | `purchasing.vendor` |
| `purchasePrice` | `purchasing.purchasePrice` |
| `rundleDeviceReport` | `extensionAttributes[name="Rundle Device Report"].values[0]` |

### Mobile Devices

| Label | API path |
|---|---|
| `name` | `general.name` |
| `assetTag` | `general.assetTag` |
| `site` | `general.site.name` |
| `username` | `userAndLocation.username` |
| `fullName` | `userAndLocation.realName` |
| `email` | `userAndLocation.emailAddress` |
| `position` | `userAndLocation.position` |
| `department` | `userAndLocation.department` |
| `building` | `userAndLocation.building` |
| `poNumber` | `purchasing.poNumber` |
| `poDate` | `purchasing.poDate` |
| `vendor` | `purchasing.vendor` |
| `purchasePrice` | `purchasing.purchasePrice` |

---

## Missing Value Detection

A field is considered missing if its value is any of:

- `None`
- `""` (empty string)
- Whitespace-only string
- `"None"` — Jamf's default `site.name` for unassigned devices
- `"-1"` — Jamf's unassigned sentinel for `departmentId` / `buildingId` (computers v3 returns these as IDs, not names)

---

## Log Format

Python writes a pure CSV directly to the `LOG_FILE` path (set by `run.sh` and passed via environment variable). Only devices with at least one missing field appear.

**Columns:** `type, id, name, serial_number, missing_fields`

`missing_fields` is a semicolon-delimited list of field labels within the cell.

**Example:**
```csv
type,id,name,serial_number,missing_fields
computer,1234,RCSTU-ABC12,C02XXXXXXX,username;email;poDate
mobile_device,567,iPad-RCS-123,DMPXXXXXXX,assetTag;vendor
```

Python also prints a text summary to stdout:
```
Computers: 450 total, 3 with missing fields
Devices: 200 total, 5 with missing fields
```

---

## Shell Wrapper (`run.sh`)

Follows the same pattern as `jamf_purchasing_import/run.sh`:

- Activates the project `.venv`
- Sets and exports `LOG_FILE` as `logs/YYYYMMDD HHMM.log`
- Creates `logs/` if absent
- Rotates logs: keeps last 8 (≈2 months at weekly cadence)
- Runs `python3 run.py`
- Prints script start/done timestamps to terminal

---

## Dependencies

```
-e ~/Scripts/jamf_client
```

`jamf_client` provides `JAMF_URL`, `get_token`, `invalidate_token`, `check_token_expiration`, `make_session`, `jamf_get`. No other dependencies needed — `requests`, `python-dotenv`, `urllib3`, and `truststore` are pulled in transitively.

---

## Token Handling

Follows the `jamf_client` token dict pattern used across all other Jamf scripts:

```python
access_token, expires_in = get_token()
token = {"t": access_token, "expiration": int(time.time()) + expires_in}
```

`jamf_get` calls `check_token_expiration` internally before each request. Token is invalidated after all work is complete.

---

## Scheduling

Intended for weekly execution via `launchd` plist (same pattern as `com.jamfpurchasing.daemon.plist` in the purchasing import project), deployed on an on-prem server / different machine.
