# DAG-Aware Workflow Scheduler for Multi-Agent Systems

A prototype implementation of dependency-aware workflow scheduling for multi-agent LLM systems using vLLM. This system executes AppWorld traces from the MAST dataset with optimized scheduling policies.

## Overview

This prototype demonstrates:
- **DAG-based workflow parsing** from MAST AppWorld traces
- **Dependency-aware scheduling** with topological sort and batching
- **vLLM integration** for efficient LLM inference serving
- **Tool calling support** for AppWorld agent APIs
- **Performance comparison** across different scheduling policies

## Architecture

```
┌─────────────────────────────────┐
│  Workflow Scheduler             │
│  • Loads DAG from MAST trace    │
│  • Topological sort for order   │
│  • Batches independent nodes    │
│  • Tracks dependencies          │
└──────────┬──────────────────────┘
           │ Batched requests
┌──────────▼──────────────────────┐
│  vLLM Server                    │
│  • Serves Llama 3.1 8B/70B      │
│  • Continuous batching          │
│  • Tool calling support         │
│  • OpenAI-compatible API        │
└─────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- NVIDIA GPU with CUDA support
- Docker with GPU support (nvidia-container-toolkit)
- At least 16GB GPU memory (for 8B model)

### Setup

1. **Install Python dependencies:**
```bash
cd workflow_scheduler
pip install -r requirements.txt
```

2. **Install Docker GPU support (if not already installed):**
```bash
# Ubuntu/Debian
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## Usage

### Step 1: Start vLLM Server

Use the provided setup script:

```bash
./setup_vllm.sh
```

This will:
- Check GPU availability
- Pull vLLM Docker image
- Start vLLM server on port 8000
- Load Llama-3.1-8B-Instruct model
- Wait for server to be ready

**Custom configuration:**
```bash
# Use different model
MODEL_NAME="meta-llama/Llama-3.1-70B-Instruct" ./setup_vllm.sh

# Use different port
PORT=8001 ./setup_vllm.sh

# Adjust memory settings
GPU_MEMORY_UTIL=0.95 MAX_NUM_SEQS=128 ./setup_vllm.sh
```

### Step 2: Run Workflow Execution

**Single policy execution:**
```bash
python main.py \
  --dag ../visualizations/AppWorld/aa8502b_1_dag.json \
  --policy dependency_aware
```

**Compare multiple policies:**
```bash
python main.py \
  --dag ../visualizations/AppWorld/aa8502b_1_dag.json \
  --compare
```

This will run the workflow with both `sequential` and `dependency_aware` policies and generate a comparison report.

**Full options:**
```bash
python main.py \
  --dag <path_to_dag.json> \
  --vllm-url http://127.0.0.1:8000/v1 \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --policy dependency_aware \
  --max-parallel 4 \
  --max-tokens 512 \
  --temperature 0.7 \
  --output-dir results/ \
  --compare
```

### Step 3: Analyze Results

Results are saved to `results/` directory:
- `<task_id>_<policy>_<timestamp>.json` - Execution results
- `<task_id>_comparison_<timestamp>.txt` - Comparison report

**Example output:**
```
==================================================
SCHEDULING POLICY COMPARISON REPORT
==================================================

## Overall Metrics

Policy               Time (ms)    Tokens     Batches    Parallel   Success
--------------------------------------------------------------------------------
sequential           45230        3420       36         1.00       ✓
dependency_aware     28450        3420       12         3.00       ✓

## Performance Improvements

dependency_aware vs sequential:
  Speedup: 1.59x
  Time saved: 16780ms (16.78s)
  Throughput improvement: +59.0%
  Parallelism factor: 3.00
```

## Components

### dag_parser.py
- Parses AppWorld DAG JSON files
- Builds adjacency lists and dependency graphs
- Implements topological sort (Kahn's algorithm)
- Groups nodes into executable batches

### vllm_client.py
- OpenAI-compatible client for vLLM
- Handles inference requests
- Supports tool calling for AppWorld APIs
- Tracks token usage and latency

### scheduler.py
- Core workflow scheduler
- Implements scheduling policies:
  - `sequential`: One node at a time
  - `dependency_aware`: Batch independent nodes
  - `parallel`: Maximum parallelism
- Tracks execution state and dependencies

### metrics.py
- Collects execution metrics
- Generates comparison reports
- Analyzes speedup and throughput

### main.py
- CLI interface
- Orchestrates execution pipeline
- Handles result saving

## Configuration

### vLLM Configuration (config/vllm_config.yaml)

Multiple profiles for different use cases:

- **dev_profile**: Development/testing (8K context, 64 seqs)
- **prod_profile**: Production throughput (16K context, 128 seqs)
- **low_latency_profile**: Interactive agents (4K context, 32 seqs)
- **multi_gpu_profile**: Large models (70B on 4 GPUs)

## Scheduling Policies

### Sequential
- Processes nodes one-by-one in topological order
- Baseline for comparison
- No parallelism (parallelism factor = 1.0)

### Dependency-Aware
- Groups independent nodes into batches
- Executes batches sequentially
- Nodes within batch can run in parallel
- Typical parallelism factor: 2-4x

### Parallel
- Maximum aggressive batching
- Similar to dependency-aware in current implementation
- Future: async/concurrent execution

## Expected Performance

Based on Medium article findings and Agent.xpu research:

| Metric | Sequential | Dependency-Aware | Expected Improvement |
|--------|-----------|------------------|---------------------|
| Latency | Baseline | 1.5-2.0x faster | 40-50% reduction |
| Throughput | Baseline | 1.5-2.0x higher | 50-100% increase |
| GPU Utilization | 60-70% | 85-95% | 25-35% improvement |
| Parallelism | 1.0 | 2-4 nodes/batch | 2-4x |

## Troubleshooting

### vLLM server won't start

```bash
# Check GPU
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Check logs
docker logs vllm-workflow-scheduler

# Reduce memory requirements
GPU_MEMORY_UTIL=0.85 MAX_MODEL_LEN=4096 ./setup_vllm.sh
```

### Out of memory errors

```bash
# Use smaller model
MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct" ./setup_vllm.sh

# Reduce batch size
MAX_NUM_SEQS=32 MAX_BATCHED_TOKENS=2048 ./setup_vllm.sh

# Reduce context window
MAX_MODEL_LEN=4096 ./setup_vllm.sh
```

### Connection errors

```bash
# Check if server is running
curl http://localhost:8000/health

# Check if model is loaded
curl http://localhost:8000/v1/models

# Wait longer for model loading
# First run downloads model weights (can take 5-10 minutes)
docker logs -f vllm-workflow-scheduler
```

## Testing Individual Components

```bash
# Test DAG parser
python dag_parser.py ../visualizations/AppWorld/aa8502b_1_dag.json

# Test vLLM client (requires server running)
python vllm_client.py

# Test metrics
python metrics.py
```

## Future Enhancements

- [ ] Async/concurrent request handling
- [ ] Failure-aware scheduling using MAST taxonomy
- [ ] Cost-optimal scheduling (latency vs. cost trade-offs)
- [ ] Heterogeneous execution (different models for different agents)
- [ ] KV cache sharing across similar agent turns
- [ ] Tool call prefetching
- [ ] Real-time monitoring dashboard
- [ ] Support for AG2 and HyperAgent traces

## Research Value

This prototype demonstrates:

1. **Workflow-level optimization**: First system to apply DAG-aware scheduling to multi-agent LLM traces
2. **Real-world traces**: Uses actual MAST dataset (1K+ traces)
3. **Systematic evaluation**: Quantifies speedup and throughput improvements
4. **Tool calling integration**: Supports AppWorld API tool calls
5. **Reproducible framework**: Open implementation for research community

## Citation

If you use this work, please cite:

```bibtex
@article{cemri2025multi,
  title={Why Do Multi-Agent LLM Systems Fail?},
  author={Cemri, Mert and Pan, Melissa Z and Yang, Shuyi and others},
  journal={arXiv preprint arXiv:2503.13657},
  year={2025}
}
```

## License

MIT License - see MAST repository for details

## Acknowledgments

- MAST dataset and taxonomy
- vLLM inference engine
- Medium article on efficient LLM agent serving
- Agent.xpu and Autellix research papers
