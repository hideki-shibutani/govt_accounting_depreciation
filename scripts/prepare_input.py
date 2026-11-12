"""元CSVから、公開済みの減価償却指標に必要な行だけを取り出す。"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
from pathlib import Path

ENGLISH = {
    "organization_code": "団体コード", "organization_name": "団体名",
    "prefecture_name": "都道府県", "table_name": "表", "target_name": "対象", "item_name": "指標",
}
METADATA = ["団体コード", "団体名", "都道府県", "指標"]
TABLES = ("公会計指標分析・財政指標組合せ分析表", "施設類型別ストック情報分析表")


def year_column_aliases(columns: list[str], file: Path) -> dict[str, str]:
    """整数年度と旧CSVの浮動小数表記を入口で同じ年度へそろえる。"""
    aliases = {}
    seen_years = set()
    for column in columns:
        match = re.fullmatch(r"(\d{4})(?:\.0+)?", column)
        if not match:
            if re.match(r"\d{4}\.", column):
                raise ValueError(f"年度列の形式が不正です: {file.name}: {column}")
            continue
        year = match.group(1)
        if year in seen_years:
            raise ValueError(f"同じ年度の列が重複しています: {file.name}: {year}")
        seen_years.add(year)
        aliases[column] = year
    return aliases


def prepare_input(raw_dir: Path, output: Path) -> dict:
    files = sorted(p for p in raw_dir.glob("*.csv") if re.fullmatch(r"\d{6}\.csv", p.name))
    if not files:
        raise ValueError("入力の6桁団体コードCSVがありません")
    selected = []
    years = set()
    for file in files:
        with file.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames or []
            # 形式の差は入口だけで整理する。後段の抽出規則は共通。
            if set(ENGLISH).issubset(columns):
                aliases = ENGLISH
            elif set(ENGLISH.values()).issubset(columns):
                aliases = {}
            else:
                raise ValueError(f"必要な列がありません: {file.name}")
            year_aliases = year_column_aliases(columns, file)
            aliases = {**aliases, **year_aliases}
            years.update(year_aliases.values())
            for row in reader:
                row = {aliases.get(name, name): value for name, value in row.items()}
                if (row["表"].startswith(TABLES) and row["対象"] == "当該団体値"
                        and row["指標"].endswith("有形固定資産減価償却率")):
                    if not year_aliases:
                        raise ValueError(f"指標行に年度列がありません: {file.name}")
                    selected.append(row)
    if not selected or not years:
        raise ValueError("公開対象の減価償却指標または年度がありません")
    fields = METADATA + sorted(years)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(selected)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(gzip.compress(text.getvalue().encode("utf-8"), mtime=0))
    return {"source_files": len(files), "indicator_rows": len(selected), "years": sorted(years), "bytes": output.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("source/facilities.csv.gz"))
    args = parser.parse_args()
    print(prepare_input(args.raw_dir, args.output))
