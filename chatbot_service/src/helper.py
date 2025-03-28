import os
from langchain.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
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

def initialize_pinecone(index_name="chatbot"):
    """Initialize and create Pinecone index if it doesn't exist."""
    try:
        logger.info("Initializing Pinecone client...")
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
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        data_directory = os.path.join(current_dir, 'Data')
        
        logger.info(f"Loading documents from {data_directory}")
        logger.info(f"Files in Data directory: {os.listdir(data_directory)}")
        
        extracted_data = load_pdf_file(data_directory)
        text_chunks = text_split(extracted_data)
        logger.info(f"Length of Text Chunks: {len(text_chunks)}")

        embeddings = download_hugging_face_embeddings()
        _, index_name = initialize_pinecone()

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