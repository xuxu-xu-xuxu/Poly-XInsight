from backend.services.ingestion import init_es, init_milvus


def test_init_es_creates_index():
    es = init_es()
    assert es.indices.exists(index="papers")


def test_init_milvus_creates_collection():
    from backend.services.ingestion import COLLECTION_NAME
    col = init_milvus()
    assert col.name == COLLECTION_NAME
