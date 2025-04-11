import logging
from pinecone import Pinecone, ServerlessSpec
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
# File để xử lý tìm kiếm sản phẩm trong cửa hàng:
# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class ProductMatcher:
    def __init__(self):
        """Initialize ProductMatcher."""
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "products")
        
        # Kiểm tra API key
        if not self.api_key:
            logger.warning("PINECONE_API_KEY not found, using dummy product matching")
            self.dummy_mode = True
        else:
            self.dummy_mode = False
            self._initialize()
    
    def _initialize(self):
        """Initialize Pinecone and embeddings if API key available."""
        if not self.dummy_mode:
            try:
                self.pc = Pinecone(api_key=self.api_key)
                self.embeddings = HuggingFaceEmbeddings(
                    model_name='sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
                )
                
                # Create index if not exists
                if self.index_name not in self.pc.list_indexes().names():
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=768,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1")
                    )
                    logger.info(f"Created Pinecone index: {self.index_name}")
            except Exception as e:
                logger.error(f"Error initializing vector database: {str(e)}")
                self.dummy_mode = True
    
    def match_ingredients_to_products(self, ingredients: List[Dict[str, str]]):
        """Match ingredients to products."""
        if self.dummy_mode:
            return self._dummy_match(ingredients)
        
        # Trong trường hợp bạn đã kết nối Pinecone, code thật ở đây
        # Tương tự như trong artifact product-matching
        pass
    
    def _dummy_match(self, ingredients: List[Dict[str, str]]):
        """Dummy product matching for testing."""
        available = []
        unavailable = []
        
        # Sample store products for testing
        sample_products = {
            "gà": {"id": "p001", "name": "Thịt gà tươi", "price": 75000, 
                  "image_url": "https://example.com/chicken.jpg", 
                  "product_url": "https://example.com/products/chicken"},
            "rau": {"id": "p002", "name": "Rau cải xanh", "price": 15000, 
                   "image_url": "https://example.com/greens.jpg", 
                   "product_url": "https://example.com/products/greens"},
            "tỏi": {"id": "p003", "name": "Tỏi củ", "price": 12000, 
                   "image_url": "https://example.com/garlic.jpg", 
                   "product_url": "https://example.com/products/garlic"},
        }
        
        for ingredient in ingredients:
            name = ingredient.get("name", "").lower()
            
            # Simple keyword matching
            matched = False
            for key, product in sample_products.items():
                if key in name:
                    available.append({
                        "ingredient": ingredient,
                        "product": product
                    })
                    matched = True
                    break
            
            if not matched:
                unavailable.append(ingredient)
        
        return {
            "available": available,
            "unavailable": unavailable
        }
    
    def bulk_process_meals(self, meals_data: List[Dict[str, Any]]):
        """Process all ingredients in a meal list."""
        processed_meals = []
        
        for meal in meals_data:
            meal_name = meal.get("name", "")
            ingredients = meal.get("ingredients", [])
            
            # Match ingredients to products
            ingredients_result = self.match_ingredients_to_products(ingredients)
            
            # Create meal result
            processed_meal = {
                "name": meal_name,
                "benefits": meal.get("benefits", ""),
                "preparation": meal.get("preparation", ""),
                "ingredients": {
                    "available": ingredients_result["available"],
                    "unavailable": ingredients_result["unavailable"]
                }
            }
            
            processed_meals.append(processed_meal)
        
        return {"processed_meals": processed_meals}