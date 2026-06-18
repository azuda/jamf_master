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
    ("name",          lambda d: d["general"]["displayName"]),
    ("assetTag",      lambda d: d["general"]["assetTag"]),
    ("site",          lambda d: None if d["general"].get("siteId", -1) in (None, -1) else d["general"]["siteId"]),
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
                "name": d["general"].get("name") or d["general"].get("displayName", ""),
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
