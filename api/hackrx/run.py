from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/hackrx/health")
async def health_check():
    return {
        "status": "healthy",
        "config": {
            "port": config.PORT,
            "host": config.HOST,
            "gemini_configured": bool(config.GEMINI_API_KEY)
        }
    }

@app.post("/api/v1/hackrx/run")
async def api_handler(request: Request, authorization: str = Header(...)):
    if authorization != f"Bearer {config.HACKRX_API_KEY}":
        raise HTTPException(status_code=401)
    
    payload = await request.json()
    # Your processing logic here
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)