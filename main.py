import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from dotenv import load_dotenv
import uuid
import os
from inngest.experimental import ai
from custom_types import RAGSearchResult
from data_loader import load_and_chunk_pdf, embed_text
from vector_db import QdrantStorage
from contextlib import asynccontextmanager


load_dotenv()

inngest_base = os.getenv("INNGEST_BASE_URL", "http://inngest:8288")
collection = "hotel_docs" #define a collection you want to use
source_id = "hotel_knowledge_base" #create a name for source(helps to better create a uuid for elements in db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.results = {}
    pdf_path = "docs/grand_horizon_hotel_guest_guide_en.pdf" #enter a path to the knowledge
    store = QdrantStorage(collection=collection)

    collection_info = store.client.get_collection(collection_name=store.collection)

    if collection_info.points_count == 0:
        chunks = load_and_chunk_pdf(pdf_path)
        vecs = embed_text(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, name=f"{source_id}: {i}")) for i in range(len(chunks))]
        payloads = [{"text": chunks[i]} for i in range(len(chunks))]
        store.upsert(ids=ids, vectors=vecs, payloads=payloads)
        print(f"Storage ingested for {len(chunks)} elements")
    else:
        print("Storage is already loaded")
    yield
    app.state.results.clear()

app = FastAPI(lifespan=lifespan)

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
    api_base_url=inngest_base,
    event_api_base_url=inngest_base
)

def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        query_vec = embed_text([question])[0]
        store = QdrantStorage(collection=collection)
        found = store.search(vector_query=query_vec, top_k=top_k)
        return RAGSearchResult(contexts=found["contexts"])

def build_inference_payload(question: str, contexts: list[str]):
      context_block = "\n\n".join(f"- {c}" for c in contexts) 
      user_content = (
             "Use the following context to answer the question.\n\n"
             f"Context:\n{context_block}\n\n"
             f"Question: {question}\n"
             "Answer concisely using the context above."
         )
      return {
            "max_tokens": 2048,
            "temperature": 0.2,
            "messages": [
                {"role": "system",
                 "content" : (
                     "You answer questions using only the provided context."
                     "1. If the requested service or amenity is directly available in the context, confirm it and give details. "
                     "2. If the requested service or item is NOT available, do not just say no: analyze the entire provided context "
                     "to find the closest available alternative, substitute, or related service, and proactively suggest it to the guest in a polite, welcoming manner."
                     "Do not mention that your are using some kind of provided context, just smartly response that you do not have some information if needed.")},
                {"role": "user", "content": user_content}
            ]
        }

adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
    )

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"),
)

async def rag_query_pdf_ai(ctx: inngest.Context):
    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 3))

    found = await ctx.step.run(
         "embed-and-search",
         lambda:_search(question=question, top_k=top_k),
         output_type=RAGSearchResult,
        )
    
    body = build_inference_payload(question=question, contexts=found.contexts)
    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body=body,     
    ) 

    answer = res["choices"][0]["message"]["content"].strip()
    result_data = {"answer": answer, "num_contexts": len(found.contexts), "status": "done"}
    app.state.results[ctx.event.id] = result_data
    return result_data

@app.get("/api/results/{event_id}")
async def get_result(event_id:str):
     return app.state.results.get(event_id, {"status": "pending"})
     

inngest.fast_api.serve(
    app,
    inngest_client,
    [rag_query_pdf_ai]
)
