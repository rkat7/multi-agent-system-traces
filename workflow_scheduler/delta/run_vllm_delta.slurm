#!/bin/bash
#SBATCH --job-name=vllm-server
#SBATCH --account=REPLACE_WITH_YOUR_ACCOUNT      # REQUIRED: Replace with your Delta account
#SBATCH --partition=gpuA100x4                     # GPU partition (A100x4, A100x8, A40x4, H200x8)
#SBATCH --nodes=1                                 # Single node
#SBATCH --gpus-per-node=1                         # Number of GPUs (1-4 for x4, 1-8 for x8)
#SBATCH --mem=64G                                 # Memory (adjust based on model size)
#SBATCH --time=04:00:00                           # Max 4 hours (adjust as needed)
#SBATCH --output=vllm_server_%j.out               # Output log
#SBATCH --error=vllm_server_%j.err                # Error log

#
# SLURM Batch Script for Running vLLM Server on Delta
# This script starts vLLM in an Apptainer container with GPU access
#

echo "========================================================================"
echo "vLLM Server on Delta - Job ${SLURM_JOB_ID}"
echo "========================================================================"
echo "Started at: $(date)"
echo "Running on node: $(hostname)"
echo "Partition: $SLURM_JOB_PARTITION"
echo "GPUs allocated: $SLURM_GPUS_ON_NODE"
echo "========================================================================"
echo ""

# Configuration
MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
SIF_PATH="${SIF_PATH:-$HOME/containers/vllm-openai.sif}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-64}"
MAX_BATCHED_TOKENS="${MAX_BATCHED_TOKENS:-4096}"
PORT="${PORT:-8000}"

# Delta-specific paths
WORK_DIR="/work/$USER/vllm_workdir"
HF_CACHE="/scratch/$USER/huggingface_cache"
VLLM_CACHE="/scratch/$USER/vllm_cache"

# Create necessary directories
mkdir -p $WORK_DIR
mkdir -p $HF_CACHE
mkdir -p $VLLM_CACHE

# Environment setup
module reset
module load apptainer || module load singularity

# Set Hugging Face cache to scratch (large models)
export HF_HOME=$HF_CACHE
export TRANSFORMERS_CACHE=$HF_CACHE
export HF_DATASETS_CACHE=$HF_CACHE

# Optional: Set HF token if needed for gated models
# export HF_TOKEN="your_token_here"

echo "Configuration:"
echo "  Model: $MODEL_NAME"
echo "  SIF: $SIF_PATH"
echo "  Max model length: $MAX_MODEL_LEN"
echo "  GPU memory utilization: $GPU_MEMORY_UTIL"
echo "  Port: $PORT"
echo "  HF Cache: $HF_CACHE"
echo "  Work directory: $WORK_DIR"
echo ""

# Verify SIF exists
if [ ! -f "$SIF_PATH" ]; then
    echo "ERROR: SIF file not found at $SIF_PATH"
    echo "Run setup_vllm_apptainer.sh first"
    exit 1
fi

echo "Starting vLLM server..."
echo ""

# Determine container command
if command -v apptainer &> /dev/null; then
    CONTAINER_CMD="apptainer"
else
    CONTAINER_CMD="singularity"
fi

# Run vLLM server in Apptainer container with GPU access
$CONTAINER_CMD run --nv \
    --bind $WORK_DIR:/workspace \
    --bind $HF_CACHE:/root/.cache/huggingface \
    --pwd /workspace \
    $SIF_PATH \
    python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_NAME \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTIL \
    --max-num-seqs $MAX_NUM_SEQS \
    --max-num-batched-tokens $MAX_BATCHED_TOKENS \
    --dtype auto \
    --enable-chunked-prefill \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json \
    --host 0.0.0.0 \
    --port $PORT

EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "vLLM server stopped - Exit code: $EXIT_CODE"
echo "Ended at: $(date)"
echo "========================================================================"

exit $EXIT_CODE
