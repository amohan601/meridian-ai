# Meridian AI — Phase 1

Phase 1 provides a local, non-cloud backend for checking service health and asking questions about uploaded PDF documents. It includes a health-check endpoint, a PDF upload endpoint, an upload-history endpoint, and a document-question endpoint.

PDFs are saved locally, their text is split into chunks, and the chunks are embedded with Google's Gemini embedding model and indexed in a local Chroma database. Answers are generated from retrieved document text using a Gemini chat model. No Google Cloud project or cloud credentials are needed. No separate logger or custom exception configuration is needed to run this phase.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Set up and run locally

Clone the repository and move into the project directory:

```bash
git clone <this-repo>
cd meridian-ai-learner
```

Initialize the project with uv and install its dependencies:

```bash
uv init --bare
uv python pin 3.12
uv add -r requirements.txt
uv sync
```

Create your local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your Gemini API key:

```dotenv
APP_MODE=local
GOOGLE_API_KEY=your-gemini-api-key
```

Start the backend from the project root:

```bash
uv run uvicorn api.main:app --app-dir backend --reload --port 8080
```

Interactive API documentation is available at [http://localhost:8080/docs](http://localhost:8080/docs). The server reads `.env` from the project root even though the application code is in `backend/`.

## Phase 1 endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check that the backend is responding. |
| `POST` | `/api/rag/upload` | Upload one or more PDF files, save the originals, and ingest their text into the vector store. |
| `GET` | See `/docs` | Return upload history for the current backend process. |
| `POST` | `/api/rag/ask` | Ask a question about indexed documents. |

### Health check

```bash
curl http://localhost:8080/api/health
```

The response includes `status: "ok"` and the active mode (`local`).

### Upload PDFs

In `/docs`, select **POST /api/rag/upload**, click **Try it out**, add one or more PDF files under `files`, and execute the request. The endpoint accepts `files: list[UploadFile]`. Non-PDF files are skipped. The response reports each file's status, page count, and indexed chunk count where applicable.

You can also upload a sample PDF with curl:

```bash
curl -X POST http://localhost:8080/api/rag/upload \
  -F "files=@sample_docs/aldermoor_annual_report_fy2024.pdf"
```

Each uploaded original is saved to local document storage, then ingested by extracting and splitting its text and saving chunks to Chroma. The supplied notes use two names for the local PDF folder: `meridian_docs/uploads/` in the learning notes and `.meridian/uploads/` in the existing setup. The existing setup places the local data under `.meridian/` by default, with `.meridian/chroma/` for the Chroma index. Both storage folders are created as needed and ignored by Git. Set `LOCAL_DATA_DIR` in `.env` to choose a different local data root. Uploaded PDFs and the vector index remain after restarting the backend. Scanned image-only PDFs may not contain extractable text to index.

### View upload history

Use the upload-history **GET** route shown in `/docs` to retrieve upload history. Its exact path was not included in the supplied README notes. Each upload is recorded in an in-memory `upload_history` dictionary. The history resets when the backend process restarts; it is not the persistent store for the original PDFs or Chroma index.

### Ask questions about uploaded documents

Use **POST /api/rag/ask** in `/docs` with a JSON body:

```json
{
  "query": "What was Aldermoor Industries' total revenue in FY2024?"
}
```

The response contains an `answer` field. The question endpoint accepts the custom Pydantic `QueryRequest` schema and returns `QueryResponse`.

```bash
curl -X POST http://localhost:8080/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What was Aldermoor Industries total revenue in FY2024?"}'
```

The default retrieval method is `similarity`. An optional `retriever_type` can select `similarity`, `multiquery`, `contextual`, `mmr`, or `hyde`.

## Architecture and file-by-file learning notes

### `data_ingestion`

The ingestion flow prepares uploaded PDFs for semantic search:

1. `PyPDFLoader` loads a PDF into a list of LangChain `Document` objects (`langchain_core.documents.Document`), with page content and metadata.
2. `RecursiveCharacterTextSplitter` (`langchain_text_splitters.RecursiveCharacterTextSplitter`) divides the loaded documents into smaller text chunks.
3. A unique ID is generated for each chunk so individual chunks can be stored and identified in the vector store.
4. The chunk documents and IDs are saved to Chroma.

The Chroma integration is `langchain_chroma.Chroma`, a subclass of LangChain's `langchain_core.vectorstores.VectorStore`. The local vector store uses the `meridian_docs` collection name and the `.meridian/chroma/` directory. Creating it requires an embedding function, collection name, and persistence location.

### `vector_store.py`

This module creates and configures the local Chroma vector store used by ingestion and retrieval. It wires together the `Chroma` implementation, the embedding function returned by `embeddings.py`, the `meridian_docs` collection, and the `.meridian/chroma/` persistence directory. Ingestion adds the chunk documents and their unique IDs to this store; retrieval queries the same store to find relevant document chunks.

### `document_store`

This stores the original uploaded PDF files. The supplied notes identify `meridian_docs/uploads/` as the local upload folder, while the original setup describes `.meridian/uploads/`; verify the configured data path in the implementation if you need the precise on-disk location. These original files are distinct from the chunk documents and embeddings in Chroma. Uploading first saves each file to document storage and then runs ingestion to split and index its text.

### `embeddings.py`

This module creates and returns a `GoogleGenerativeAIEmbeddings` instance from `langchain_google_genai`. Its configuration includes:

- Model: `gemini-embedding-001`
- Google API key, supplied through `GOOGLE_API_KEY`
- Output dimensionality: `768`

The embedding function converts document chunks and search queries into vectors for Chroma storage and retrieval. The API key is required for document embeddings and question answering.

### `llm.py`

This module supplies the chat model used when answering questions from ingested documents. It creates a `ChatGoogleGenerativeAI` instance from `langchain_google_genai`, configured with the model name `gemini-3.8-flash`, the Google API key, and a temperature setting. The model receives a prompt containing retrieved document context and the user's question.

The module also provides `extract_text(content) -> str`. It accepts content that may be plain text or a list of content blocks. For a list, it joins the text from blocks whose type is `text` into one string.

### `retrieval.py`

This is the most involved part of the question-answering flow. It builds the RAG chain in `build_rag_chain` and invokes the chain with the user's question to get an answer.

`build_rag_chain` receives a retriever type. The supported implementations are `similarity`, `multiquery`, `contextual`, `mmr`, and `hyde`. The selected retriever is wrapped with `RunnableLambda` (`langchain_core.runnables.RunnableLambda`), which calls the corresponding retriever implementation with the original question. The retriever returns a list of `Document` objects.

The chain formats the retrieved documents as context: `format_docs` joins each document's metadata source and `page_content`. The original question is passed through as `input`, so the prompt receives two keys:

- `context`: formatted retrieved-document information
- `input`: the original question

A `ChatPromptTemplate` from `langchain_core.prompts` is configured with a system message and a human message. The system prompt tells the model to answer using the provided context; the human message contains `{input}`. The chain then calls the `ChatGoogleGenerativeAI` model from `get_llm()` and uses `StrOutputParser` (`langchain_core.output_parsers.StrOutputParser`) to return the model response as a string.

Conceptually, the LCEL flow is:

```text
{
  "context": build_retriever(retriever_type) | format_docs,
  "input": RunnablePassthrough()
}
| ANSWER_PROMPT
| get_llm()
| StrOutputParser()
```

The endpoint invokes this question-answering flow through `retrieval.py`. Answers are based on retrieved document text, so the uploaded PDF needs extractable text and relevant indexed chunks for a useful response.

### API schemas and endpoints

The upload endpoint receives `files: list[UploadFile]` from FastAPI. It saves each original file to document storage, runs ingestion to split and index its contents, and records each upload in the in-memory `upload_history` dictionary. A separate history endpoint returns those records. The ask endpoint accepts `QueryRequest`, invokes the retrieval chain with the question, and returns a `QueryResponse` containing the answer.

## Local data and configuration

- `GOOGLE_API_KEY` is needed for embeddings and question answering.
- `APP_MODE=local` uses Chroma on disk; Google Cloud services are not used.
- Local uploaded PDFs and the Chroma index persist under the configured local data directory, `.meridian/` by default.
- `LOCAL_DATA_DIR` changes the local data root.
- Upload history is held in memory and resets when the backend process restarts.
- `.venv/` is local and should not be committed.

## Troubleshooting

- **Missing API key:** Add `GOOGLE_API_KEY` to `.env`, then restart the backend.
- **Import error for `api`:** Run the command from the project root and include `--app-dir backend`.
- **No text indexed:** Try a text-based PDF rather than a scanned image PDF.
- **Port 8080 is already in use:** Stop the other process or use a different port, such as `--port 8081`.
- **No useful answer:** Confirm the upload response reports indexed chunks, then ask a question the document text can answer.

## Project layout

```text
backend/
  api/                 FastAPI application and endpoint definitions
  config/              Environment-based settings
  rag/                 PDF ingestion, local vector storage, and question answering
  tests/               Backend tests
sample_docs/           Example PDFs for local testing
requirements.txt       Python dependencies
.env.example           Local environment-variable template
```

The company and example data in the sample documents are fictional.
