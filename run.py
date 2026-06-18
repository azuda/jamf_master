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
