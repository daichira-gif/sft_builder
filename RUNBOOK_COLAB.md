# Colab Runbook (SFT Data Generation)

本手順書は、Colab 上で本パッケージを実行して SFT 用データを合成・検証するための手順をまとめたものです。

---

## 1. 依存関係のインストール
- Colab で Python 実行・ネットワーク利用が可能であることが前提です。
```bash
!pip install -q -U datasets pandas pyarrow lxml orjson pyyaml transformers huggingface_hub
```

---

## 2. リポジトリの配置と設定
- リポジトリを `/content/sft_builder` にクローンし、Python のパスに追加します。
```python
!git clone https://github.com/daichira-gif/sft_builder.git /content/sft_builder
import sys
sys.path.append('/content/sft_builder')
```

---

## 3. 環境変数セット（推奨例）
- データ生成比率の初期案です。
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
os.environ['SFT_FOCUS_XML']  = '3.5'
os.environ['SFT_FOCUS_TOML'] = '3.0'

# BUDGET: XML_OUT を厚めに（必要に応じて調整）
os.environ['SFT_BUDGET_XML_OUT'] = '4500'

# カリキュラム（Phase 2 を既定として本番実行）
os.environ['SFT_CURRICULUM_PHASE'] = '2'

# 多様化（既定 ON、抽出系は自動で空値を防止）
os.environ['SFT_DIVERSIFY_ENABLE']       = '1'
os.environ['SFT_DIVERSIFY_ROW_TRIM']     = '1'
os.environ['SFT_DIVERSIFY_HARD_MIXED']   = '1'
```

---

## 4. 実行
```python
# データ合成の実行
!python -m sft_builder.colab_runner
```
- 実行ログに出力ファイルの件数、フォーマット分布、デバッグログの有無（XML/TOML 失敗、P0 reject）が表示されます。

---

## 5. 検証
```python
# 構文・形式検証
!python -m sft_builder.validate_outputs

# 品質検証（往復・属性一貫・重複・分布サマリ）
!python -m sft_builder.validate_quality
```
- **期待**: `Duplicate=0`, `Attribute/Round-trip issues=0` を基本とし、レポートされる分布に多様性が確認できること。

---

## 6.反復・再配分
- 生成されるフォーマット分布が目標と乖離する場合、以下の環境変数を微調整して再実行・検証します。
  - `SFT_TABULAR_JSON_TO_CSV_PROB`（CSV回答の比率）
  - `SFT_XML_OUT_PROB_*` / `SFT_TOML_OUT_PROB_*` / `SFT_YAML_OUT_PROB_*`（内部モード配分）
  - `SFT_FOCUS_XML/TOML`（AUTO‑BUDGET提案の重み）
  - `SFT_BUDGET_*`（主要パックの生成件数）

- **カリキュラム調整**:
  - `SFT_CURRICULUM_PHASE` を `1`（保守的）から `3`（難易度高）の範囲で調整し、徐々に強度を上げることが可能です。

---

## 7. 注意事項
- **Tokenizer**: 既定では `unsloth/Qwen3-4B-Instruct-2507` を使用します。変更する場合は `SFT_TOKENIZER_MODEL` 環境変数を設定してください。
- **品質ゲート**: P0境界チェック、構文検証、往復検証は常に有効です。エラーやリジェクトが増えすぎないよう、設定は段階的に調整してください。
- **出力**: 生成結果は OpenAI messages 形式の JSONL ファイルとして `SFT_OUT_DIR` で指定したディレクトリに保存されます。
- **Hugging Face Token**: データセットを `push_to_hub` するには、Write権限を持つトークンが必要です。ColabのSecrets機能で安全に管理することを推奨します。
- **Dataset Card**: データセットを公開する際は、データソースやライセンスに関する注意を記載してください。
