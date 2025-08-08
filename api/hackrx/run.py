from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List  # Add this import
from app.config import config
from app.processors import DocumentProcessor, VectorDBManager
import google.generativeai as genai

app = FastAPI()

class QueryRequest(BaseModel):
    documents: str  # URL
    questions: List[str]  # Now properly imported

@app.post("/api/v1/hackrx/run")
async def process_query(
    request: QueryRequest,
    authorization: str = Header(...)
): # Authentication
    if authorization != f"Bearer {config.HACKRX_API_KEY}":
        raise HTTPException(status_code=401)
    
    # Document Processing
    processor = DocumentProcessor()
    vector_mgr = VectorDBManager()
    
    # 1. Load and chunk document
    text = processor.load_document(request.documents)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text("\n".join(text))
    
    # 2. Create vector index
    index = vector_mgr.create_index(chunks)
    
    # 3. Process questions
    answers = []
    for question in request.questions:
        # Retrieve relevant chunks
        docs = index.similarity_search(question, k=3)
        context = "\n".join([d.page_content for d in docs])
        
        # Generate response with Gemini
        response = genai.GenerativeModel('Gemini 2.5 Pro').generate_content(
            f"Document Context:\n{context}\n\nQuestion: {question}\n"
            "Answer with: 1) Direct answer 2) Conditions 3) Source excerpt"
        )
        
        answers.append(response.text)
    
    return {"answers": answers}
