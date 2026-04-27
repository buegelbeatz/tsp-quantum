---
name: "huggingface"
description: "Inspect and discover Hugging Face models with token-aware Hub access."
layer: digital-generic-team
---

# Skill: HuggingFace

## Purpose
Provide Data Scientist workflows for listing, inspecting, and identifying suitable models from Hugging Face Hub with optional token authentication.

## Features

### List Models
Discover models with flexible filtering:
- **Search**: Text-based model search
- **Task**: Filter by pipeline task (e.g., `text-generation`, `summarization`)
- **Author**: Filter by organization or author
- **Limit**: Control result count (default: 10)

**Example:**
```bash
python scripts/hf_models.py list --task text-generation --limit 5
```

**Output:**
```json
{
  "status": "ok",
  "mode": "list",
  "count": 5,
  "models": [
    {"id": "meta-llama/Llama-2-7b", "downloads": 1000000},
    ...
  ]
}
```

### Inspect Model
Get detailed metadata for a specific model:
- Model ID, pipeline tag, download count, likes
- Up to 20 model tags for categorization

**Example:**
```bash
python scripts/hf_models.py inspect --model-id meta-llama/Llama-2-7b
```

**Output:**
```json
{
  "status": "ok",
  "mode": "inspect",
  "model": {
    "id": "meta-llama/Llama-2-7b",
    "pipeline_tag": "text-generation",
    "downloads": 1000000,
    "likes": 5000,
    "tags": ["llama", "large-language-model", ...]
  }
}
```

### Determine Models
Intelligently rank models based on task match and popularity:
- **Score Logic**: +2 points for task tag match, +1 point for any downloads
- Ranked by score (descending), then by download count

**Example:**
```bash
python scripts/hf_models.py determine --task text-generation --limit 10
```

**Output:**
```json
{
  "status": "ok",
  "mode": "determine",
  "count": 3,
  "candidates": [
    {"id": "meta-llama/Llama-2-7b", "score": 3, "downloads": 1000000},
    {"id": "gpt2", "score": 1, "downloads": 500000},
    ...
  ]
}
```

## Configuration

### Environment Variables
- `HUGGINGFACE_TOKEN`: Optional authentication token for private model access
  - If not set, uses public API without authentication
  - Increases rate limits and enables private model access

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set token in .env (optional, for private models)
export HUGGINGFACE_TOKEN=hf_your_token_here
```

## Inputs
- CLI arguments via `argparse` with subcommands
- Optional `HUGGINGFACE_TOKEN` from environment
- Query parameters: `task`, `search`, `author`, `model-id`, `limit`

## Outputs
- Deterministic JSON payloads with status, mode, and results
- Error handling returns `{"status": "error", "error": "..."}` on failure
- Compatible with jq for downstream filtering and processing

## Entry Points
- `scripts/hf_models.py`: Main CLI script

## Dependencies
- `huggingface_hub`: Official Hugging Face Hub API client
- `.github/skills/shared/shell/SKILL.md`: Registry-backed tool execution

## Testing
```bash
pytest scripts/tests/test_hf_models.py -v
```

## Information Flow
- **producer**: Data scientist workflow or direct script invocation
- **consumer**: huggingface skill scripts, downstream data processing pipelines
- **trigger**: Request to list, inspect, or determine models from Hub
- **payload summary**: Combined search filters, task constraints, optional authenticated token context → structured JSON model metadata
