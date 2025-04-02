import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    logger.error("PINECONE_API_KEY not found in .env file.")
    raise ValueError("PINECONE_API_KEY not found in .env file.")

# Get index name from environment variables
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "chatbot")
logger.info(f"Using Pinecone index: {PINECONE_INDEX_NAME}")

# Initialize Pinecone client globally
pc = Pinecone(api_key=PINECONE_API_KEY)

def load_pdf_file(data_path):
    """Load PDF files from a directory."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Directory not found: '{data_path}'")
    if not os.path.isdir(data_path):
        raise ValueError(f"Expected directory, got file: '{data_path}'")
    loader = DirectoryLoader(data_path, glob="*.pdf", loader_cls=PyPDFLoader)
    try:
        documents = loader.load()
        return documents
    except Exception as e:
        raise Exception(f"Error loading PDF files: {str(e)}")

def text_split(extracted_data):
    """Split documents into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks

def download_hugging_face_embeddings():
    """Download and return HuggingFace embeddings."""
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    return embeddings

def initialize_pinecone(index_name=None):
    """Initialize and create Pinecone index if it doesn't exist."""
    try:
        logger.info("Initializing Pinecone client...")
        # Use environment variable if index_name is not provided
        if index_name is None:
            index_name = PINECONE_INDEX_NAME
        
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=768,  # Dimension for multilingual model
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            logger.info(f"Created Pinecone index: {index_name}")
        return pc, index_name
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {str(e)}")
        raise

def load_documents_to_pinecone():
    """Load documents and upsert to Pinecone."""
    try:       
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_directory = os.path.join(current_dir, 'Data')
        
        # Kiểm tra xem index đã tồn tại chưa
        _, index_name = initialize_pinecone()
        
        # Kiểm tra xem index đã chứa dữ liệu chưa
        # Sử dụng một simple query để kiểm tra
        try:
            index = pc.Index(index_name)
            response = index.query(vector=[0] * 768, top_k=1, include_metadata=False)
            
            # Nếu có ít nhất một kết quả, tức là index đã có dữ liệu
            if response.matches and len(response.matches) > 0:
                logger.info("Index already contains data. Skipping document loading...")
                embeddings = download_hugging_face_embeddings()
                return LangchainPinecone.from_existing_index(index_name, embeddings)
        except Exception as e:
            logger.warning(f"Error checking index content, will proceed with loading: {str(e)}")
        
        # Nếu không có dữ liệu hoặc xảy ra lỗi, tiếp tục quá trình tải dữ liệu
        logger.info(f"Loading documents from {data_directory}")
        logger.info(f"Files in Data directory: {os.listdir(data_directory)}")
        
        extracted_data = load_pdf_file(data_directory)
        text_chunks = text_split(extracted_data)
        logger.info(f"Length of Text Chunks: {len(text_chunks)}")

        embeddings = download_hugging_face_embeddings()

        docsearch = LangchainPinecone.from_documents(
            documents=text_chunks,
            embedding=embeddings,
            index_name=index_name
        )
        logger.info("Data successfully upserted to Pinecone index.")
        return docsearch
    except Exception as e:
        logger.error(f"Error loading documents to Pinecone: {str(e)}")
        raise