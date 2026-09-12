from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import os 

url = os.getenv("QDRANT_URL", "http://localhost:6333")

class QdrantStorage:
    def __init__(self,url=url,collection: str = ..., dim = 3072):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def upsert(self, ids, vectors, payloads):
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(self.collection, points=points)

    def search(self, vector_query, top_k: int = 5):
        results = self.client.query_points(
            collection_name=self.collection,
            query=vector_query,
            with_payload=True,
            limit = top_k)

        contexts = []
        for r in results.points:
            payload = r.payload or {}
            text = payload.get("text")
            if text:
                contexts.append(text)


        return {"contexts": contexts}