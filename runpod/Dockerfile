# RunPod serverless worker: BGE-M3 embeddings + bge-reranker-v2-m3 (see runpod/README.md).
# Build context is the REPOSITORY ROOT (RunPod's GitHub build has no build-context setting):
#   docker build -f runpod/Dockerfile .
# Base image with CUDA 12.1 and PyTorch preinstalled, so choose "previous generation" GPUs
# (latest-generation GPUs need CUDA 12.8+).
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /worker
COPY runpod/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download both models at build time so a cold start does not wait for Hugging Face.
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-m3'); CrossEncoder('BAAI/bge-reranker-v2-m3')"

COPY runpod/handler.py .
CMD ["python", "-u", "handler.py"]
