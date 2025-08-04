# app/processors.py
import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List, Dict
import requests
import tempfile

class DocumentProcessor:
    @staticmethod
    def load_document(url: str) -> List[str]:
        """Handles PDF, DOCX, and email attachments"""
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            response = requests.get(url)
            tmp.write(response.content)
            
            if url.endswith('.pdf'):
                from PyPDF2 import PdfReader
                reader = PdfReader(tmp.name)
                return [page.extract_text() for page in reader.pages]
            elif url.endswith('.docx'):
                from docx import Document
                doc = Document(tmp.name)
                return [para.text for para in doc.paragraphs]
            else:  # Assume text/email
                return [response.text]

class VectorDBManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def create_index(self, chunks: List[str]):
        return FAISS.from_texts(chunks, self.embeddings)