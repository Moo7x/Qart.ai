# RunPod serverless worker: BGE-M3 embeddings + bge-reranker-v2-m3 (see runpod/README.md).
# Base image with CUDA and PyTorch preinstalled; check the tag still exists on Docker Hub.
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /worker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download both models at build time so a cold start does not wait for Hugging Face.
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-m3'); CrossEncoder('BAAI/bge-reranker-v2-m3')"

COPY handler.py .
CMD ["python", "-u", "handler.py"]
