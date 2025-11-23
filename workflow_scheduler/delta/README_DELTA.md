```markdown
# Running Workflow Scheduler on NCSA Delta Cluster

Complete guide for deploying and running the DAG-aware workflow scheduler on UIUC's NCSA Delta supercomputer.

## Delta Cluster Overview

**Hardware Available:**
- **GPU Nodes:**
  - A100 (40GB): 4-way and 8-way configurations
  - A40 (48GB): 4-way configuration
  - H200 (141GB): 8-way configuration
  - MI100 (32GB): 8-way AMD configuration

- **Storage:**
  - `/work/$USER`: Lustre file system (fast, large capacity)
  - `/scratch/$USER`: Temporary scratch space
  - `/u/$USER` or `/home/$USER`: Home directory (100 GB quota)
  - `/projects`: Shared project storage

- **Container System:** Apptainer/Singularity (not Docker)
- **Job Scheduler:** SLURM

---

## Prerequisites

### 1. Delta Account Setup

```bash
# Login to Delta
ssh $USER@login.delta.ncsa.illinois.edu

# Check your account allocations
accounts

# Note your account name (e.g., bbka-delta-gpu)
```

### 2. Storage Setup

```bash
# Create project directories
mkdir -p /work/$USER/MAST
mkdir -p /work/$USER/workflow_results
mkdir -p /scratch/$USER/huggingface_cache
mkdir -p /scratch/$USER/apptainer_cache
mkdir -p $HOME/containers
```

### 3. Transfer Code to Delta

**From your local machine:**
```bash
# Option 1: rsync (recommended)
rsync -avz --progress MAST/ $USER@login.delta.ncsa.illinois.edu:/work/$USER/MAST/

# Option 2: scp
scp -r MAST $USER@login.delta.ncsa.illinois.edu:/work/$USER/

# Option 3: git (if repo is public/accessible)
ssh $USER@login.delta.ncsa.illinois.edu
cd /work/$USER
git clone https://github.com/your-repo/MAST.git
```

---

## Setup Instructions

### Step 1: Prepare Python Environment

**On Delta login node:**
```bash
cd /work/$USER/MAST/workflow_scheduler

# Load Python module
module load python/3.11  # or check: module avail python

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Convert vLLM Docker Image to Apptainer

```bash
cd /work/$USER/MAST/workflow_scheduler/delta

# Set cache directory to scratch (important - home has 100GB quota)
export APPTAINER_CACHEDIR=/scratch/$USER/apptainer_cache

# Run conversion script
./setup_vllm_apptainer.sh
```

**This will:**
- Download vLLM Docker image (~5GB)
- Convert to Apptainer SIF format
- Save to `$HOME/containers/vllm-openai.sif`
- Take 5-10 minutes

**Custom configuration:**
```bash
# Use different model or paths
MODEL_NAME="meta-llama/Llama-3.1-70B-Instruct" \
SIF_PATH="/work/$USER/containers/vllm-70b.sif" \
./setup_vllm_apptainer.sh
```

### Step 3: Configure SLURM Scripts

**Edit account name in ALL .slurm files:**
```bash
# Replace in all scripts
cd /work/$USER/MAST/workflow_scheduler/delta
sed -i 's/REPLACE_WITH_YOUR_ACCOUNT/your-account-name/g' *.slurm

# Or edit manually
nano run_vllm_delta.slurm
# Change: #SBATCH --account=REPLACE_WITH_YOUR_ACCOUNT
# To:     #SBATCH --account=your-account-name
```

---

## Running Workflows

### Method 1: Batch Jobs (Recommended for Production)

**Step 1: Submit vLLM Server Job**
```bash
cd /work/$USER/MAST/workflow_scheduler/delta

# Submit vLLM server job
sbatch run_vllm_delta.slurm

# Check job status
squeue -u $USER

# View output (once running)
tail -f vllm_server_*.out
```

**Step 2: Submit Workflow Execution Job**
```bash
# Once vLLM server is running, submit workflow job
sbatch run_workflow_delta.slurm

# Monitor
squeue -u $USER
tail -f workflow_*.out
```

**Expected Timeline:**
- vLLM job: 5-10 min startup + runtime
- Workflow job: 2-5 min per trace

### Method 2: Interactive Testing (Recommended for Development)

**Start Interactive vLLM Server:**
```bash
cd /work/$USER/MAST/workflow_scheduler/delta

# Set your account
export ACCOUNT=your-account-name

# Request interactive node and start vLLM
./run_vllm_interactive_delta.sh
```

**In a separate terminal, run workflow:**
```bash
# SSH to Delta in new terminal
ssh $USER@login.delta.ncsa.illinois.edu
cd /work/$USER/MAST/workflow_scheduler

# Activate environment
source venv/bin/activate

# Run workflow (replace NODE with actual compute node name)
python main.py \
  --dag ../visualizations/AppWorld/aa8502b_1_dag.json \
  --vllm-url http://NODE:8000/v1 \
  --compare
```

---

## GPU Partition Options

Choose based on your needs:

### For 8B Models (Llama-3.1-8B-Instruct)

```bash
#SBATCH --partition=gpuA100x4        # Standard, 4x A100 40GB
#SBATCH --gpus-per-node=1            # 1 GPU sufficient
#SBATCH --mem=64G                    # Moderate memory
```

### For 70B Models (Llama-3.1-70B-Instruct)

```bash
#SBATCH --partition=gpuA100x8        # 8x A100 for tensor parallel
#SBATCH --gpus-per-node=4            # 4 GPUs for 70B model
#SBATCH --mem=256G                   # More memory
# Add to vLLM args: --tensor-parallel-size 4
```

### For H200 (Latest, Highest Memory)

```bash
#SBATCH --partition=gpuH200x8        # 8x H200 141GB each
#SBATCH --gpus-per-node=1            # Even 1 H200 has massive memory
#SBATCH --mem=128G
```

### Available Partitions

| Partition | GPUs | Memory/GPU | Best For |
|-----------|------|------------|----------|
| `gpuA100x4` | 4x A100 | 40GB | 8B-13B models |
| `gpuA100x8` | 8x A100 | 40GB | 70B models (tensor parallel) |
| `gpuA40x4` | 4x A40 | 48GB | 8B-13B with larger context |
| `gpuH200x8` | 8x H200 | 141GB | Largest models, long context |
| `gpuMI100x8` | 8x MI100 | 32GB | AMD GPUs (experimental) |

**Interactive versions:** Add `-interactive` suffix (e.g., `gpuA100x4-interactive`)

---

## Configuration Adjustments

### vLLM Server Parameters (in run_vllm_delta.slurm)

```bash
# Model selection
MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"

# Context window
MAX_MODEL_LEN=8192    # Increase for longer context (4096, 16384, 32768)

# Batch size
MAX_NUM_SEQS=64       # Higher = more throughput, more memory
MAX_BATCHED_TOKENS=4096

# GPU memory
GPU_MEMORY_UTIL=0.90  # 0.85-0.95 range
```

### For Maximum Throughput

```bash
MAX_MODEL_LEN=16384
MAX_NUM_SEQS=128
MAX_BATCHED_TOKENS=8192
GPU_MEMORY_UTIL=0.92
```

### For Low Latency

```bash
MAX_MODEL_LEN=4096
MAX_NUM_SEQS=32
MAX_BATCHED_TOKENS=2048
GPU_MEMORY_UTIL=0.85
```

---

## Monitoring and Debugging

### Check Job Status

```bash
# Your jobs
squeue -u $USER

# Detailed job info
scontrol show job JOB_ID

# Job history
sacct -u $USER --format=JobID,JobName,Partition,State,Elapsed,MaxRSS
```

### View Logs

```bash
# Real-time monitoring
tail -f vllm_server_*.out
tail -f workflow_*.out

# Error logs
tail -f vllm_server_*.err
tail -f workflow_*.err

# List all logs
ls -lt *.out *.err
```

### Check vLLM Server Health

**From compute node or login node:**
```bash
# Replace NODE with compute node name from squeue
curl http://NODE:8000/health

# List models
curl http://NODE:8000/v1/models
```

### GPU Utilization

```bash
# If on compute node with GPU access
nvidia-smi

# Watch GPU usage
watch -n 1 nvidia-smi
```

### Common Issues

**1. Job Pending**
```bash
# Check why pending
squeue -u $USER -o "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"

# Reasons:
# - Resources: Not enough GPUs available
# - Priority: Other users have higher priority
# - QOSMaxWallDurationPerJobLimit: Time limit too long
```

**2. Out of Memory**
- Reduce `MAX_NUM_SEQS` or `MAX_BATCHED_TOKENS`
- Reduce `MAX_MODEL_LEN`
- Lower `GPU_MEMORY_UTIL` to 0.85
- Request more memory: `#SBATCH --mem=128G`

**3. Home Directory Quota Exceeded**
```bash
# Check quota
quota

# Move cache to scratch
export APPTAINER_CACHEDIR=/scratch/$USER/apptainer_cache
export HF_HOME=/scratch/$USER/huggingface_cache
```

**4. Module Not Found**
```bash
# List available modules
module avail python
module avail apptainer
module avail singularity

# Load specific version
module load python/3.11
```

---

## Performance Optimization

### Storage Best Practices

**Do:**
- ✅ Use `/work` for project files (fast Lustre)
- ✅ Use `/scratch` for cache and temporary files
- ✅ Keep model weights in `/scratch/$USER/huggingface_cache`

**Don't:**
- ❌ Don't use `/home` for large files (100GB quota)
- ❌ Don't write many small files to Lustre (use local `/tmp`)

### Job Scheduling Tips

**1. Right-size your resources:**
```bash
# Don't request more than you need
#SBATCH --gpus-per-node=1  # Not 4 if you only use 1
#SBATCH --mem=64G          # Not 256G if you only need 64G
#SBATCH --time=04:00:00    # Not 48:00:00 if you finish in 4h
```

**2. Use job arrays for multiple traces:**
```bash
#SBATCH --array=1-10

# In script:
DAG_FILE=$(ls ../visualizations/AppWorld/*.json | sed -n "${SLURM_ARRAY_TASK_ID}p")
python main.py --dag $DAG_FILE
```

**3. Chain jobs with dependencies:**
```bash
# Start vLLM server
JOB1=$(sbatch --parsable run_vllm_delta.slurm)

# Start workflow after vLLM is running
sbatch --dependency=after:$JOB1 run_workflow_delta.slurm
```

---

## Expected Performance on Delta

### A100 GPU (40GB) with Llama-3.1-8B

| Metric | Sequential | Dependency-Aware |
|--------|-----------|------------------|
| Time (36 nodes) | ~40-50s | ~25-30s |
| Speedup | 1.0x | **1.6-1.8x** |
| GPU Utilization | 60-70% | 85-95% |
| Tokens/sec | ~70-80 | ~115-130 |

### H200 GPU (141GB) with Llama-3.1-70B

| Metric | Sequential | Dependency-Aware |
|--------|-----------|------------------|
| Time (36 nodes) | ~60-80s | ~35-45s |
| Speedup | 1.0x | **1.7-2.0x** |
| GPU Utilization | 70-80% | 90-98% |
| Tokens/sec | ~50-60 | ~90-110 |

---

## Example Workflows

### Quick Test (Single Trace)

```bash
cd /work/$USER/MAST/workflow_scheduler/delta

# 1. Convert Docker image (first time only)
./setup_vllm_apptainer.sh

# 2. Start vLLM
sbatch run_vllm_delta.slurm

# 3. Wait for it to start (check: squeue -u $USER)

# 4. Run workflow
sbatch run_workflow_delta.slurm

# 5. Check results
ls -lh /work/$USER/workflow_results/
```

### Full Benchmark (All AppWorld Traces)

```bash
# Create job array script
cat > run_all_traces.slurm << 'EOF'
#!/bin/bash
#SBATCH --array=1-16
#SBATCH --account=your-account
#SBATCH --partition=gpuA100x4
#SBATCH --gpus-per-node=1
#SBATCH --mem=16G
#SBATCH --time=01:00:00

cd /work/$USER/MAST/workflow_scheduler
source venv/bin/activate

DAG_FILE=$(ls ../visualizations/AppWorld/*.json | sed -n "${SLURM_ARRAY_TASK_ID}p")

python main.py \
  --dag $DAG_FILE \
  --vllm-url http://VLLM_NODE:8000/v1 \
  --compare \
  --output-dir /work/$USER/workflow_results
EOF

# Submit array job
sbatch run_all_traces.slurm
```

---

## Costs and Allocation

Delta uses **Service Units (SUs)** charged per GPU-hour:

| Resource | SU Rate | Example Cost |
|----------|---------|--------------|
| A100 GPU | ~2 SU/hr | 4hr job = 8 SU |
| A40 GPU | ~1.5 SU/hr | 4hr job = 6 SU |
| H200 GPU | ~3 SU/hr | 4hr job = 12 SU |

**Check your allocation:**
```bash
accounts
```

**Monitor usage:**
```bash
sacct -u $USER --format=JobID,JobName,Elapsed,AllocCPUS,AllocTRES
```

---

## Getting Help

**Delta Documentation:**
- User Guide: https://docs.ncsa.illinois.edu/systems/delta/
- Container Guide: https://docs.ncsa.illinois.edu/systems/delta/en/latest/user_guide/containers.html
- Job Submission: https://docs.ncsa.illinois.edu/systems/delta/en/latest/user_guide/running_jobs.html

**Support:**
- Email: help@ncsa.illinois.edu
- Include: Job ID, error messages, slurm scripts

**Project-Specific:**
- Check main `README.md` for workflow scheduler details
- See `QUICKSTART.md` for general usage
- Review `IMPLEMENTATION_SUMMARY.md` for architecture

---

## Checklist

**Pre-run:**
- [ ] Account name set in all `.slurm` files
- [ ] Python environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] vLLM SIF file created (`setup_vllm_apptainer.sh`)
- [ ] Storage directories created
- [ ] Code transferred to `/work/$USER/MAST/`

**Testing:**
- [ ] Interactive vLLM server starts successfully
- [ ] Can connect to vLLM from login node
- [ ] Workflow executes on single trace
- [ ] Results saved to `/work/$USER/workflow_results/`

**Production:**
- [ ] Batch vLLM job submitted and running
- [ ] Workflow job submitted with dependency
- [ ] Monitor logs for errors
- [ ] Collect results and generate reports

---

**You're ready to run on Delta!** Start with the Quick Test workflow above.
```
