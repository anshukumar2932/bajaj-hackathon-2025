import os

class Config:
    EMBEDDING_MODEL = "text-embedding-3-large"
    LLM_MODEL = "gpt-4-turbo"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3
    MAX_RESPONSE_TIME = 30  # seconds
    API_KEY = os.getenv("HACKRX_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")