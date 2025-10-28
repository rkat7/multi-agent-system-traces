#!/bin/bash
#
# vLLM Server Setup Script
# Starts vLLM with optimal configuration for agent workflow scheduling
#

set -e

# Configuration
MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-64}"
MAX_BATCHED_TOKENS="${MAX_BATCHED_TOKENS:-4096}"
TENSOR_PARALLEL="${TENSOR_PARALLEL:-1}"

echo "========================================================================"
echo "Starting vLLM Server for Workflow Scheduling"
echo "========================================================================"
echo "Model: $MODEL_NAME"
echo "Port: $PORT"
echo "Max model length: $MAX_MODEL_LEN"
echo "GPU memory utilization: $GPU_MEMORY_UTIL"
echo "Max sequences: $MAX_NUM_SEQS"
echo "Max batched tokens: $MAX_BATCHED_TOKENS"
echo "Tensor parallel size: $TENSOR_PARALLEL"
echo "========================================================================"
echo ""

# Check if NVIDIA GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. NVIDIA GPU required for vLLM."
    exit 1
fi

echo "Checking GPU availability..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Please install Docker."
    exit 1
fi

# Check if Docker can access GPU
echo "Checking Docker GPU support..."
if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo "ERROR: Docker cannot access GPU. Please install nvidia-container-toolkit."
    echo "Install with: sudo apt-get install -y nvidia-container-toolkit"
    exit 1
fi
echo "✓ Docker GPU support confirmed"
echo ""

# Pull vLLM image if not present
echo "Checking for vLLM Docker image..."
if ! docker images | grep -q "vllm/vllm-openai"; then
    echo "Pulling vLLM Docker image (this may take a while)..."
    docker pull vllm/vllm-openai:latest
fi
echo "✓ vLLM image available"
echo ""

# Stop any existing vLLM containers on the same port
echo "Checking for existing containers on port $PORT..."
EXISTING_CONTAINER=$(docker ps -q -f "publish=$PORT")
if [ ! -z "$EXISTING_CONTAINER" ]; then
    echo "Stopping existing container..."
    docker stop $EXISTING_CONTAINER
fi
echo ""

# Start vLLM server
echo "Starting vLLM server..."
echo "This will download the model on first run (may take several minutes)"
echo ""

docker run -d --rm \
    --name vllm-workflow-scheduler \
    --gpus all \
    -p $PORT:8000 \
    --ipc=host \
    -e HF_TOKEN=${HF_TOKEN:-} \
    vllm/vllm-openai:latest \
    --model "$MODEL_NAME" \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTIL \
    --max-num-seqs $MAX_NUM_SEQS \
    --max-num-batched-tokens $MAX_BATCHED_TOKENS \
    --tensor-parallel-size $TENSOR_PARALLEL \
    --dtype auto \
    --enable-chunked-prefill \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json

echo ""
echo "========================================================================"
echo "vLLM server starting in background (container: vllm-workflow-scheduler)"
echo "========================================================================"
echo ""
echo "Waiting for server to be ready (this may take 2-5 minutes)..."
echo "You can monitor progress with: docker logs -f vllm-workflow-scheduler"
echo ""

# Wait for server to be ready
MAX_WAIT=300  # 5 minutes
WAIT_TIME=0
SLEEP_INTERVAL=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✓ Server is ready!"
        break
    fi

    echo "Waiting... ($WAIT_TIME/$MAX_WAIT seconds)"
    sleep $SLEEP_INTERVAL
    WAIT_TIME=$((WAIT_TIME + SLEEP_INTERVAL))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo "ERROR: Server did not start within $MAX_WAIT seconds"
    echo "Check logs with: docker logs vllm-workflow-scheduler"
    exit 1
fi

echo ""
echo "========================================================================"
echo "vLLM Server Ready!"
echo "========================================================================"
echo "Server URL: http://localhost:$PORT"
echo "Health endpoint: http://localhost:$PORT/health"
echo "Models endpoint: http://localhost:$PORT/v1/models"
echo ""
echo "To view logs: docker logs -f vllm-workflow-scheduler"
echo "To stop server: docker stop vllm-workflow-scheduler"
echo ""
echo "Test the server with:"
echo "  curl http://localhost:$PORT/v1/models"
echo ""
echo "========================================================================"
