# RunPod retrieval worker

A serverless GPU worker that serves two open models for Qart.ai's hybrid search:

| Model | Licence | Use |
|---|---|---|
| `BAAI/bge-m3` | MIT | dense text embeddings (normalised) |
| `BAAI/bge-reranker-v2-m3` | Apache-2.0 | cross-encoder relevance scores for reranking |

Inference only: no model is trained or fine-tuned.

## Files
- `handler.py`: validates each job and dispatches it; models load once per worker.
- `Dockerfile`: CUDA/PyTorch base image; both models are downloaded at build time.
- `requirements.txt`: worker-only dependencies (not installed by the app).

## Job format
```
{"input": {"task": "embed", "texts": ["reconcile bank statement"]}}
→ {"vectors": [[...]], "model": "BAAI/bge-m3"}

{"input": {"task": "rerank", "query": "bank reconciliation", "passages": ["...", "..."]}}
→ {"scores": [...], "model": "BAAI/bge-reranker-v2-m3"}
```
At most 256 texts of 8,000 characters per job; invalid input returns `{"error": ...}`.

## Deployment
Serverless endpoint built from this repository: Dockerfile `runpod/Dockerfile`, built from the
repository root (`docker build -f runpod/Dockerfile .`). The base image uses PyTorch 2.6 with CUDA 12.4, so the
endpoint uses previous-generation GPUs (16–24 GB is enough for both models). Min workers 0, max
workers 1, short idle timeout, with an account spending limit.

## Configuration
The app reads `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` from the environment (or the local `.env`,
which is not committed). Without them, `src/retrieval/runpod_backends.py` raises
`RunPodNotConfiguredError`; with them, `python -m eval.retrieval_eval` adds the hybrid
recall@5 next to the BM25 baseline.
