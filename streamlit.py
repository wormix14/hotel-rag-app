import inngest
import streamlit as st
import asyncio
import requests
import time
from dotenv import load_dotenv
import os


load_dotenv()

inngest_base = os.getenv("INNGEST_BASE_URL", "http://127.0.0.1:8288")
inngest_client = inngest.Inngest(app_id="rag_app", is_production=False,event_api_base_url=inngest_base)

def inngest_api_base():
    return f"{inngest_base}/v1"

async def send_event(question: str):
    response = await inngest_client.send(
    inngest.Event(
        name="rag/query_pdf_ai",
        data={
            "question":question
        }
    )
)
    return response[0]

def fetch_runs(event_id:str) -> list[dict]:
    url = f"{inngest_api_base()}/events/{event_id}/runs"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()  
    return data.get("data", [])

def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status

            
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run failed with status: {status}")
                
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


st.title("🤖 AI Concierge RAG")

# Создаем форму для ввода вопроса
with st.form("rag_form"):
    question = st.text_input("Enter your question:")
    submitted = st.form_submit_button("Ask")

if submitted and question.strip():
    with st.spinner("processing your question..."):
        try:
            # 1. Отправляем событие в Inngest и получаем event_id (через asyncio.run, так как Streamlit синхронный)
            event_id = asyncio.run(send_event(question.strip()))
            
            # 2. Опрашиваем Inngest до тех пор, пока задача не завершится и не вернет output
            output = wait_for_run_output(event_id)
            
            # 3. Достаем нужные поля из ответа воркера
            answer = output.get("answer", "Answer not found")
            num_contexts = output.get("num_contexts", 0)

            # 4. Выводим результат на экран
            st.success("Done!")
            st.markdown("### Answer:")
            st.write(answer)
            st.caption(f"(contexts): {num_contexts}")

        except Exception as e:
            import traceback
            st.error(f"Error: {type(e).__name__} - {e}")
            st.code(traceback.format_exc())