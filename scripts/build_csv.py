"""保管した指標行から、従来と同じ公開CSVを生成する。VPSには接続しない。"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAIN_COLUMNS = ["is_prefecture", "団体コード", "団体名", "都道府県", "指標", "Year", "value", "facility_id", "facility_en"]


def write_csv(frame: pd.DataFrame, path: Path, *, index: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=index, encoding="utf-8-sig", lineterminator="\n")
    # 同じサイズでも値が違えば更新する。内容が同じ場合だけ一時ファイルを捨てる。
    if path.exists() and filecmp.cmp(path, temporary, shallow=False):
        temporary.unlink()
    else:
        os.replace(temporary, path)


def build(input_file: Path, output_dir: Path, terms_file: Path) -> dict:
    terms = json.loads(terms_file.read_text(encoding="utf-8"))
    facilities = {row["jp"]: row for row in terms["depreciation_rates"]["facilities"]}
    source = pd.read_csv(input_file, dtype=str)
    years = [column for column in source.columns if re.fullmatch(r"\d{4}", column)]
    if source.empty or not years:
        raise ValueError("入力の指標行または年度がありません")
    source.loc[source["指標"] == "有形固定資産減価償却率", "指標"] = "有形固定資産減価償却率【全施設】"
    source["is_prefecture"] = source["団体コード"].str.fullmatch(r"\d{2}000\d", na=False)
    identifiers = ["is_prefecture", "団体コード", "団体名", "都道府県", "指標"]
    frames = []
    # 原型と同じく団体、年度、指標の順に縦持ちデータを作る。
    for _code, organization in source.groupby("団体コード", sort=True):
        frame = organization.melt(id_vars=identifiers, value_vars=years, var_name="Year", value_name="value")
        names = frame["指標"].str.extract(r"【(.+?)】")[0]
        frame["facility_id"] = names.map({name: item["id"] for name, item in facilities.items()})
        frame["facility_en"] = names.map({name: item["en"] for name, item in facilities.items()})
        frames.append(frame)
    long_data = pd.concat(frames, ignore_index=True)[MAIN_COLUMNS]
    outputs = ["facilities_depreciation.csv"]
    write_csv(long_data, output_dir / outputs[0], index=False)
    organizations = long_data[["団体コード", "is_prefecture", "団体名", "都道府県"]].drop_duplicates().sort_values("団体コード")
    for is_prefecture, prefix in [(True, "prefecture"), (False, "municipality")]:
        data = long_data[long_data["is_prefecture"] == is_prefecture]
        master = organizations[organizations["is_prefecture"] == is_prefecture]
        for facility_id, group in data.groupby("facility_id"):
            filename = f"{prefix}_{facility_id}.csv"
            relative = filename if facility_id == "overall" else f"{prefix}/{filename}"
            values = group.pivot_table(index="団体コード", columns="Year", values="value", aggfunc="first")
            values.columns = [f"{int(year) + 1}-03-31" for year in values.columns]
            output = master.set_index("団体コード")[["団体名"]].join(values.reindex(index=master["団体コード"]))
            write_csv(output, output_dir / relative, index=True)
            outputs.append(relative)
    return {"input_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(), "organizations": len(organizations),
            "indicator_rows": len(source), "long_rows": len(long_data), "files": sorted(outputs)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "source/facilities.csv.gz")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--terms", type=Path, default=ROOT / "source/facilities_depreciation_terms.json")
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    record = build(args.input, args.output_dir, args.terms)
    if args.record:
        record["checked_at"] = datetime.now(timezone.utc).isoformat()
        args.record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
