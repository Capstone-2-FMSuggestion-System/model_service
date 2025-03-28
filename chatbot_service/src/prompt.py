import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv
import os
import logging
from src.helper import load_documents_to_pinecone

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GOOGLE_API_KEY not found in .env file.")
    raise ValueError("GOOGLE_API_KEY not found in .env file.")

# Cấu hình Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)

from langchain_core.language_models import LLM

class GeminiLLM(LLM):
    model_name: str = "gemini-2.0-flash-lite"
    model: genai.GenerativeModel = None
    
    def __init__(self, model_name="gemini-2.0-flash-lite"): 
        super().__init__()
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
    
    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "gemini"
    
    def _call(self, prompt: str, stop=None, **kwargs):
        """Call the Gemini API and return the output."""
        try:
            response = self.model.generate_content(prompt, generation_config={
                "temperature": 0.7,
                "max_output_tokens": 200,
            })
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error invoking Gemini: {str(e)}")
            return "Tôi xin lỗi, đã có lỗi xảy ra."
            
    async def _acall(self, prompt: str, stop=None, **kwargs):
        """Async call the Gemini API and return the output."""
        # For simplicity, we're using the synchronous version in an async wrapper
        return self._call(prompt, stop, **kwargs)

# Prompt tối ưu cho dinh dưỡng
system_prompt = (
    "Bạn là một chuyên gia dinh dưỡng thân thiện và chuyên nghiệp, luôn trả lời chi tiết, tự nhiên BẰNG TIẾNG VIỆT. "
    "Nhiệm vụ của bạn là tư vấn về dinh dưỡng, thực phẩm, chế độ ăn, sức khỏe, thực đơn, và các vấn đề đặc biệt (dị ứng, trẻ em, phụ nữ mang thai). "
    "Dựa trên dữ liệu được cung cấp dưới đây và lịch sử cuộc trò chuyện, trả lời câu hỏi của người dùng một cách chính xác và tự nhiên. "
    "Nếu không biết câu trả lời, hãy nói 'Xin lỗi, tôi không biết câu trả lời cho câu hỏi này.' "
    "Giữ câu trả lời ngắn gọn, tối đa 3 câu."
    "\n\n"
    "Lịch sử cuộc trò chuyện: {history}\n"
    "Dữ liệu: {context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

def get_retriever():
    """Get or create a Pinecone retriever."""
    try:
        docsearch = load_documents_to_pinecone()
        retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        logger.info("Retriever created successfully.")
        return retriever
    except Exception as e:
        logger.error(f"Error getting retriever: {str(e)}")
        raise

def create_rag_chain(retriever=None):
    """Create a Retrieval-Augmented Generation (RAG) chain."""
    if retriever is None:
        retriever = get_retriever()
    
    llm = GeminiLLM()
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt
    )
    
    # Create a custom retrieval chain that handles the missing history variable
    def _invoke_with_history_handling(inputs):
        # If history is not provided, add an empty string as default
        if "history" not in inputs:
            inputs["history"] = ""
        # Call the original chain
        return question_answer_chain.invoke({"context": retriever.invoke(inputs["input"]), **inputs})
    
    # Create a custom chain object with our handler
    from langchain_core.runnables import RunnablePassthrough
    rag_chain = RunnablePassthrough() | _invoke_with_history_handling
    
    return rag_chain