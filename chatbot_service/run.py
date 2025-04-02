import logging
import os
import sys
import uvicorn
from fastapi import FastAPI
import argparse

# Add the parent directory to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.prompt import create_rag_chain
from store_index import create_or_update_index, update_index_with_new_data

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
    # Thiết lập argument parser
    parser = argparse.ArgumentParser(description="Family Menu Suggestion System")
    parser.add_argument("--create-index", action="store_true", help="Create or update Pinecone index")
    parser.add_argument("--force-create", action="store_true", help="Force create new Pinecone index")
    parser.add_argument("--example", action="store_true", help="Run example query")
    args = parser.parse_args()
    
    # Nếu cần tạo index
    if args.create_index:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_directory = os.path.join(current_dir, 'Data')
        logger.info("Creating/updating Pinecone index...")
        
        if args.force_create:
            # Nếu force create, tạo mới index với update_only=False
            create_or_update_index(data_directory, update_only=False)
            logger.info("Successfully created new index")
        else:
            # Nếu không, chỉ cập nhật index với dữ liệu mới
            update_index_with_new_data(data_directory)
            logger.info("Successfully updated index with new data")
        sys.exit(0)
    
    # Nếu muốn chạy ví dụ truy vấn
    if args.example:
        main()
        sys.exit(0)
    
    # Khởi động ứng dụng FastAPI
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)