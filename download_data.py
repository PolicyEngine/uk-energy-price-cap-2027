"""Fetch Microcosm UK build fcfac709, the dataset policyengine 6.20.2 certifies.

The file is in a private Hugging Face dataset; the download reads the token
from HUGGING_FACE_TOKEN (or HF_TOKEN). run_cap.py checks its SHA-256.
"""

import os
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download

PATH = (
    "releases/microcosm-uk-2024-25-national/"
    "uk-frs-calibration-attempt-20261115T104657Z-fcfac709/microcosm_uk_2024_25.h5"
)
REVISION = "ad84c0602ed28f694ef52662eb9b063779e4e923"

token = os.environ.get("HUGGING_FACE_TOKEN") or os.environ.get("HF_TOKEN")
source = hf_hub_download(
    "policyengine/populace-uk-private",
    PATH,
    repo_type="dataset",
    revision=REVISION,
    token=token,
)
dest = Path("data") / PATH
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, dest)
print(dest)
