from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import hashlib

from google.genai import errors

from gemini import generate_embedding
from vector_store import (
    add_documents,
    document_hash_exists,
    get_documents,
    delete_document
)

from PyPDF2 import PdfReader

from rag import (
    answer_question,
    debug_retrieval,
    debug_rag_prompt
)


# ============================================================
# Request Models
# ============================================================

class ChatRequest(BaseModel):
    message: str


# ============================================================
# File Hash
# ============================================================

def calculate_file_hash(file):
    file.seek(0)

    file_hash = hashlib.sha256()

    while chunk := file.read(8192):
        file_hash.update(chunk)

    file.seek(0)

    return file_hash.hexdigest()


# ============================================================
# Text Chunking
# ============================================================

def chunk_text(text, chunk_size=500, overlap=100):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap

    return chunks


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="AI Knowledge Assistant",
    description="A RAG-based AI Knowledge Assistant using FastAPI, ChromaDB and Gemini.",
    version="1.0.0"
)


# ============================================================
# CORS Configuration
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy"
    }


# ============================================================
# Chat Endpoint
# ============================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    try:

        result = answer_question(request.message)

        return result

    except errors.ClientError as e:

        # ----------------------------------------------------
        # 429 - Quota exceeded
        # ----------------------------------------------------

        if e.code == 429:

            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota has been exceeded. "
                    "Please wait until the quota becomes available "
                    "and try again."
                )
            )

        # ----------------------------------------------------
        # Other Gemini client errors
        # ----------------------------------------------------

        raise HTTPException(
            status_code=500,
            detail="Gemini API request failed."
        )

    except errors.ServerError as e:

        # ----------------------------------------------------
        # 503 / temporary Gemini service problem
        # ----------------------------------------------------

        if e.code == 503:

            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini is temporarily unavailable because "
                    "the model is experiencing high demand. "
                    "Please try again later."
                )
            )

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini service is temporarily unavailable. "
                "Please try again later."
            )
        )

    except Exception as e:

        print(f"Unexpected error in /api/chat: {e}")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the request."
        )


# ============================================================
# Debug Retrieval Endpoint
# ============================================================

@app.post("/api/debug/retrieval")
def debug_retrieval_endpoint(request: ChatRequest):

    try:

        return debug_retrieval(request.message)

    except Exception as e:

        print(f"Retrieval debug error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to perform retrieval debugging."
        )


# ============================================================
# Debug RAG Prompt Endpoint
# ============================================================

@app.post("/api/debug/rag-prompt")
def debug_rag_prompt_endpoint(request: ChatRequest):

    try:

        return debug_rag_prompt(request.message)

    except Exception as e:

        print(f"RAG prompt debug error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate RAG debugging information."
        )


# ============================================================
# List Documents
# ============================================================

@app.get("/api/documents")
def list_documents():

    try:

        documents = get_documents()

        return {
            "total_documents": len(documents),
            "documents": documents
        }

    except Exception as e:

        print(f"Document listing error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve documents."
        )


# ============================================================
# Delete Document
# ============================================================

@app.delete("/api/documents/{filename}")
def delete_document_endpoint(filename: str):

    try:

        deleted = delete_document(filename)

        if not deleted:

            return {
                "filename": filename,
                "status": "not_found"
            }

        return {
            "filename": filename,
            "status": "deleted"
        }

    except Exception as e:

        print(f"Document deletion error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Unable to delete document."
        )


# ============================================================
# Upload PDF Document
# ============================================================

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate file type
    # --------------------------------------------------------

    if file.content_type != "application/pdf":

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    try:

        # ----------------------------------------------------
        # Calculate file hash
        # ----------------------------------------------------

        file_hash = calculate_file_hash(file.file)

        # ----------------------------------------------------
        # Check duplicate document
        # ----------------------------------------------------

        if document_hash_exists(file_hash):

            return {
                "filename": file.filename,
                "status": "already_indexed"
            }

        # ----------------------------------------------------
        # Read PDF
        # ----------------------------------------------------

        pdf = PdfReader(file.file)

        text = ""

        for page in pdf.pages:

            text += page.extract_text() or ""

        # ----------------------------------------------------
        # Check extracted text
        # ----------------------------------------------------

        if not text.strip():

            raise HTTPException(
                status_code=400,
                detail="No extractable text found in the PDF."
            )

        # ----------------------------------------------------
        # Create chunks
        # ----------------------------------------------------

        chunks = chunk_text(text)

        embedded_chunks = []

        # ----------------------------------------------------
        # Generate embeddings
        # ----------------------------------------------------

        for chunk in chunks:

            embedding = generate_embedding(chunk)

            embedded_chunks.append(
                {
                    "text": chunk,
                    "embedding": embedding
                }
            )

        # ----------------------------------------------------
        # Store in ChromaDB
        # ----------------------------------------------------

        add_documents(
            embedded_chunks,
            file.filename,
            file_hash
        )

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "filename": file.filename,
            "chunks_created": len(chunks),
            "status": "indexed"
        }

    except HTTPException:
        raise

    except errors.ClientError as e:

        if e.code == 429:

            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota has been exceeded "
                    "while creating document embeddings."
                )
            )

        raise HTTPException(
            status_code=500,
            detail="Gemini API failed while creating embeddings."
        )

    except errors.ServerError:

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini is temporarily unavailable while "
                "creating document embeddings. Please try again later."
            )
        )

    except Exception as e:

        print(f"Document upload error: {e}")

        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing the PDF."
        )