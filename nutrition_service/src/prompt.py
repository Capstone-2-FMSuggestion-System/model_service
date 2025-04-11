from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
import logging
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NutritionPrompt:
    @staticmethod
    def get_nutrition_chat_prompt():
        """Prompt cho tư vấn dinh dưỡng dựa trên kiến thức có sẵn của Mistral."""
        system_prompt = (
            "Bạn là một chuyên gia dinh dưỡng thân thiện và chuyên nghiệp, luôn trả lời chi tiết và tự nhiên BẰNG TIẾNG VIỆT. "
            "Hãy sử dụng kiến thức dinh dưỡng của bạn để tư vấn về chế độ ăn uống, sức khỏe, và các vấn đề đặc biệt. "
            "Khi không chắc chắn, hãy thừa nhận và đề xuất tham khảo thêm ý kiến của bác sĩ hoặc chuyên gia dinh dưỡng. "
            "\n\n"
            "Thông tin về người dùng: {health_info}\n"
            "Lịch sử trò chuyện: {history}\n"
        )
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
    
    @staticmethod
    def get_meal_suggestion_prompt():
        """Prompt cho gợi ý món ăn dựa trên kiến thức có sẵn của Mistral."""
        system_prompt = (
            "Bạn là chuyên gia ẩm thực và dinh dưỡng. Nhiệm vụ của bạn là gợi ý món ăn phù hợp dựa trên thông tin sức khỏe "
            "và sở thích của người dùng. Hãy gợi ý 3 món ăn chi tiết với nguyên liệu cụ thể.\n\n"
            "Thông tin sức khỏe: {health_info}\n"
            "Sở thích: {preferences}\n\n"
            "Trả lời BẰNG TIẾNG VIỆT theo định dạng JSON như sau:\n"
            "```json\n"
            "{\n"
            "  \"analysis\": \"Phân tích ngắn gọn nhu cầu dinh dưỡng\",\n"
            "  \"meals\": [\n"
            "    {\n"
            "      \"name\": \"Tên món ăn\",\n"
            "      \"ingredients\": [\n"
            "        {\"name\": \"Nguyên liệu 1\", \"quantity\": \"100g\"},\n"
            "        {\"name\": \"Nguyên liệu 2\", \"quantity\": \"2 muỗng canh\"}\n"
            "      ],\n"
            "      \"benefits\": \"Lợi ích dinh dưỡng\",\n"
            "      \"preparation\": \"Cách chế biến ngắn gọn\"\n"
            "    }\n"
            "  ],\n"
            "  \"advice\": \"Lời khuyên bổ sung\"\n"
            "}\n"
            "```"
        )
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

def create_chat_chain():
    """Tạo chain xử lý chat dinh dưỡng."""
    try:
        # Khởi tạo Mistral LLM qua Ollama
        model = ChatOllama(
            model="mistral",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7
        )
        
        # Tạo prompt
        prompt = NutritionPrompt.get_nutrition_chat_prompt()
        
        # Tạo chain đơn giản
        chain = prompt | model
        
        return chain
    except Exception as e:
        logger.error(f"Error creating chat chain: {str(e)}")
        raise

def create_meal_suggestion_chain():
    """Tạo chain gợi ý món ăn."""
    try:
        # Khởi tạo Mistral LLM qua Ollama
        model = ChatOllama(
            model="mistral",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7
        )
        
        # Tạo prompt
        prompt = NutritionPrompt.get_meal_suggestion_prompt()
        
        # Tạo chain đơn giản
        chain = prompt | model
        
        return chain
    except Exception as e:
        logger.error(f"Error creating meal suggestion chain: {str(e)}")
        raise

def parse_json_response(response_text):
    """Trích xuất JSON từ phản hồi LLM."""
    try:
        # Tìm và trích xuất JSON
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            json_text = response_text
        
        return json.loads(json_text)
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return {}