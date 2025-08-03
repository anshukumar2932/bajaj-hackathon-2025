import os
import json
import time
from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
from typing import List, Optional
from app.processors import DocumentProcessor, VectorStoreManager, QueryProcessor
from app.config import Config
from app.utils import logger, verify_token

app = FastAPI()

# Models
class DocumentRequest(BaseModel):
    documents: str  # URL to document
    questions: List[str]

class AnswerResponse(BaseModel):
    answers: List[str]
    processing_time: Optional[float]
    success: bool = True
    error: Optional[str]

@app.post("/api/v1/hackrx/run", response_model=AnswerResponse)
async def process_documents(
    request: Request,
    payload: DocumentRequest,
    authorization: str = Header(...)
):
    """Main endpoint for document processing and question answering"""
    try:
        # Verify authentication
        await verify_token(authorization)
        
        start_time = time.time()
        answers = []
        
        # Initialize processors
        doc_processor = DocumentProcessor()
        vector_mgr = VectorStoreManager()
        query_processor = QueryProcessor()
        
        # 1. Load and process document
        raw_docs = doc_processor.load_document(payload.documents)
        chunks = doc_processor.chunk_documents(raw_docs)
        
        # 2. Create vector store (FAISS for Vercel compatibility)
        vector_mgr.create_vector_store(chunks, use_pinecone=False)
        
        # 3. Process each question
        for question in payload.questions:
            try:
                # 4. Retrieve relevant chunks
                relevant_docs = vector_mgr.similarity_search(question)
                
                # 5. Process with LLM
                result = query_processor.process_query(question, relevant_docs)
                
                # 6. Format response
                try:
                    answer_json = json.loads(result["result"])
                    formatted_answer = (
                        f"{answer_json.get('answer', 'No answer found.')}\n\n"
                        f"Conditions: {', '.join(answer_json.get('conditions', ['None']))}\n"
                        f"References: {json.dumps(answer_json.get('references', []), indent=2)}\n"
                        f"Confidence: {answer_json.get('confidence', 'Unknown')}\n"
                        f"Rationale: {answer_json.get('rationale', 'Not provided.')}"
                    )
                except json.JSONDecodeError:
                    formatted_answer = result["result"]
                
                answers.append(formatted_answer)
            except Exception as e:
                logger.error(f"Failed processing question: {question}. Error: {str(e)}")
                answers.append(f"Error processing question: {str(e)}")
        
        total_time = time.time() - start_time
        logger.info(f"Total processing time: {total_time:.2f}s")
        
        return {
            "answers": answers,
            "processing_time": total_time,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e),
                "success": False
            }
        )

@app.get("/api/v1/hackrx/health")
async def health_check():
    """Health check endpoint for platform validation"""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "1.0.0"
    }