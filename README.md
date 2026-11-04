![Update Status](https://img.shields.io/badge/Data%20Update-Yearly-blue)
![License](https://img.shields.io/badge/License-MIT-green)

# 公共施設の老朽化データ：Japan Public Facilities Depreciation Data
　このリポジトリは、都道府県・市区町村が公表する「施設類型別ストック情報分析表」を用いて、施設別に、有形固定資産減価償却率を自動抽出して公開するものです。有形固定資産減価償却率は、以下の数式に基づいています。

$$
\text{有形固定資産減価償却率 (\\%)} = \frac{\text{減価償却累計額}}{\text{有形固定資産の取得価額}} \times 100
$$

　有形固定資産減価償却率は、公共施設が耐用年数に対してどの程度経過しているか（老朽化の度合い）を会計のルールにしたがって把握するための指標です。公共施設が新設された時に０％であり、耐用年数を迎えると１００％となります。統一的な基準による地方公会計にしたがい、平成２８（２０１６）年度に「財政状況資料集」の収録指標の一つとしてはじめて算出され、その後も継続して公表されています。

## 公開データについて
- **ファイル形式**: CSV (UTF-8 with BOM)
- **更新確認**: GitHub Actionsで毎月1日12:17 JSTに実行。Actions画面から手動実行も可能です。原資料の改訂頻度とは別です。
- **命名規則**: 
  - `prefecture_*.csv`: 都道府県データ
  - `municipality_*.csv`: 市区町村データ

## 収録項目
- 団体コード / 団体名
- 施設名（facility_id）
- 各年度の有形固定資産減価償却率（3月31日時点）

## 誤報告・欠損データ（misreporting / missing-data）
　稀に、数値が誤って報告されることがあり、報告者がそれを分析欄で訂正することもありますが、本リポジトリは訂正前の公表値をそのまま収録しています。それ以外にも、計算・集計作業の遅れや、公表時のリンクミスなどによって、欠損値が生じることがあります。また、固定資産台帳の整備状況によって、数値が大きく改められることもあります。

## データの生成元
　このデータは、[地方財政ダッシュボード](https://shibutani.org) のデータベースを基に自動的に生成されています。

### 更新手順

旧VPSでの週次更新を終了し、GitHub Actionsへ移行しました。既存のCSV名・URL・UTF-8 BOM形式を維持します。

元CSVを更新したときは、このリポジトリを取得したローカル環境で、公開対象の指標行だけを抽出します。

```powershell
python scripts/prepare_input.py --raw-dir C:/xampp/htdocs/shibutani.org/data
```

生成した `source/facilities.csv.gz` をこのリポジトリへ反映してください。GitHubのファイルアップロード画面も利用できます。
この入力には、既に公開している減価償却率の団体情報・指標・年度値だけを含みます。元CSV全体はアップロードしません。
入力を差し替えると自動で生成されます。月次・手動実行も、この保管済み入力を使います。

Actionsの **Update depreciation data → Run workflow** で手動実行できます。追加のAPIトークンやVPSへの接続は不要です。
テスト・生成が成功した場合だけ、CSVと `build-record.json` をコミットします。記録には入力ハッシュ・団体数・生成ファイル・確認時刻を残します。
データが同じ月も確認記録を更新し、月次処理の結果を確認できるようにしています。失敗はActionsのエラーとして表示し、自動再試行は行いません。

ローカル確認は次のコマンドです。

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build_csv.py
```

`scripts/prepare_input.py` は英語列名と従来の日本語列名に対応します。
`scripts/build_csv.py` は元の集計・出力形式を引き継ぎ、同じファイルサイズでも内容が変わった場合は更新します。
元コードは `tests/original_generator.py.txt` に保管し、代表例の出力をテストで比較しています。

## 原典資料
　各都道府県・市区町村が公表する「財政状況資料集」を独自に解析したものです。

## 参考文献
- **澁谷英樹**, 「地方公会計に基づいた公共施設老朽化の現状：施設類型別ストック情報分析表を用いた分析」, 『アカデミア．社会科学編』, 22号, pp. 91-101, 2022年, [https://doi.org/10.15119/00003854](https://doi.org/10.15119/00003854).
- **奥村桃子**・**大竹春菜**・**田中美紅**・**大野世莉**・**上野真美**「社会資本老朽化の地域格差」, 第1回　今後の社会資本のあり方に関する懸賞論文　学生部門佳作, 2023年, [https://www.jice.or.jp/cms/labs/pdf/2022-infra-kensho-student-honorable-mention.pdf](https://www.jice.or.jp/cms/labs/pdf/2022-infra-kensho-student-honorable-mention.pdf).


