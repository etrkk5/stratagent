"""Original, dependency-free inventory review pilot. No network or file writes."""
import argparse
import csv
import io
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 256 * 1024
MAX_ROWS = 1000
SKU = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
QUANTITY = re.compile(r"[0-9]{1,9}")


def review(data):
    if len(data) > MAX_BYTES:
        raise ValueError("CSV exceeds 256 KiB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("CSV must be UTF-8.") from None
    rows = csv.reader(io.StringIO(text, newline=""), strict=True)
    issues, seen, count = [], set(), 0
    try:
        if next(rows, None) != ["sku", "quantity"]:
            raise ValueError("CSV headers must be exactly sku,quantity.")
        for record, fields in enumerate(rows, start=2):
            if not fields:
                continue
            count += 1
            if count > MAX_ROWS:
                raise ValueError("CSV exceeds 1000 records.")
            if len(fields) != 2:
                issues.append({"record": record, "rule": "column-count"})
                continue
            sku, quantity = (field.strip() for field in fields)
            if not SKU.fullmatch(sku):
                issues.append({"record": record, "rule": "invalid-sku"})
            elif sku in seen:
                issues.append({"record": record, "rule": "duplicate-sku"})
            else:
                seen.add(sku)
            if not QUANTITY.fullmatch(quantity):
                issues.append({"record": record, "rule": "invalid-quantity"})
    except csv.Error:
        raise ValueError("Malformed CSV.") from None
    return {"schema_version": 1, "ok": not issues, "records_checked": count, "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review local inventory CSV without modifying it.")
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.csv_file.open("rb") as handle:
            result = review(handle.read(MAX_BYTES + 1))
    except (OSError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) else "CSV file is not readable."
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
