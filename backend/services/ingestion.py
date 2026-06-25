from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from elasticsearch import Elasticsearch
from backend.config import get_settings
from backend.services.embedding import embed_sentences
from backend.services.chunking import chunk_sections
from backend.services.pdf_service import parse_pdf

COLLECTION_NAME = "literature_chunks"
DIM = 1024
MILVUS_TEXT_MAX_LENGTH = 4096


def truncate_for_milvus(text: str, max_bytes: int = MILVUS_TEXT_MAX_LENGTH) -> str:
    encoded = (text or "").encode("utf-8")
    if len(encoded) <= max_bytes:
        return text or ""
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def init_milvus():
    settings = get_settings()
    connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)
    if utility.has_collection(COLLECTION_NAME):
        col = Collection(COLLECTION_NAME)
        col.load()
        return col
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="heading", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
    ]
    schema = CollectionSchema(fields, description="Literature chunks")
    collection = Collection(COLLECTION_NAME, schema)
    index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    collection.create_index("embedding", index_params)
    collection.load()
    return collection


def init_es() -> Elasticsearch:
    settings = get_settings()
    es = Elasticsearch(
        settings.es_host,
        basic_auth=(settings.es_user, settings.es_password),
        verify_certs=False,
    )
    if not es.indices.exists(index="papers"):
        es.indices.create(index="papers", body={
            "mappings": {
                "properties": {
                    "paper_id": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "abstract": {"type": "text", "analyzer": "standard"},
                    "full_text": {"type": "text", "analyzer": "standard"},
                    "authors": {"type": "text"},
                    "year": {"type": "integer"},
                    "journal": {"type": "text"},
                }
            }
        })
    if not es.indices.exists(index="paper_chunks"):
        es.indices.create(index="paper_chunks", body={
            "mappings": {
                "properties": {
                    "paper_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "section": {"type": "keyword"},
                    "chunk_type": {"type": "keyword"},
                    "heading": {"type": "text", "analyzer": "standard"},
                    "text": {"type": "text", "analyzer": "standard"},
                    "token_count": {"type": "integer"},
                }
            }
        })
    return es


async def ingest_pdf(file_path: str) -> dict:
    parsed = parse_pdf(file_path)
    paper_id = parsed["paper_id"]
    meta = parsed["metadata"]
    sections = parsed["sections"]

    settings = get_settings()
    chunks = chunk_sections(sections, settings.chunk_size, settings.chunk_overlap)
    texts = [c["text"] for c in chunks]
    emb_result = await embed_sentences(texts)

    collection = init_milvus()
    entities = []
    for i, (chunk, emb) in enumerate(zip(chunks, emb_result["dense_embeddings"])):
        entities.append({
            "id": f"{paper_id}_{i}",
            "paper_id": paper_id,
            "chunk_index": i,
            "text": truncate_for_milvus(chunk["text"]),
            "heading": chunk["heading"],
            "embedding": emb,
        })
    collection.insert(entities)
    collection.flush()

    es = init_es()
    es.index(index="papers", id=paper_id, document={
        "paper_id": paper_id,
        "title": meta.get("title", ""),
        "authors": meta.get("authors", ""),
        "abstract": meta.get("abstract") or parsed["full_text"][:1000],
        "full_text": parsed["full_text"],
        "year": meta.get("year"),
        "journal": meta.get("journal") or "",
    })
    for i, chunk in enumerate(chunks):
        chunk_id = f"{paper_id}_{i}"
        es.index(index="paper_chunks", id=chunk_id, document={
            "paper_id": paper_id,
            "chunk_id": chunk_id,
            "chunk_index": i,
            "section": chunk.get("section", chunk.get("heading", "")),
            "chunk_type": chunk.get("chunk_type", "body"),
            "heading": chunk.get("heading", ""),
            "text": chunk.get("text", ""),
            "token_count": chunk.get("token_count", 0),
        })

    return {
        "paper_id": paper_id,
        "title": meta.get("title", ""),
        "authors": meta.get("authors"),
        "year": meta.get("year"),
        "journal": meta.get("journal"),
        "abstract": meta.get("abstract"),
        "chunk_count": len(chunks),
        "full_text": parsed["full_text"],
        "tables": parsed.get("tables", []),
    }


def delete_paper_indexes(paper_id: str) -> None:
    collection = init_milvus()
    collection.delete(expr=f'paper_id == "{paper_id}"')
    collection.flush()

    es = init_es()
    es.delete_by_query(index="papers", body={"query": {"term": {"paper_id": paper_id}}}, refresh=True)
    es.delete_by_query(index="paper_chunks", body={"query": {"term": {"paper_id": paper_id}}}, refresh=True)


async def reindex_pdf(file_path: str, paper_id: str | None = None) -> dict:
    target_paper_id = paper_id or parse_pdf(file_path)["paper_id"]
    delete_paper_indexes(target_paper_id)
    return await ingest_pdf(file_path)
