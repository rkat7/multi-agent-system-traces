#!/bin/bash
#
# Interactive Job Script for Testing vLLM on Delta
# Requests an interactive GPU node and starts vLLM server
#

set -e

echo "========================================================================"
echo "Requesting Interactive GPU Node on Delta"
echo "========================================================================"
echo ""

# Configuration
ACCOUNT="${ACCOUNT:-REPLACE_WITH_YOUR_ACCOUNT}"
PARTITION="${PARTITION:-gpuA100x4-interactive}"
GPUS="${GPUS:-1}"
MEM="${MEM:-64G}"
TIME="${TIME:-01:00:00}"

echo "Configuration:"
echo "  Account: $ACCOUNT"
echo "  Partition: $PARTITION"
echo "  GPUs: $GPUS"
echo "  Memory: $MEM"
echo "  Time: $TIME"
echo ""

if [ "$ACCOUNT" = "REPLACE_WITH_YOUR_ACCOUNT" ]; then
    echo "ERROR: Please set your Delta account"
    echo "Usage: ACCOUNT=your_account $0"
    exit 1
fi

echo "Requesting interactive node..."
echo "This may take a few minutes depending on queue..."
echo ""

# Request interactive node
srun --account=$ACCOUNT \
     --partition=$PARTITION \
     --nodes=1 \
     --gpus-per-node=$GPUS \
     --mem=$MEM \
     --time=$TIME \
     --pty bash -c '

echo "========================================================================"
echo "Interactive Node Allocated: $(hostname)"
echo "GPUs: $SLURM_GPUS_ON_NODE"
echo "========================================================================"
echo ""

# Load modules
module reset
module load apptainer || module load singularity

# Configuration
MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
SIF_PATH="${SIF_PATH:-$HOME/containers/vllm-openai.sif}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.90}"

# Delta paths
WORK_DIR="/work/$USER/vllm_workdir"
HF_CACHE="/scratch/$USER/huggingface_cache"

mkdir -p $WORK_DIR
mkdir -p $HF_CACHE

export HF_HOME=$HF_CACHE

# Verify SIF
if [ ! -f "$SIF_PATH" ]; then
    echo "ERROR: SIF file not found at $SIF_PATH"
    echo "Run setup_vllm_apptainer.sh first"
    exit 1
fi

echo "Starting vLLM server interactively..."
echo "Press Ctrl+C to stop"
echo ""
echo "Server will be available at: http://$(hostname):$PORT"
echo "To test from login node: ssh -L $PORT:$(hostname):$PORT $(whoami)@dt-login03.delta.ncsa.illinois.edu"
echo ""

# Determine container command
if command -v apptainer &> /dev/null; then
    CONTAINER_CMD="apptainer"
else
    CONTAINER_CMD="singularity"
fi

# Run vLLM interactively
$CONTAINER_CMD run --nv \
    --bind $WORK_DIR:/workspace \
    --bind $HF_CACHE:/root/.cache/huggingface \
    --pwd /workspace \
    $SIF_PATH \
    python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_NAME \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTIL \
    --host 0.0.0.0 \
    --port $PORT
'

echo ""
echo "========================================================================"
echo "Interactive session ended"
echo "========================================================================"
