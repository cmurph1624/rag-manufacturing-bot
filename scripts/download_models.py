import os
import sys
from huggingface_hub import snapshot_download

def download_model(repo_id):
    print(f"Attempting to download {repo_id}...")
    try:
        path = snapshot_download(repo_id=repo_id)
        print(f"Successfully downloaded {repo_id} to {path}")
        return True
    except Exception as e:
        print(f"Failed to download {repo_id}: {e}")
        return False

if __name__ == "__main__":
    # The model used in src/retrieval/rerank.py
    model_id = "BAAI/bge-reranker-base"
    
    if download_model(model_id):
        print("\nModel download successful. You can now run the evaluation.")
        sys.exit(0)
    else:
        print("\nModel download failed. Please check your internet connection or HuggingFace token.")
        print("Alternatively, switch retrieval_strategy to 'semantic' in config.yaml to skip reranking.")
        sys.exit(1)
