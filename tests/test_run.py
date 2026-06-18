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
