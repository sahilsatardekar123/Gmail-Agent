from __future__ import annotations

"""
Utility script to download a local Qwen chat model into the `models/` folder.

Usage (from project root, with venv activated):

    python download_qwen.py
"""

from huggingface_hub import snapshot_download


def main() -> None:
    # Hugging Face model repo ID
    repo_id = "Qwen/Qwen2.5-1.5B-Instruct"

    # Local path where the model will be stored
    local_dir = "models/qwen2.5-1.5b-instruct"

    print(f"Downloading '{repo_id}' to '{local_dir}'...")
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # better for Windows
    )
    print("Download complete.")
    print(f"Model saved at: {local_dir}")


if __name__ == "__main__":
    main()

