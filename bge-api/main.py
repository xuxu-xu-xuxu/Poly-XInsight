from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from FlagEmbedding import BGEM3FlagModel
import torch
import os

app = FastAPI(title="BGE-M3 Embedding Service")
model = None

MODEL_PATH = os.environ.get("MODEL_PATH", "BAAI/bge-m3")
USE_FP16 = os.environ.get("BGE_USE_FP16", "auto").lower()
MODELSCOPE_CACHE = "/root/.cache/modelscope"


def _download_from_modelscope(model_id: str) -> str:
    """Download model from ModelScope, return local path."""
    from modelscope import snapshot_download
    print(f"Downloading {model_id} from ModelScope...")
    local_dir = snapshot_download(model_id, cache_dir=MODELSCOPE_CACHE)
    print(f"Model downloaded to: {local_dir}")
    return local_dir


@app.on_event("startup")
async def load_model():
    global model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = device == "cuda" if USE_FP16 == "auto" else USE_FP16 in {"1", "true", "yes", "on"}

    # Try ModelScope first for Chinese network compatibility
    model_path = MODEL_PATH
    if not os.path.isdir(MODEL_PATH) and "/" in MODEL_PATH:
        try:
            model_path = _download_from_modelscope(MODEL_PATH)
            print(f"Model loaded from ModelScope: {model_path}")
        except Exception as e:
            print(f"ModelScope download failed ({e}), falling back to HuggingFace...")
            # Fall back to original path (HuggingFace)
            model_path = MODEL_PATH

    model = BGEM3FlagModel(model_path, use_fp16=use_fp16, device=device)

class EmbeddingRequest(BaseModel):
    sentences: List[str]
    max_length: int = 8192
    batch_size: int = 12
    return_sparse: bool = False

@app.post("/embed")
async def get_embeddings(request: EmbeddingRequest):
    import torch
    with torch.inference_mode():
        output = model.encode(
            request.sentences,
            batch_size=request.batch_size,
            max_length=request.max_length,
            return_dense=True,
            return_sparse=request.return_sparse
        )
    result = {"dense_embeddings": output["dense_vecs"].tolist()}
    if request.return_sparse:
        result["sparse_embeddings"] = output["lexical_weights"]
    return result

class RerankRequest(BaseModel):
    query: str
    documents: List[str]

@app.post("/rerank")
async def rerank_documents(request: RerankRequest):
    pairs = [[request.query, doc] for doc in request.documents]
    result = model.compute_score(pairs)
    # use combined colbert+sparse+dense score for best accuracy
    scores = result.get("colbert+sparse+dense", result["dense"])
    ranked = sorted(
        [{"index": i, "score": float(s)} for i, s in enumerate(scores)],
        key=lambda x: x["score"], reverse=True
    )
    return {"ranked": ranked}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
