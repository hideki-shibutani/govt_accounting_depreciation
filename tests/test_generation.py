import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPORARY = ROOT / ".test-tmp"
TEMPORARY.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_input import prepare_input
from build_csv import build, write_csv
import pandas as pd


def make_raw(path, *, english=False):
    fields = ["団体コード", "団体名", "都道府県", "表", "対象", "指標", "2022", "2023"]
    aliases = {"団体コード": "organization_code", "団体名": "organization_name", "都道府県": "prefecture_name",
               "表": "table_name", "対象": "target_name", "指標": "item_name"}
    if english:
        fields = [aliases.get(field, field) for field in fields]
    for code, name in [("010006", "北海道"), ("011002", "北海道札幌市")]:
        with (path / (code + ".csv")).open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerow([code, name, "北海道", "公会計指標分析・財政指標組合せ分析表", "当該団体値", "有形固定資産減価償却率", "59", "60.1"])
            writer.writerow([code, name, "北海道", "施設類型別ストック情報分析表①", "当該団体値", "【図書館】有形固定資産減価償却率", "", "70.2"])
            writer.writerow([code, name, "北海道", "施設類型別ストック情報分析表①", "類似団体平均値", "【図書館】有形固定資産減価償却率", "88", "89"])


class GenerationTest(unittest.TestCase):
    def test_english_and_legacy_inputs_produce_identical_public_input(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY) as temporary:
            root = Path(temporary)
            for name, english in [("legacy", False), ("english", True)]:
                raw = root / name; raw.mkdir()
                make_raw(raw, english=english)
                result = prepare_input(raw, root / (name + ".csv.gz"))
                self.assertEqual(result["indicator_rows"], 4)
            self.assertEqual((root / "legacy.csv.gz").read_bytes(), (root / "english.csv.gz").read_bytes())

    def test_same_size_value_change_is_written(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY) as temporary:
            path = Path(temporary) / "test.csv"
            write_csv(pd.DataFrame({"rate": ["12.3"]}), path, index=False)
            size = path.stat().st_size
            write_csv(pd.DataFrame({"rate": ["45.6"]}), path, index=False)
            self.assertEqual(size, path.stat().st_size)
            self.assertIn("45.6", path.read_text(encoding="utf-8-sig"))

    def test_output_matches_preserved_original(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY) as temporary:
            root = Path(temporary); raw = root / "raw"; raw.mkdir()
            make_raw(raw)
            old = root / "old"; new = root / "new"
            for path in [old, new]:
                (path / "prefecture").mkdir(parents=True)
                (path / "municipality").mkdir()
            terms = ROOT / "source/facilities_depreciation_terms.json"
            (old / terms.name).write_bytes(terms.read_bytes())
            reference = (ROOT / "tests/original_generator.py.txt").read_text(encoding="utf-8")
            start = reference.index("IS_WINDOWS =")
            end = reference.index("\nPUBLISH_DIR =", start)
            reference = reference[:start] + f"ROOT = Path({str(old)!r})\nRAW_DIR = Path({str(raw)!r})\n" + reference[end:]
            original = root / "original.py"; original.write_text(reference, encoding="utf-8")
            subprocess.run([sys.executable, str(original)], check=True, capture_output=True)
            prepare_input(raw, root / "input.csv.gz")
            result = build(root / "input.csv.gz", new, terms)
            expected = sorted(p.relative_to(old).as_posix() for p in old.rglob("*.csv"))
            self.assertEqual(result["files"], expected)
            for relative in expected:
                with (old / relative).open(encoding="utf-8-sig", newline="") as left, (new / relative).open(encoding="utf-8-sig", newline="") as right:
                    self.assertEqual(list(csv.reader(left)), list(csv.reader(right)), relative)
                self.assertTrue((new / relative).read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_missing_columns_remain_an_error(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY) as temporary:
            root = Path(temporary)
            (root / "010006.csv").write_text("wrong,columns\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "必要な列"):
                prepare_input(root, root / "input.csv.gz")
            self.assertFalse((root / "input.csv.gz").exists())


if __name__ == "__main__":
    unittest.main()
