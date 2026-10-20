import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from stratagent.service import Stratagent

PILOT = Path(__file__).resolve().parents[1] / "examples/projects/inventory-review"
SPEC = importlib.util.spec_from_file_location("inventory_pilot", PILOT / "inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class InventoryPilotTests(unittest.TestCase):
    def test_valid_and_original_invalid_examples(self):
        self.assertTrue(inventory.review((PILOT / "valid.csv").read_bytes())["ok"])
        result = inventory.review((PILOT / "invalid.csv").read_bytes())
        self.assertFalse(result["ok"])
        self.assertEqual(result["records_checked"], 3)
        self.assertEqual([item["rule"] for item in result["issues"]], ["duplicate-sku", "invalid-quantity", "invalid-sku", "invalid-quantity"])

    def test_bom_whitespace_zero_and_case_sensitive_skus(self):
        self.assertTrue(inventory.review(b"\xef\xbb\xbfsku,quantity\r\n a , 0 \r\nA,1\r\n\r\n")["ok"])

    def test_quantities_and_skus_are_bounded_ascii(self):
        for sku, quantity in (("=FORMULA", "1"), ("A", "1.5"), ("A", "-1"), ("A", "9999999999"), ("A", "\u0661"), ("A" * 65, "1")):
            with self.subTest(sku=sku, quantity=quantity):
                self.assertFalse(inventory.review(f"sku,quantity\n{sku},{quantity}\n".encode())["ok"])

    def test_missing_extra_columns_and_fields_are_reported_without_content(self):
        result = inventory.review(b"sku,quantity\nPRIVATE-SKU\nA,1,extra\n,\n")
        self.assertEqual([item["rule"] for item in result["issues"]], ["column-count", "column-count", "invalid-sku", "invalid-quantity"])
        self.assertNotIn("PRIVATE-SKU", json.dumps(result))

    def test_invalid_encoding_headers_and_quoting_fail(self):
        for data in (b"", b"sku,count\nA,1", b"quantity,sku\n1,A", b"sku,quantity\n\xff,1", b'sku,quantity\n"A,1'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                inventory.review(data)

    def test_record_and_byte_limits(self):
        self.assertEqual(inventory.review(b"sku,quantity\n" + b"A,1\n" * 1000)["records_checked"], 1000)
        for data in (b"sku,quantity\n" + b"A,1\n" * 1001, b"x" * (inventory.MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                inventory.review(data)

    def test_cli_exit_codes_and_no_input_changes(self):
        for filename, expected in (("valid.csv", 0), ("invalid.csv", 1), ("absent.csv", 2)):
            path = PILOT / filename
            before = path.read_bytes() if path.exists() else None
            result = subprocess.run([sys.executable, str(PILOT / "inventory.py"), str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertIsInstance(json.loads(result.stderr if expected == 2 else result.stdout), dict)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(path.read_bytes() if path.exists() else None, before)

    def test_real_pilot_copy_has_a_reviewed_repeatable_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "inventory-review"
            shutil.copytree(PILOT, target, ignore=shutil.ignore_patterns("__pycache__"))
            originals = {path.name: path.read_bytes() for path in target.iterdir() if path.is_file()}
            service = Stratagent(target)
            service.init("Small Python CSV inventory review. Offline operation. No web UI and no payments.", ["codex", "antigravity", "claude", "generic"])
            decision = service.decision_request()["suggested_decision"]
            decision["reason"] = "Original test fixture chooses focused ownership for a small offline inventory workflow."
            preview, files = service.preview_blueprint(decision)
            self.assertFalse(preview["blockers"])
            self.assertIn(".agents/skills/sa-test-reviewer/SKILL.md", files)
            self.assertTrue(all(not item["binding"]["mcps"] for item in preview["source"]["blueprint"]["roles"]))
            service.blueprint(decision, preview["approval"], True)
            self.assertTrue(service.blueprint(decision, preview["approval"], True)["already_installed"])
            self.assertTrue(service.verify()["ok"])
            self.assertEqual({name: (target / name).read_bytes() for name in originals}, originals)
            self.assertTrue(service.status()["approved_blueprint"]["context_current"])
