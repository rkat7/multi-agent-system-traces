# Quick Start Guide

Get the DAG-aware workflow scheduler running in 5 minutes.

## Step-by-Step Setup

### 1. Verify GPU and Dependencies

```bash
# Check GPU
nvidia-smi

# Should show your GPU(s) with available memory
```

### 2. Install Python Dependencies

```bash
cd workflow_scheduler
pip install -r requirements.txt
```

### 3. Start vLLM Server

```bash
./setup_vllm.sh
```

**What this does:**
- Pulls vLLM Docker image (first run only, ~5GB)
- Downloads Llama-3.1-8B-Instruct model (first run only, ~16GB)
- Starts vLLM server on port 8000
- Waits for server to be ready (~2-5 minutes)

**Expected output:**
```
========================================================================
vLLM Server Ready!
========================================================================
Server URL: http://localhost:8000
Health endpoint: http://localhost:8000/health
Models endpoint: http://localhost:8000/v1/models
```

### 4. Test the Server

```bash
# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models -H "Authorization: Bearer sk-local-demo"
```

### 5. Run Your First Workflow

**Test with DAG parser:**
```bash
python dag_parser.py ../visualizations/AppWorld/aa8502b_1_dag.json
```

**Run single policy:**
```bash
python main.py --dag ../visualizations/AppWorld/aa8502b_1_dag.json --policy dependency_aware
```

**Compare policies (recommended for research):**
```bash
python main.py --dag ../visualizations/AppWorld/aa8502b_1_dag.json --compare
```

### 6. View Results

Results are saved to `results/` directory:

```bash
ls -lh results/

# View latest comparison
cat results/*comparison*.txt
```

## Expected Timeline

- **First run:**
  - vLLM setup: 10-15 minutes (downloads model)
  - Workflow execution: 2-5 minutes
  - **Total: ~15-20 minutes**

- **Subsequent runs:**
  - vLLM startup: 30-60 seconds (model cached)
  - Workflow execution: 2-5 minutes
  - **Total: ~3-6 minutes**

## Example Output

```
======================================================================
EXECUTING WORKFLOW: aa8502b_1
Task: Follow all the artists who have sung at least one song I have liked on Spotify.
Scheduling Policy: dependency_aware
======================================================================

Executing 36 dependency-aware batches...

Batch 1/36: 1 nodes
  Executing batch of 1 nodes...
    - node_0: Supervisor Response (Supervisor)
      ✓ Completed in 1240ms, 145 tokens

Batch 2/36: 1 nodes
  Executing batch of 1 nodes...
    - node_1: Code Exec (system)
      ✓ Completed in 85ms, 0 tokens

...

======================================================================
WORKFLOW EXECUTION COMPLETED
  Total Time: 28450ms (28.45s)
  Nodes Executed: 36/36
  Failed Nodes: 0
  Total Tokens: 3420
  Success: True
======================================================================
```

## Common Issues

### 1. vLLM server won't start

**Check Docker GPU access:**
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

**If fails, install nvidia-container-toolkit:**
```bash
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. Out of memory

**Reduce batch size:**
```bash
MAX_NUM_SEQS=32 MAX_BATCHED_TOKENS=2048 ./setup_vllm.sh
```

**Or use smaller context:**
```bash
MAX_MODEL_LEN=4096 ./setup_vllm.sh
```

### 3. Connection refused

**Wait for model to load:**
```bash
docker logs -f vllm-workflow-scheduler
```

Look for: `"Application startup complete"`

## Next Steps

1. **Try different DAGs:**
   ```bash
   ls ../visualizations/AppWorld/*.json
   python main.py --dag ../visualizations/AppWorld/396c5a2_1_dag.json --compare
   ```

2. **Experiment with parameters:**
   ```bash
   python main.py \
     --dag ../visualizations/AppWorld/aa8502b_1_dag.json \
     --max-tokens 1024 \
     --temperature 0.5 \
     --max-parallel 8 \
     --compare
   ```

3. **Analyze results:**
   - Compare latency across policies
   - Measure parallelism factor
   - Calculate throughput improvements

4. **Scale up:**
   - Use larger model (70B with 4 GPUs)
   - Process multiple traces
   - Benchmark full MAST AppWorld dataset

## Stopping the Server

```bash
docker stop vllm-workflow-scheduler
```

## Clean Up

```bash
# Stop container
docker stop vllm-workflow-scheduler

# Remove results
rm -rf results/*

# Remove Docker image (optional, saves ~5GB)
docker rmi vllm/vllm-openai:latest
```

## Performance Expectations

Based on a single GPU (e.g., A100/L40S):

| Metric | Sequential | Dependency-Aware |
|--------|-----------|------------------|
| AppWorld trace (36 nodes) | ~45s | ~28s |
| Tokens/second | ~75 | ~120 |
| GPU utilization | ~65% | ~90% |
| Speedup | 1.0x | **1.6x** |

## Getting Help

- Check logs: `docker logs vllm-workflow-scheduler`
- Review README.md for detailed documentation
- Test components individually (see Testing section in README)

## Research Tips

For publishable results:

1. **Run multiple traces:**
   ```bash
   for dag in ../visualizations/AppWorld/*.json; do
       python main.py --dag "$dag" --compare
   done
   ```

2. **Collect metrics:**
   - Save all results/*.json files
   - Aggregate speedup statistics
   - Calculate mean/median/p95 latency

3. **Vary parameters:**
   - Different batch sizes
   - Different max tokens
   - Different temperature settings

4. **Compare baselines:**
   - Sequential vs. dependency-aware
   - Different vLLM configurations
   - Different model sizes

---

**Ready to run?** Start with Step 1 above!
