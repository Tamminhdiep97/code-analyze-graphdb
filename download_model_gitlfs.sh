#!/bin/bash

set -a
source .env
set +a

# Set proxy and disable SSL verification
export GIT_SSL_NO_VERIFY=true
export https_proxy=http://tamdm10:Nguoita12345678%40@hcm-proxy:9090
# export https_proxy=""
# Enable verbose Git and Git LFS output
export GIT_TRACE=1
export GIT_CURL_VERBOSE=1

# Install git-lfs if not already installed
if ! command -v git-lfs &> /dev/null; then
    echo "Installing git-lfs..."
    sudo apt update && sudo apt install -y git-lfs
fi

# Initialize git-lfs
git lfs install

# Clone the model repository
MODEL_PATH="$VLLM_MODEL_DOWNLOAD"
echo "------------------------------------"
echo "$MODEL_PATH"
echo "------------------------------------"
# MODEL_PATH="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
# MODEL_PATH="Qwen/Qwen3-14B-AWQ"

git config --global credential.helper store
MODEL_REPO="https://huggingface.co/$MODEL_PATH"
TARGET_DIR="./review_endpoint/model/$MODEL_PATH"

echo "Cloning model from $MODEL_REPO to $TARGET_DIR"
git clone "$MODEL_REPO" "$TARGET_DIR"

# Resume LFS downloads with verbose output
cd "$TARGET_DIR"
echo "Pulling LFS files..."
git lfs pull

