---
layer: digital-generic-team
---
# HuggingFace Model Discovery Scripts

Command-line tools for discovering, inspecting, and ranking Hugging Face Hub models.

## Quick Start

### List Models
```bash
python hf_models.py list --task text-generation --limit 5
```

### Inspect a Model
```bash
python hf_models.py inspect --model-id meta-llama/Llama-2-7b
```

### Determine Best Models
```bash
python hf_models.py determine --task summarization --search "abstractive" --limit 10
```

## Authentication

### Using a Private Token
Set the `HUGGINGFACE_TOKEN` environment variable:

```bash
export HUGGINGFACE_TOKEN=hf_your_token_here
python hf_models.py list --task text-generation
```

Or load from `.env`:
```bash
# .env
HUGGINGFACE_TOKEN=hf_your_token_here
```

### Generate a Token
1. Visit [HuggingFace Settings → Tokens](https://huggingface.co/settings/tokens)
2. Create a new token with appropriate permissions
3. Copy and store securely

## Output Format

All commands output deterministic JSON:

```json
{
  "status": "ok|error",
  "mode": "list|inspect|determine",
  "models": [...],
  "error": "..."
}
```

Parse output with `jq`:
```bash
python hf_models.py list --task text-generation | jq '.models[] | {id, downloads}'
```

## Examples

### Find the most downloaded text classification models
```bash
python hf_models.py determine --task text-classification --limit 20 \
  | jq '.candidates[0:3]'
```

### Get metadata for a specific model
```bash
python hf_models.py inspect --model-id huggingface/transformers \
  | jq '.model | {id, pipeline_tag, downloads, likes}'
```

### Search for multilingual models
```bash
python hf_models.py list --search "multilingual" --limit 10 \
  | jq '.models[] | .id'
```

## Error Handling

When an error occurs, the output includes status and error details:

```json
{
  "status": "error",
  "error": "Model not found: invalid/model-id"
}
```

Check exit code:
- `0`: Success
- `1`: Error (API failure, invalid arguments, etc.)

## Testing

```bash
pytest tests/test_hf_models.py -v
```

Requires:
- pytest
- huggingface_hub
- mock (standard library in Python 3.3+)
