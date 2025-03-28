import logging
import os
import sys
import uvicorn
from fastapi import FastAPI

# Add the parent directory to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.prompt import create_rag_chain

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Family Menu Suggestion System")

@app.get("/")
async def root():
    return {"message": "Welcome to Family Menu Suggestion System API"}

@app.get("/query")
async def query(question: str):
    try:
        logger.info(f"Received query: {question}")
        rag_chain = create_rag_chain()
        response = rag_chain.invoke({"input": question})
        return {"answer": response['answer']}
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return {"error": str(e)}

def main():
    try:
        logger.info("Initializing RAG chain...")
        rag_chain = create_rag_chain()
        logger.info("RAG chain initialized successfully.")

        # Ví dụ truy vấn
        query = "Chế độ ăn uống lành mạnh là gì?"
        response = rag_chain.invoke({"input": query})
        logger.info(f"Response to '{query}': {response['answer']}")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Nếu muốn chạy ví dụ truy vấn trực tiếp, bỏ comment dòng dưới
    # main()
    
    # Khởi động ứng dụng FastAPI
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)