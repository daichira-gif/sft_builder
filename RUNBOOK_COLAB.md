# Colab Runbook (Structured SFT Builder, Strategy‑aligned)

本手順書は、Colab 上で「構造化出力」SFT データ合成を行うための操作ガイドです。本パッケージの方針（to‑XML 強化、CSV‑in 抽出、Text→TOML/→YAML/→XML、スキーマ指向の生成）に沿った実行・検証・反復の方法をまとめています。

---

## 1. 依存関係のインストール
- Colab（Python 3.10/3.11 想定）で、ネットワーク利用が可能であることが前提です。
```bash
!pip install -q -U datasets pandas pyarrow lxml orjson pyyaml transformers tomli huggingface_hub
```

---

## 2. リポジトリの配置と設定
- 本リポジトリを `/content` に置き、Python のパスに `/content` を追加します。
```python
import sys
sys.path.append('/content')  # 例: /content/sft_builder ディレクトリ直下を参照
```

---

## 3. 環境変数セット（推奨例）
- 本パッケージの方針に沿った初期配分例です。まずは少量で試走し、AUTO‑BUDGET 提案・検証結果を見ながら段階的に増やしてください。
```python
import os
# 出力先
os.environ['SFT_OUT_DIR'] = '/content/structured_sft_outputs'

# 比率: タブラー内で JSON→CSV を増やして CSV 側の汎化を強化
os.environ['SFT_TABULAR_JSON_TO_CSV_PROB'] = '0.65'

# XML 出力の入力ソース配分（合計は自動正規化）
os.environ['SFT_XML_OUT_PROB_JSON'] = '0.35'
os.environ['SFT_XML_OUT_PROB_YAML'] = '0.20'
os.environ['SFT_XML_OUT_PROB_CSV']  = '0.20'
os.environ['SFT_XML_OUT_PROB_TEXT'] = '0.25'

# TOML 出力のモード配分
os.environ['SFT_TOML_OUT_PROB_JSON']      = '0.40'
os.environ['SFT_TOML_OUT_PROB_YAML']      = '0.25'
os.environ['SFT_TOML_OUT_PROB_TEXT']      = '0.25'
os.environ['SFT_TOML_OUT_PROB_TOML2JSON'] = '0.10'

# YAML 出力（ミニマル）の入力ソース配分
os.environ['SFT_YAML_OUT_PROB_XML']  = '0.45'
os.environ['SFT_YAML_OUT_PROB_CSV']  = '0.35'
os.environ['SFT_YAML_OUT_PROB_TEXT'] = '0.15'
os.environ['SFT_YAML_OUT_PROB_JSON'] = '0.05'

# AUTO-BUDGET 提案時の XML/TOML へのフォーカス重み
os.environ['SFT_FOCUS_XML']  = '3.5'  # to‑XML を重点
os.environ['SFT_FOCUS_TOML'] = '3.0'  # TOML も重点

# 主要 BUDGET（例: 小規模試走値）
os.environ['SFT_BUDGET_TABULAR']   = '500'
os.environ['SFT_BUDGET_XML_IN']    = '200'
os.environ['SFT_BUDGET_XML_OUT']   = '600'
os.environ['SFT_BUDGET_TOML_OUT']  = '300'
os.environ['SFT_BUDGET_YAML_OUT']  = '150'
os.environ['SFT_BUDGET_GTFS']      = '200'
os.environ['SFT_BUDGET_HARD_MIXED']= '200'

# スキーマ指向（TEXT+SPEC）パックの BUDGET（生成を強化）
os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA']         = '600'
os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA_NESTED']  = '600'
os.environ['SFT_BUDGET_TEXT_YAML_SCHEMA']         = '300'
os.environ['SFT_BUDGET_TEXT_TOML_SCHEMA']         = '300'

# カリキュラム（Phase 2 既定、必要に応じて 1→3 と上げる）
os.environ['SFT_CURRICULUM_PHASE'] = '2'

# 多様化（既定 ON、抽出系は自動で空値を防止）
os.environ['SFT_DIVERSIFY_ENABLE']       = '1'
os.environ['SFT_DIVERSIFY_ROW_TRIM']     = '1'
os.environ['SFT_DIVERSIFY_HARD_MIXED']   = '1'
```

---

## 4. 実行
- 20260104 の戦略反映ランナーで実行します（P0 ガード有効、ストリーミング読み込み）。
```python
from sft_builder.20260104 import colab_runner
colab_runner.main()
```
- 実行ログには、出力件数、出力フォーマット分布、AUTO‑BUDGET 提案、デバッグログの状況（XML/TOML 失敗、P0 reject）が表示されます。

---

## 5. 検証（構文・品質・仕様準拠）
```python
# 構文・形式検証（XML/TOML/YAML/CSV）
from sft_builder import validate_outputs as vout
from sft_builder import validate_quality as vq

!python -m sft_builder.validate_outputs
!python -m sft_builder.validate_quality
```
- スキーマ系（TEXT+SPEC）は、生成直後に以下の仕様準拠バリデータでフィルタされます（builders に統合済み）:
  - JSON flat: キー集合・型一致
  - JSON nested: `{'id','meta','tags'}`、`meta` のキー集合・型一致、`tags` は文字列配列
  - YAML flat: トップレベル配列、各要素のキー集合・型一致
  - TOML: トップレベル `[[items]]`、各テーブルのキー集合・型一致
- 期待: `Duplicate=0`、`Attribute/Round-trip issues=0`、デバッグログ最小化（XML/TOML 失敗、P0 reject）

---

## 6. 反復・再配分（AUTO‑BUDGET とチューニング）
- 生成分布が目標と乖離する場合、以下を調整して再実行します。
  - `SFT_TABULAR_JSON_TO_CSV_PROB`（CSV回答の比率）
  - `SFT_XML_OUT_PROB_*` / `SFT_TOML_OUT_PROB_*` / `SFT_YAML_OUT_PROB_*`（内部モード配分）
  - `SFT_FOCUS_XML/TOML`（AUTO‑BUDGET提案の重み）
  - `SFT_BUDGET_*`（主要パックの生成件数）
  - スキーマ系強化: `SFT_BUDGET_TEXT_*` 系（生成タスクを増やす）

- **カリキュラム調整**:
  - `SFT_CURRICULUM_PHASE` を `1`（保守的）から `3`（難易度高）の範囲で調整し、徐々に強度を上げることが可能です。

---

## 7. 注意事項（品質ゲートと運用）
- Tokenizer: 既定 `unsloth/Qwen3-4B-Instruct-2507`。変更は `SFT_TOKENIZER_MODEL` で指定。
- 品質ゲート: P0 境界チェック、構文検証（XML/TOML/YAML/CSV）、往復検証、仕様準拠（スキーマ系）を内蔵。ログは `SFT_OUT_DIR/_debug/` に保存。
- 出力: 生成結果は OpenAI messages 形式 JSONL（`messages: [{role, content}, ...]`）。
- Push to Hub: `huggingface_hub` のトークンは Colab Secrets 等で安全に管理。
- 公開時はデータソース・ライセンス・生成ポリシー（リーク回避）を Dataset Card に明記。

---

## 付録: 戦略整合の BUDGET プリセット例
strategy.md の配分目安（to‑XML 40–45%、CSV‑in 抽出 20%、Text→TOML 10%、維持 10–15%）に近づけるための環境変数セット例です。実行後のレポートと AUTO‑BUDGET 提案を確認し、誤差を詰めてください。

1) パイロット（小規模）例（総量 ≈ 4,000）
```python
import os
# Tabular（CSV↔JSON）。CSV‑in 抽出寄りにするため 0.35 に設定（CSV→JSON を相対的に増やす）
os.environ['SFT_BUDGET_TABULAR'] = '700'   # ≈ 17.5%
os.environ['SFT_TABULAR_JSON_TO_CSV_PROB'] = '0.35'

# XML 入出力
os.environ['SFT_BUDGET_XML_IN']  = '350'   # ≈ 8.75%（維持）
os.environ['SFT_BUDGET_XML_OUT'] = '1700'  # ≈ 42.5%（to‑XML 重点）

# TOML / YAML 出力（維持 + Text→TOML 強化）
os.environ['SFT_BUDGET_TOML_OUT'] = '350'  # ≈ 8.75%（維持）
os.environ['SFT_BUDGET_YAML_OUT'] = '150'  # ≈ 3.75%（維持）

# Text→JSON（GTFS）、制約フィルタ（hard_mixed）
os.environ['SFT_BUDGET_GTFS']       = '250'  # ≈ 6.25%（維持）
os.environ['SFT_BUDGET_HARD_MIXED'] = '150'  # ≈ 3.75%（維持）

# TEXT+SPEC（スキーマ生成）
os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA']         = '450'  # ≈ 11.25%
os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA_NESTED']  = '450'  # ≈ 11.25%
os.environ['SFT_BUDGET_TEXT_YAML_SCHEMA']         = '200'  # ≈ 5.0%
os.environ['SFT_BUDGET_TEXT_TOML_SCHEMA']         = '250'  # ≈ 6.25%（Text→TOML を 10% 近辺まで引き上げ）

# to‑XML フォーカス
os.environ['SFT_FOCUS_XML']  = '3.5'
os.environ['SFT_FOCUS_TOML'] = '3.0'
```

2) 中規模（総量 ≈ 20,000）例
```python
import os
os.environ['SFT_BUDGET_TABULAR'] = '3500'          # ≈ 17.5%（CSV‑in 寄せ: prob=0.35）
os.environ['SFT_TABULAR_JSON_TO_CSV_PROB'] = '0.35'

os.environ['SFT_BUDGET_XML_IN']  = '1800'          # ≈ 9.0%
os.environ['SFT_BUDGET_XML_OUT'] = '8500'          # ≈ 42.5%

os.environ['SFT_BUDGET_TOML_OUT'] = '1800'         # ≈ 9.0%
os.environ['SFT_BUDGET_YAML_OUT'] = '800'          # ≈ 4.0%

os.environ['SFT_BUDGET_GTFS']       = '1200'       # ≈ 6.0%
os.environ['SFT_BUDGET_HARD_MIXED'] = '700'        # ≈ 3.5%

os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA']         = '2100'  # ≈ 10.5%
os.environ['SFT_BUDGET_TEXT_JSON_SCHEMA_NESTED']  = '2100'  # ≈ 10.5%
os.environ['SFT_BUDGET_TEXT_YAML_SCHEMA']         = '1000'  # ≈ 5.0%
os.environ['SFT_BUDGET_TEXT_TOML_SCHEMA']         = '1500'  # ≈ 7.5%（Text→TOML を 10% 近辺へ）

os.environ['SFT_FOCUS_XML']  = '3.5'
os.environ['SFT_FOCUS_TOML'] = '3.0'
```

メモ:
- Tabular は内部で JSON→CSV と CSV→JSON が分岐します。CSV‑in 抽出を増やすには `SFT_TABULAR_JSON_TO_CSV_PROB` を 0.3–0.4 程度に下げてください。
- YAML 側の CSV‑in を増やしたい場合は、`SFT_YAML_OUT_PROB_CSV` を上げる調整も有効です。
- 実際のフォーマット分布は入力テキストの多様性やサイジングにも依存するため、必ず実行後のレポートと AUTO‑BUDGET 提案を確認し、誤差を詰めてください。
