# Verification

- 13 backend tests passed: parsing, page locations, chunk overlap, retrieval, upload rollback, citations, persistence, and deletion.
- Frontend script checks passed: initial state, policy selection, safe text rendering, source cards, and send controls.
- Real local-model checks passed: 18 annual leave days, 5-day carry forward with March 31 deadline, 10 sick days, unsupported salary question declined, separate policy returned 27 days without cross-document sources.
- Both models installed inside the project-local `models/` directory; dedicated Ollama server on 127.0.0.1:11435 has cloud features disabled.
- The app served successfully at http://127.0.0.1:8765 during verification. App and model services were stopped afterward. Upload test policies were kept in temporary storage and removed.
- Rendered browser layout was not verified because browser access was denied. Frontend JavaScript and API behavior were checked.

Re-run: .venv\Scripts\python.exe -m pytest tests -q
Frontend: node tests/test_frontend.cjs
Real models: .venv\Scripts\python.exe tests/live_smoke.py
