import json
import os
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_bmr(age: int, gender: str, weight: float, height: float) -> float:
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation.
    
    Args:
        age: Age in years
        gender: 'male' or 'female'
        weight: Weight in kg
        height: Height in cm
        
    Returns:
        BMR in calories per day
    """
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # female
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    return round(bmr, 2)

def calculate_daily_calories(bmr: float, activity_level: str) -> Dict[str, float]:
    """
    Calculate total daily energy expenditure based on activity level.
    
    Args:
        bmr: Basal Metabolic Rate
        activity_level: Sedentary, Light, Moderate, Active, or Very Active
        
    Returns:
        Dictionary with maintenance, deficit, and surplus calorie values
    """
    multipliers = {
        'sedentary': 1.2,  # Little or no exercise
        'light': 1.375,    # Light exercise 1-3 days per week
        'moderate': 1.55,  # Moderate exercise 3-5 days per week
        'active': 1.725,   # Active exercise 6-7 days per week
        'very active': 1.9 # Very intense exercise daily
    }
    
    activity_level = activity_level.lower()
    multiplier = multipliers.get(activity_level, 1.2)  # Default to sedentary if unknown
    
    maintenance = round(bmr * multiplier, 2)
    deficit = round(maintenance * 0.8, 2)  # 20% caloric deficit
    surplus = round(maintenance * 1.15, 2)  # 15% caloric surplus
    
    return {
        'maintenance': maintenance,
        'deficit': deficit,
        'surplus': surplus
    }

def parse_nutrition_facts(nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and standardize nutrition facts from various formats.
    
    Args:
        nutrition_data: Raw nutrition data from various sources
        
    Returns:
        Standardized nutrition facts dictionary
    """
    result = {
        'calories': 0,
        'protein': 0,
        'carbohydrates': 0,
        'fat': 0,
        'fiber': 0,
        'sugar': 0,
        'sodium': 0
    }
    
    try:
        # Update default values with provided data, handling unit conversions
        for key, value in nutrition_data.items():
            key = key.lower()
            
            if isinstance(value, str):
                # Remove units like 'g', 'mg', etc.
                value = ''.join(c for c in value if c.isdigit() or c == '.')
                try:
                    value = float(value)
                except ValueError:
                    value = 0
            
            if key in ('calories', 'kcal', 'energy'):
                result['calories'] = value
            elif key in ('protein', 'proteins'):
                result['protein'] = value
            elif key in ('carbohydrates', 'carbs', 'carbohydrate'):
                result['carbohydrates'] = value
            elif key in ('fat', 'total_fat', 'fats'):
                result['fat'] = value
            elif key in ('fiber', 'dietary_fiber'):
                result['fiber'] = value
            elif key in ('sugar', 'sugars'):
                result['sugar'] = value
            elif key in ('sodium', 'salt'):
                result['sodium'] = value
                
        return result
    
    except Exception as e:
        logger.error(f"Error parsing nutrition facts: {str(e)}")
        return result

def get_matching_ingredient(query: str, ingredients_list: List[str]) -> Optional[str]:
    """
    Find the most relevant matching ingredient from a list.
    
    Args:
        query: Ingredient to search for
        ingredients_list: List of ingredients to search in
        
    Returns:
        Best matching ingredient or None if no good match
    """
    query = query.lower()
    
    # Direct match
    for ingredient in ingredients_list:
        if query == ingredient.lower():
            return ingredient
    
    # Partial match
    matches = []
    for ingredient in ingredients_list:
        if query in ingredient.lower() or ingredient.lower() in query:
            matches.append((ingredient, len(ingredient)))
    
    # Sort by length (shorter matches are usually more accurate)
    if matches:
        matches.sort(key=lambda x: x[1])
        return matches[0][0]
    
    return None 