# ==============================================================================
# 構造化SFTデータ合成・検証 on Colab
# ==============================================================================
#
# このスクリプトは、Google Colab上でsft_builderリポジトリを実行し、
# 構造化データセットを合成、検証、そしてHugging Face Hubにアップロードするための
# 完全なコードです。
# 各セル（`# %%`で区切られたブロック）を上から順番に実行してください。

# %%
# ==============================================================================
# ステップ 1: セットアップ (リポジトリのクローンと依存関係のインストール)
# ==============================================================================

import os
import sys
import pathlib

print("🔩 ステップ 1: セットアップを開始します...")

# リポジトリをクローン（Colab 標準）
print("GitHub リポジトリをクローンします...")
!rm -rf /content/sft_builder
!git clone -q https://github.com/daichira-gif/sft_builder.git /content/sft_builder

# Python パスを追加
if '/content' not in sys.path:
    sys.path.insert(0, '/content')
print("sys.path 追加: /content (sft_builder をパッケージとして解決)")

# 依存関係をインストール
!pip install -q -U datasets pandas pyarrow lxml orjson pyyaml transformers huggingface_hub tomli

print("\n✅ セットアップが完了しました。")


# %%
# ==============================================================================
# ステップ 2: 環境変数の設定
# ==============================================================================
# データ生成の挙動を制御するための環境変数を設定します。
# これらの値は 'RUNBOOK_COLAB.md' に記載されている推奨値です。

print("\n⚙️ ステップ 2: 環境変数を設定します...")

# 出力先ディレクトリ
os.environ['SFT_OUT_DIR'] = '/content/structured_sft_outputs'

# 各種確率・設定値
os.environ['SFT_TABULAR_JSON_TO_CSV_PROB'] = '0.65'
os.environ['SFT_XML_OUT_PROB_JSON'] = '0.35'
os.environ['SFT_XML_OUT_PROB_YAML'] = '0.20'
os.environ['SFT_XML_OUT_PROB_CSV']  = '0.20'
os.environ['SFT_XML_OUT_PROB_TEXT'] = '0.25'
os.environ['SFT_TOML_OUT_PROB_JSON']      = '0.40'
os.environ['SFT_TOML_OUT_PROB_YAML']      = '0.25'
os.environ['SFT_TOML_OUT_PROB_TEXT']      = '0.25'
os.environ['SFT_TOML_OUT_PROB_TOML2JSON'] = '0.10'
os.environ['SFT_YAML_OUT_PROB_XML']  = '0.45'
os.environ['SFT_YAML_OUT_PROB_CSV']  = '0.35'
os.environ['SFT_YAML_OUT_PROB_TEXT'] = '0.15'
os.environ['SFT_YAML_OUT_PROB_JSON'] = '0.05'
os.environ['SFT_FOCUS_XML'] = '3.5'
os.environ['SFT_FOCUS_TOML'] = '3.0'
os.environ['SFT_BUDGET_XML_OUT'] = '4500'
os.environ['SFT_CURRICULUM_PHASE'] = '2'
os.environ['SFT_DIVERSIFY_ENABLE']       = '1'
os.environ['SFT_DIVERSIFY_ROW_TRIM']     = '1'
os.environ['SFT_DIVERSIFY_HARD_MIXED']   = '1'

print("✅ 環境変数の設定が完了しました。")
print(f"   - 出力ディレクトリ: {os.environ['SFT_OUT_DIR']}")


# %%
# ==============================================================================
# ステップ 3: データセットの合成
# ==============================================================================
# 設定した環境変数に基づき、データ合成処理を実行します。
# 完了までには数分かかる場合があります。

print("\n⏳ ステップ 3: データセットの合成を開始します...")

!python -m sft_builder.colab_runner

print("\n✅ データセットの合成が完了しました。")


# %%
# ==============================================================================
# ステップ 4: 生成データの検証
# ==============================================================================
# 生成されたデータセットの形式と品質を検証します。

print("\n🔍 ステップ 4: 生成データの検証を開始します...")

print("\n--- 形式検証 (validate_outputs) ---")
!python -m sft_builder.validate_outputs

print("\n--- 品質検証 (validate_quality) ---")
!python -m sft_builder.validate_quality

print("\n✅ 生成データの検証が完了しました。")


# %%
# ==============================================================================
# ステップ 5: Hugging Face Hub へのアップロード
# ==============================================================================
# 生成・検証済みのデータセットをHugging Face Hubにアップロードします。
# このセルを実行すると、Hugging Faceのアクセストークンの入力を求められます。
# https://huggingface.co/settings/tokens から 'write' 権限を持つトークンを
# 取得してください。

from datasets import load_dataset
from huggingface_hub import login
import glob

print("\n🚀 ステップ 5: Hugging Face Hub へのアップロードを開始します...")

# --------------------------------------------------------------------------
# Hugging Face Hubにログイン
# ColabのSecrets機能を使うとより安全です:
# from google.colab import userdata
# token = userdata.get('HF_TOKEN') # 'HF_TOKEN'という名前でSecretを保存
# login(token=token)
# --------------------------------------------------------------------------
login()


# 生成されたJSONLファイルをロード
out_dir = os.environ.get('SFT_OUT_DIR', '/content/structured_sft_outputs')
jsonl_files = glob.glob(os.path.join(out_dir, '*.jsonl'))

if not jsonl_files:
    print(f"\n❌ エラー: ディレクトリ '{out_dir}' にアップロード対象のJSONLファイルが見つかりません。")
else:
    print(f"\n📂 以下のファイルをロードします: {jsonl_files}")
    dataset = load_dataset('json', data_files=jsonl_files, split='train')

    # --------------------------------------------------------------------------
    # !!! 注意 !!!
    # ↓↓↓ 下の 'your-username/your-dataset-name' を書き換えてください ↓↓↓
    repo_name = "your-username/your-dataset-name"
    # ↑↑↑ あなたのHugging Faceユーザー名と、希望するデータセット名にしてください ↑↑↑
    # --------------------------------------------------------------------------

    if repo_name == "your-username/your-dataset-name":
        print("\n⚠️  注意: `repo_name` をあなたのHugging Faceリポジトリ名に変更してください。アップロードをスキップします。")
    else:
        print(f"\n🚀 データセットを '{repo_name}' としてHugging Face Hubにアップロードします...")
        try:
            dataset.push_to_hub(repo_name)
            print(f"\n✅ データセットが https://huggingface.co/datasets/{repo_name} に正常にアップロードされました。")
            print("\n[重要] アップロードしたデータセットのDataset Card（データセットの説明ページ）を編集し、")
            print("データソース（OpenFoodFacts, Shopify, GTFS）への言及と、それらのライセンスを遵守する必要がある旨を明記してください。")
        except Exception as e:
            print(f"\n❌ アップロード中にエラーが発生しました: {e}")

# 作業用ディレクトリをクリーンアップ
!rm -rf tmp_colab_check

print("\n🎉 全ての処理が完了しました。")
