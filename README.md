# Policybot

A standalone, local policy document chatbot, inspired by the policy Q&A flow in effi-rag. Upload a policy and ask questions, with cited excerpts. No EffiHR integration, AWS credentials, Redis, Docker, Postgres, cloud APIs, or frontend build tools.

## Run on Windows

1. Install Python 3.11+ and [Ollama](https://ollama.com/download/windows).
2. Double-click `setup.bat` once. This installs Python packages and downloads `qwen2.5:3b` (chat, roughly 2 GB) and `nomic-embed-text` (embeddings, roughly 274 MB). Internet is needed for setup only.
3. Double-click `start.bat`. It starts a dedicated local model server and opens your browser at **http://127.0.0.1:8765**. Keep the terminal open; Ctrl+C stops the web app. The local model server can remain running and is reused on the next launch.
4. Upload a PDF, DOCX, TXT, or Markdown policy (up to 20 MB). Select the policy, then ask questions. Expand the source cards to read supporting passages.

After setup finishes, use `start.bat` to launch the app. Models are downloaded during setup and are not included in this repository.

`requirements-lock.txt` records the package versions tested for this build; Windows setup prefers this file when present.

Try `examples/sample-policy.txt`: "How much annual leave do I get?", "Can unused leave carry forward?", "What about sick leave?", and "What is the salary increment?" The last question should report missing policy information.

## What runs locally

- FastAPI serves the API and a plain HTML/CSS/JavaScript frontend. No npm or CDN requests.
- PDF/DOCX/text extraction → overlapping, page-aware chunks → Ollama embeddings.
- SQLite stores extracted passages, vectors, and per-document chats in `data/policybot.sqlite3`. Original files are not retained.
- Retrieval combines cosine similarity and BM25 with reciprocal rank fusion. Only passages from the selected policy enter the model context.
- Ollama generates an answer using the retrieved passages and recent conversation. Returned source IDs are checked against the provided excerpts. Source excerpts remain visible for review; citations are not proof that every model claim is correct.
- All application model requests go to a dedicated Ollama server at `127.0.0.1:11435`; no API keys. Models live in this project's `models/` directory. Ollama's API reference: [chat](https://docs.ollama.com/api/chat), [embeddings](https://docs.ollama.com/api/embed).

Documents and chat history persist across restarts. Delete a policy with its × button to remove its passages and chat; Clear chat keeps the policy. SQLite may retain deleted bytes until vacuuming, so deletion is not secure erasure.

Keep the project in a local folder with at least 4 GB of free disk space for models, dependencies, and working files. Source files, the Python environment, models, policy text, and chats stay inside the project folder. Setup uses project-local temporary and package-cache directories.

## Other systems / manual setup

```sh
python -m venv .venv
# Activate the environment (Windows: .venv\Scripts\activate)
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python local_models.py --pull
python run.py
```

Optional environment variables: `POLICYBOT_PORT` (default 8765), `POLICYBOT_DATA` (storage directory), `POLICYBOT_CHAT_MODEL`, `POLICYBOT_EMBED_MODEL`, and `POLICYBOT_NO_BROWSER=1`. If you change the embedding model, delete and re-upload old policies. To install a different model, set `OLLAMA_HOST=127.0.0.1:11435` and use `ollama pull MODEL` while Policybot's local server is running. Moving the folder requires restarting this dedicated server so it uses the new model path.

## Limits

This is a single-user desktop app bound to loopback, without authentication. Scanned PDFs need OCR before upload; password-protected PDFs are rejected. Documents are limited to one million extracted characters. DOCX tables are included; PDF extraction may lose complex table formatting. Local answer speed depends on hardware, and first requests may take longer as models load. Review passages when precision matters. The prompt asks the model to decline unsupported questions and ignore instructions embedded in policy text, but a small local model can still make mistakes.

## Tests

```sh
python -m pip install pytest
python -m pytest tests -q
```

Tests isolate storage and mock model calls, covering parsing, overlapping chunks, retrieval, policy isolation, failed-upload rollback, persistence, citation validation, and deletion. API explorer: http://127.0.0.1:8765/api/docs.

Optional frontend checks (Node installed): `node tests/test_frontend.cjs`. These check UI state and safe source rendering using the real frontend script; they do not replace browser layout testing.

Optional real-model check: `.venv\Scripts\python.exe tests/live_smoke.py`. It uses temporary project-local storage and real Ollama models to test policy facts, a follow-up, an unsupported salary question, and isolation between two documents.
