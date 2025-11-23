#!/bin/bash
#
# vLLM Server Setup for NCSA Delta Cluster using Apptainer
# Converts Docker image to Apptainer SIF and prepares for SLURM execution
#

set -e

# Configuration
MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
VLLM_DOCKER_IMAGE="${VLLM_DOCKER_IMAGE:-docker://vllm/vllm-openai:latest}"
SIF_PATH="${SIF_PATH:-$HOME/containers/vllm-openai.sif}"
CACHE_DIR="${CACHE_DIR:-/scratch/$USER/apptainer_cache}"

echo "========================================================================"
echo "vLLM Apptainer Setup for NCSA Delta"
echo "========================================================================"
echo "Model: $MODEL_NAME"
echo "Docker image: $VLLM_DOCKER_IMAGE"
echo "SIF output: $SIF_PATH"
echo "Cache directory: $CACHE_DIR"
echo "========================================================================"
echo ""

# Create necessary directories
mkdir -p $(dirname $SIF_PATH)
mkdir -p $CACHE_DIR

# Set Apptainer cache directory to avoid filling home quota
export APPTAINER_CACHEDIR=$CACHE_DIR
export SINGULARITY_CACHEDIR=$CACHE_DIR

echo "Step 1: Checking for existing Apptainer/Singularity module..."
if ! command -v apptainer &> /dev/null && ! command -v singularity &> /dev/null; then
    echo "Loading Apptainer module..."
    module load apptainer || module load singularity || {
        echo "ERROR: Neither apptainer nor singularity module found"
        echo "Try: module avail apptainer"
        exit 1
    }
fi

# Determine which command to use
if command -v apptainer &> /dev/null; then
    CONTAINER_CMD="apptainer"
else
    CONTAINER_CMD="singularity"
fi

echo "✓ Using: $CONTAINER_CMD"
echo ""

# Check if SIF already exists
if [ -f "$SIF_PATH" ]; then
    echo "SIF file already exists at: $SIF_PATH"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing SIF file"
        echo ""
        echo "========================================================================"
        echo "Setup Complete!"
        echo "========================================================================"
        echo "SIF file: $SIF_PATH"
        echo ""
        echo "Next steps:"
        echo "1. Submit SLURM job: sbatch run_vllm_delta.slurm"
        echo "2. Or run interactively: see run_vllm_interactive_delta.sh"
        echo "========================================================================"
        exit 0
    fi
fi

echo "Step 2: Converting Docker image to Apptainer SIF..."
echo "This will download the Docker image and convert it (~5-10 minutes)"
echo ""

$CONTAINER_CMD pull --force $SIF_PATH $VLLM_DOCKER_IMAGE

if [ $? -eq 0 ]; then
    echo "✓ Conversion successful!"
    echo ""
else
    echo "✗ Conversion failed"
    echo "Check cache directory: $CACHE_DIR"
    exit 1
fi

# Get SIF file info
echo "Step 3: Verifying SIF file..."
ls -lh $SIF_PATH
echo ""

# Test the container (without GPU)
echo "Step 4: Testing container (basic check, no GPU)..."
$CONTAINER_CMD exec $SIF_PATH python3 --version || {
    echo "WARNING: Container test failed"
}
echo ""

echo "========================================================================"
echo "Setup Complete!"
echo "========================================================================"
echo "SIF file: $SIF_PATH"
echo "Size: $(du -h $SIF_PATH | cut -f1)"
echo ""
echo "Next steps:"
echo ""
echo "1. BATCH JOB (recommended for long runs):"
echo "   sbatch run_vllm_delta.slurm"
echo ""
echo "2. INTERACTIVE JOB (for testing):"
echo "   ./run_vllm_interactive_delta.sh"
echo ""
echo "3. Check job status:"
echo "   squeue -u $USER"
echo ""
echo "4. View logs:"
echo "   tail -f vllm_server_*.out"
echo ""
echo "========================================================================"
