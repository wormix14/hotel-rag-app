import inngest
import streamlit as st
import asyncio
import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()

inngest_base = os.getenv("INNGEST_BASE_URL", "http://inngest:8288")
backend_base = os.getenv("BACKEND_URL", "http://backend:8000")
inngest_client = inngest.Inngest(app_id="rag_app", is_production=False, event_api_base_url=inngest_base)

http_session = requests.Session()

def inngest_api_base():
    return f"{inngest_base}/v1"

async def send_event(question: str):
    response = await inngest_client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": 3  
            }
        )
    )
    return response[0]

def wait_for_fastapi_output(event_id: str, pool_interval_s: float = 0.25, timeout:float = 60.0):
    url=f"{backend_base}/api/results/{event_id}"
    start = time.time()

    while True:
        try:
            res = http_session.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "done":
                    return data
        except requests.RequestException:
            pass

        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for result from FastAPI")

        time.sleep(pool_interval_s)
            
        


st.title("🤖 AI Concierge RAG")

with st.form("rag_form"):
    question = st.text_input("Enter your question:")
    submitted = st.form_submit_button("Ask")

if submitted and question.strip():
    with st.spinner("processing your question..."):
        try:
            t0 = time.time()
            event_id = asyncio.run(send_event(question.strip()))
            t_sent = time.time()
            st.write(f"⏱ Event sent in: {t_sent - t0:.2f}s")
            
            output =  wait_for_fastapi_output(event_id)
            t_done = time.time()
            
            st.write(f"⏱ Polling took: {t_done - t_sent:.2f}s")
            st.write(f"⏱ Total time: {t_done - t0:.2f}s")
            
            answer = output.get("answer", "Answer not found")
            num_contexts = output.get("num_contexts", 0)

            st.success("Done!")
            st.markdown("### Answer:")
            st.write(answer)
            st.caption(f"(contexts): {num_contexts}")

        except Exception as e:
            import traceback
            st.error(f"Error: {type(e).__name__} - {e}")
            st.code(traceback.format_exc())