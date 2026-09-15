###Tech Stack
* **LLM & Embeddings:** OpenAI(`gpt-4o-mini`)
* **Vector Database:** Qdrant
* **Orchestration & Workflow:** Inngest
* **Backend:** FastAPI
* **Frontend UI:** Streamlit


### 1. Obtain the Project
* **Via Git:**
  ```bash
  git clone <YOUR_REPOSITORY_URL>
  cd <REPOSITORY_FOLDER>
* **Without Git:**
  Download ZIP on the repository page.
  Extract the archive to a local folder.
  Open your terminal (PowerShell or Command Prompt) inside the extracted project folder.

### 2. Environment Configuration
Create a .env file in the root directory of the project with the following variables:
OPENAI_API_KEY=your_openai_api_key_here
INNGEST_EVENT_KEY=local_test_key

### 3. Build and Run via Docker Compose
```bash
docker compose up --build
```
### Service Access
*Streamlit UI (Guest Assistant): http://localhost:8501
*Inngest Dashboard (Workflow Runs & Events): http://localhost:8288
*Qdrant Dashboard (Vector Collections): http://localhost:6333/dashboard

By default, the project is configured with a hotel concierge guide located in the `docs/` folder (`docs/grand_horizon_hotel_guest_guide_en.pdf`). 

To use your own document:
1. Place your PDF file into the `docs/` folder.
2. Open `main.py` and update the collection settings at the top of the file:
   ```python
   collection = "your_collection_name" 
   source_id = "your_knowledge_base"    
3. The in `main.py` update the `pdf_path` variable inside the lifespan function:
   ```python
   pdf_path = "docs/your_custom_document.pdf"
