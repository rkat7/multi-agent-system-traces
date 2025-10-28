#!/bin/bash
#SBATCH --job-name=workflow-exec
#SBATCH --account=REPLACE_WITH_YOUR_ACCOUNT      # REQUIRED: Replace with your Delta account
#SBATCH --partition=gpuA100x4                     # Must match vLLM server partition
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1                         # 1 GPU for client (or use CPU-only node)
#SBATCH --mem=16G                                 # Modest memory for client
#SBATCH --time=02:00:00                           # Workflow execution time
#SBATCH --output=workflow_%j.out
#SBATCH --error=workflow_%j.err
#SBATCH --dependency=singleton                    # Wait for vLLM server job

#
# SLURM Batch Script for Running Workflow Scheduler on Delta
# This assumes vLLM server is already running (submit run_vllm_delta.slurm first)
#

echo "========================================================================"
echo "Workflow Scheduler on Delta - Job ${SLURM_JOB_ID}"
echo "========================================================================"
echo "Started at: $(date)"
echo "Running on node: $(hostname)"
echo "========================================================================"
echo ""

# Configuration
VLLM_URL="${VLLM_URL:-http://localhost:8000/v1}"
MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.1-8B-Instruct}"
DAG_PATH="${DAG_PATH:-../visualizations/AppWorld/aa8502b_1_dag.json}"
POLICY="${POLICY:-dependency_aware}"

# Delta paths
PROJECT_DIR="/work/$USER/MAST/workflow_scheduler"
RESULTS_DIR="/work/$USER/workflow_results"

mkdir -p $RESULTS_DIR

# Environment setup
module reset
module load python/3.11  # or python/3.10, check: module avail python

# Change to project directory
cd $PROJECT_DIR || {
    echo "ERROR: Project directory not found: $PROJECT_DIR"
    echo "Make sure to copy your code to /work/$USER/MAST/"
    exit 1
}

# Activate virtual environment if using one
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Verify Python dependencies
python -c "import openai, networkx, yaml" || {
    echo "ERROR: Missing Python dependencies"
    echo "Install with: pip install -r requirements.txt"
    exit 1
}

echo "Configuration:"
echo "  vLLM URL: $VLLM_URL"
echo "  Model: $MODEL_NAME"
echo "  DAG: $DAG_PATH"
echo "  Policy: $POLICY"
echo "  Results directory: $RESULTS_DIR"
echo ""

# Wait for vLLM server to be ready (if running in same job chain)
echo "Checking vLLM server availability..."
MAX_WAIT=300
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s ${VLLM_URL}/health > /dev/null 2>&1; then
        echo "✓ vLLM server is ready"
        break
    fi
    echo "Waiting for vLLM server... ($WAIT_TIME/$MAX_WAIT seconds)"
    sleep 10
    WAIT_TIME=$((WAIT_TIME + 10))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo "ERROR: vLLM server did not respond within $MAX_WAIT seconds"
    echo "Check if vLLM server job is running: squeue -u $USER"
    exit 1
fi

echo ""
echo "Starting workflow execution..."
echo ""

# Run workflow scheduler
python main.py \
    --dag $DAG_PATH \
    --vllm-url $VLLM_URL \
    --model $MODEL_NAME \
    --policy $POLICY \
    --output-dir $RESULTS_DIR \
    --compare

EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Workflow execution completed - Exit code: $EXIT_CODE"
echo "Results saved to: $RESULTS_DIR"
echo "Ended at: $(date)"
echo "========================================================================"

# List results
echo ""
echo "Generated files:"
ls -lh $RESULTS_DIR/*$(date +%Y%m%d)* 2>/dev/null || echo "No results found"

exit $EXIT_CODE
