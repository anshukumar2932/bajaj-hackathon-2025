import os
import time
from typing import List, Dict
import json
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredEmailLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from fastapi import HTTPException
from app.config import Config
from app.utils import logger
import pinecone

class DocumentProcessor:
    @staticmethod
    def load_document(document_url: str):
        """Load document based on file type with error handling"""
        try:
            start_time = time.time()
            logger.info(f"Loading document from {document_url}")
            
            if document_url.endswith('.pdf'):
                loader = PyPDFLoader(document_url)
            elif document_url.endswith('.docx'):
                loader = Docx2txtLoader(document_url)
            elif document_url.endswith('.eml') or document_url.endswith('.msg'):
                loader = UnstructuredEmailLoader(document_url)
            else:
                raise ValueError("Unsupported file format")
            
            documents = loader.load()
            logger.info(f"Document loaded in {time.time() - start_time:.2f}s")
            return documents
        
        except Exception as e:
            logger.error(f"Document loading failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Document loading error: {str(e)}")

    @staticmethod
    def chunk_documents(documents):
        """Split documents into manageable chunks with metadata preservation"""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=Config.CHUNK_SIZE,
                chunk_overlap=Config.CHUNK_OVERLAP,
                add_start_index=True
            )
            chunks = text_splitter.split_documents(documents)
            
            # Enhance metadata for Vercel compatibility
            for chunk in chunks:
                chunk.metadata['source'] = chunk.metadata.get('source', 'unknown')
                chunk.metadata['page'] = chunk.metadata.get('page', 0)
                # Remove any non-serializable metadata
                for key in list(chunk.metadata.keys()):
                    if not isinstance(chunk.metadata[key], (str, int, float, bool)):
                        del chunk.metadata[key]
            
            return chunks
        except Exception as e:
            logger.error(f"Document chunking failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Document processing error: {str(e)}")

class VectorStoreManager:
    def __init__(self):
        try:
            self.embeddings = OpenAIEmbeddings(
                model=Config.EMBEDDING_MODEL,
                openai_api_key=Config.OPENAI_API_KEY
            )
            # Initialize both FAISS and Pinecone
            self.vector_store = None
            self.pinecone_index = None
            if Config.PINECONE_API_KEY and Config.PINECONE_ENV:
                pinecone.init(
                    api_key=Config.PINECONE_API_KEY,
                    environment=Config.PINECONE_ENV
                )
        except Exception as e:
            logger.error(f"Vector store initialization failed: {str(e)}")
            raise

    def create_vector_store(self, chunks, use_pinecone=False):
        """Create vector store from document chunks"""
        try:
            start_time = time.time()
            
            if use_pinecone and Config.PINECONE_API_KEY:
                index_name = "hackrx-documents"
                if index_name not in pinecone.list_indexes():
                    pinecone.create_index(index_name, dimension=1536)
                
                self.pinecone_index = Pinecone.from_documents(
                    chunks, 
                    self.embeddings, 
                    index_name=index_name
                )
                logger.info(f"Pinecone index created in {time.time() - start_time:.2f}s")
            else:
                # Default to FAISS for Vercel compatibility
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)
                logger.info(f"FAISS index created in {time.time() - start_time:.2f}s")
            
            return self.vector_store if not use_pinecone else self.pinecone_index
        except Exception as e:
            logger.error(f"Vector store creation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Vector store error: {str(e)}")

    def similarity_search(self, query, k=5, use_pinecone=False):
        """Perform semantic search on stored vectors"""
        try:
            start_time = time.time()
            
            if use_pinecone and self.pinecone_index:
                results = self.pinecone_index.similarity_search(query, k=k)
            else:
                if not self.vector_store:
                    raise ValueError("Vector store not initialized")
                results = self.vector_store.similarity_search(query, k=k)
            
            logger.info(f"Similarity search completed in {time.time() - start_time:.2f}s")
            return results
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

class QueryProcessor:
    def __init__(self):
        try:
            self.llm = ChatOpenAI(
                model=Config.LLM_MODEL, 
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                openai_api_key=Config.OPENAI_API_KEY
            )
            self.prompt_template = self._create_prompt_template()
            self.domain_specific_templates = self._create_domain_templates()
        except Exception as e:
            logger.error(f"Query processor initialization failed: {str(e)}")
            raise

    def _create_prompt_template(self):
        """Create custom prompt template optimized for Vercel execution"""
        template = """
        You are an expert document analyst for HackRx 6.0. Analyze the context and answer precisely.

        Context: {context}

        Question: {question}

        Respond in this JSON format:
        {{
            "answer": "Direct answer",
            "conditions": ["List", "of", "conditions"],
            "references": [{{"page": "X", "section": "Y", "excerpt": "Z"}}],
            "rationale": "Explanation",
            "confidence": "High/Medium/Low"
        }}

        Guidelines:
        - Be factual and concise
        - Only use provided context
        - Include all relevant conditions
        - For legal/insurance terms, provide exact definitions
        """
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

    def _create_domain_templates(self) -> Dict[str, PromptTemplate]:
        """Create domain-specific prompt templates for HackRx"""
        domains = {
            "insurance": """
            Insurance Policy Analysis for HackRx:
            Focus on: coverage, exclusions, waiting periods, claim procedures.
            Highlight sub-limits, co-payments, special conditions.
            """,
            "legal": """
            Legal Document Analysis for HackRx:
            Focus on: obligations, rights, termination clauses, liabilities.
            Highlight defined terms, jurisdictional aspects.
            """,
            "hr": """
            HR Policy Analysis for HackRx:
            Focus on: employee benefits, leave policies, code of conduct.
            Highlight eligibility criteria, probation periods.
            """,
            "compliance": """
            Compliance Document Analysis for HackRx:
            Focus on: regulatory requirements, reporting obligations.
            Highlight deadlines, penalties, certification requirements.
            """
        }
        return {domain: PromptTemplate.from_template(template) for domain, template in domains.items()}

    def _determine_domain(self, question: str) -> str:
        """Determine domain for HackRx question optimization"""
        question_lower = question.lower()
        if any(term in question_lower for term in ["policy", "cover", "premium", "claim"]):
            return "insurance"
        elif any(term in question_lower for term in ["clause", "contract", "agreement"]):
            return "legal"
        elif any(term in question_lower for term in ["employee", "leave", "benefit"]):
            return "hr"
        elif any(term in question_lower for term in ["compliance", "regulation", "audit"]):
            return "compliance"
        return "general"

    def process_query(self, query: str, relevant_docs, domain: str = None) -> Dict:
        """Process query with LLM using retrieved context"""
        try:
            start_time = time.time()
            
            if not domain:
                domain = self._determine_domain(query)
            
            prompt_template = self.domain_specific_templates.get(domain, self.prompt_template)
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=relevant_docs,
                chain_type_kwargs={"prompt": prompt_template},
                return_source_documents=True
            )
            
            result = qa_chain({"query": query})
            processing_time = time.time() - start_time
            
            if processing_time > Config.MAX_RESPONSE_TIME * 0.8:
                logger.warning(f"Query nearing timeout: {processing_time:.2f}s")
            
            return {
                "result": result["result"],
                "processing_time": processing_time,
                "source_documents": result["source_documents"]
            }
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")