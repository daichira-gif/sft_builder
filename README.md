# 構造化SFTデータ合成・検証パッケージ

## 概要

本リポジトリは構造化出力SFTのための合成・検証をColabで再現するための最小一式を提供します。

## ライセンス (License)

### スクリプトのライセンス

このリポジトリに含まれるスクリプトおよびコードは、**Apache License 2.0** の下で提供されます。詳細については、`LICENSE` ファイルをご覧ください。

### 生成されるデータセットのライセンスに関する重要な注意

**本スクリプトを使用して生成されたデータセット（`*.jsonl` ファイルなど）は、Apache License 2.0 の対象外です。**

生成されるデータセットの内容は、以下の公開データセットから派生したものが含まれる可能性があります。

-   **OpenFoodFacts**
-   **Shopify's public dataset on Kaggle**
-   **GTFS (General Transit Feed Specification) data**

これらのデータセットを利用するユーザーは、**それぞれの元のデータセットのライセンス条項を自身で確認し、それを遵守する責任があります。** 例えば、OpenFoodFactsはOpen Database License (ODbL)を採用しています。生成されたデータセットを配布、公開、または商業利用する際には、必ずオリジナルのライセンス条件に従ってください。

---

## フォルダ構成

- `sft_builder`: 合成・検証パッケージ（`python -m` 実行）

## 必要ライブラリ

- `datasets`
- `pandas`
- `pyarrow`
- `lxml`
- `orjson`
- `pyyaml`
- `transformers`
- `huggingface_hub`

```bash
pip install -U datasets pandas pyarrow lxml orjson pyyaml transformers huggingface_hub
```

## Colab実行手順

### 1. リポジトリのクローンとパスの設定

```python
!git clone https://github.com/daichira-gif/sft_builder.git /content/sft_builder
import sys
sys.path.append('/content/sft_builder')
```

### 2. データセットの合成（環境変数設定例）

```python
import os

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

# 合成実行
!python -m sft_builder.colab_runner
```

### 3. 生成データの検証

```python
# 形式検証
!python -m sft_builder.validate_outputs

# 品質検証
!python -m sft_builder.validate_quality
```

### 4. データセットのHugging Face Hubへのアップロード

```python
from datasets import load_dataset, DatasetDict
from huggingface_hub import login
import glob
import os

# Hugging Face Hubにログイン（ColabのSecretsを使うことを推奨）
# from google.colab import userdata
# token = userdata.get('HF_TOKEN')
# login(token=token)
login()


# 生成されたJSONLファイルをロード
# 必要に応じてファイルパスを調整してください
out_dir = os.environ.get('SFT_OUT_DIR', '/content/structured_sft_outputs')
jsonl_files = glob.glob(os.path.join(out_dir, '*.jsonl'))

if not jsonl_files:
    print("エラー: 生成されたJSONLファイルが見つかりません。")
else:
    dataset = load_dataset('json', data_files=jsonl_files, split='train')

    # (任意) train/testに分割
    # train_test_split = dataset.train_test_split(test_size=0.1)
    # dataset_dict = DatasetDict({
    #     'train': train_test_split['train'],
    #     'test': train_test_split['test']
    # })

    # Hubへプッシュ
    # 'your-username/your-dataset-name' を実際のHugging Faceのユーザー名とデータセット名に置き換えてください
    repo_name = "your-username/your-dataset-name"
    dataset.push_to_hub(repo_name)
    # dataset_dict.push_to_hub(repo_name)

    print(f"データセットが https://huggingface.co/datasets/{repo_name} にアップロードされました。")

```
**注意:** アップロードするデータセットのDataset Cardには、データソース（OpenFoodFacts/Shopify/GTFS）への準拠とライセンスに関する注意書きを必ず記載してください。