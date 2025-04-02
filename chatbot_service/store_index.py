import os
import logging
from typing import List, Optional, Set
from langchain_core.documents import Document
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
# Import helper functions
from src.helper import (
    load_pdf_file,  # Hàm để đọc file PDF
    text_split,  # Hàm để chia nhỏ văn bản thành các đoạn
    download_hugging_face_embeddings,  # Hàm để tải model embedding từ Hugging Face
    initialize_pinecone  # Hàm để khởi tạo Pinecone
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # Lấy API key từ file .env
if not PINECONE_API_KEY:
    logger.error("PINECONE_API_KEY not found in .env file.")
    raise ValueError("PINECONE_API_KEY not found in .env file.")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)  # Khởi tạo client Pinecone


def get_existing_document_ids(index_name: str) -> Set[str]:
    """
    Lấy ID của các tài liệu đã có trong Pinecone index.
    
    Args:
        index_name: Tên của Pinecone index
        
    Returns:
        Tập hợp các ID tài liệu đã có trong index
    """
    try:
        # Lấy index từ Pinecone
        index = pc.Index(index_name)
        
        # Truy vấn tất cả vector ID (giới hạn 10000 cho mục đích thực tế)
        # Thay đổi kích thước vector từ 384 thành 768
        response = index.query(vector=[0] * 768, top_k=10000, include_metadata=False)
        
        # Trích xuất ID
        existing_ids = {match.id for match in response.matches}
        logger.info(f"Found {len(existing_ids)} existing documents in the index")
        return existing_ids
    except Exception as e:
        logger.error(f"Error getting existing document IDs: {str(e)}")
        return set()


def create_or_update_index(data_path: str, index_name: str = "chatbot", update_only: bool = False) -> LangchainPinecone:
    """
    Tạo một Pinecone index mới hoặc cập nhật index đã tồn tại với các tài liệu mới.
    
    Args:
        data_path: Đường dẫn đến thư mục chứa các file PDF
        index_name: Tên của Pinecone index
        update_only: Nếu True, chỉ cập nhật index với tài liệu mới, không tạo lại
        
    Returns:
        LangchainPinecone vector store
    """
    try:
        # Khởi tạo Pinecone
        _, index_name = initialize_pinecone(index_name)
        
        # Đọc và xử lý tài liệu
        logger.info(f"Loading documents from {data_path}")
        extracted_data = load_pdf_file(data_path)
        text_chunks = text_split(extracted_data)
        logger.info(f"Processed {len(text_chunks)} text chunks from documents")
        
        # Lấy model embedding
        embeddings = download_hugging_face_embeddings()
        
        # Nếu đang cập nhật, lấy ID tài liệu hiện có để tránh trùng lặp
        if update_only and index_name in pc.list_indexes().names():
            existing_ids = get_existing_document_ids(index_name)
            
            # Lọc ra các tài liệu chưa có trong index
            new_chunks = []
            for chunk in text_chunks:
                # Tạo ID đơn giản dựa trên hash nội dung
                doc_id = str(hash(chunk.page_content))
                if doc_id not in existing_ids:
                    if chunk.metadata is None:
                        chunk.metadata = {}
                    chunk.metadata["doc_id"] = doc_id
                    new_chunks.append(chunk)
            
            logger.info(f"Found {len(new_chunks)} new chunks to add to the index")
            
            if not new_chunks:
                logger.info("No new documents to add to the index")
                return LangchainPinecone.from_existing_index(index_name, embeddings)
            
            # Thêm tài liệu mới vào index hiện có
            docsearch = LangchainPinecone.from_existing_index(index_name, embeddings)
            docsearch.add_documents(new_chunks)
            logger.info(f"Successfully added {len(new_chunks)} new chunks to the index")
        else:
            # Tạo index mới hoặc thay thế index cũ
            docsearch = LangchainPinecone.from_documents(
                documents=text_chunks,
                embedding=embeddings,
                index_name=index_name
            )
            logger.info(f"Created new index with {len(text_chunks)} chunks")
        
        return docsearch
    
    except Exception as e:
        logger.error(f"Error in create_or_update_index: {str(e)}")
        raise


def update_index_with_new_data(data_path: str, index_name: str = "chatbot") -> LangchainPinecone:
    """
    Update an existing Pinecone index with new documents.
    
    Args:
        data_path: Path to directory containing new PDF files
        index_name: Name of the Pinecone index
        
    Returns:
        Updated LangchainPinecone vector store
    """
    # Cập nhật index với dữ liệu mới
    return create_or_update_index(data_path, index_name, update_only=True)


def list_indexed_files(index_name: str = "chatbot") -> List[str]:
    """
    List files that have been indexed in Pinecone.
    
    Args:
        index_name: Name of the Pinecone index
        
    Returns:
        List of filenames that have been indexed
    """
    try:
        # Lấy index từ Pinecone
        index = pc.Index(index_name)
        
        # Truy vấn với metadata
        response = index.query(
            # Thay đổi kích thước vector từ 384 thành 768
            vector=[0] * 768,  # Vector giả
            top_k=100,  # Giới hạn kết quả
            include_metadata=True
        )
        
        # Trích xuất tên file duy nhất từ metadata
        filenames = set()
        for match in response.matches:
            if hasattr(match, 'metadata') and match.metadata:
                if 'source' in match.metadata:
                    filenames.add(match.metadata['source'])
        
        return list(filenames)
    except Exception as e:
        logger.error(f"Error listing indexed files: {str(e)}")
        return []


if __name__ == "__main__":
    # Sửa đường dẫn đến thư mục Data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(current_dir, 'Data')
    
    # Cập nhật index với dữ liệu mới
    docsearch = update_index_with_new_data(data_directory)
    
    # Liệt kê các file đã được index
    indexed_files = list_indexed_files()
    logger.info(f"Indexed files: {indexed_files}")