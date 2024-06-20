import google.generativeai as genai
import json

def load_api_key(file_path):
    """Loads the Gemini API key from a JSON file."""

    with open(file_path, "r") as f:
        credentials = json.load(f)
    api_key = credentials.get("gemini_api_key")
    if not api_key:
        raise ValueError(f"Missing 'gemini_api_key' key in {file_path}.")
    return api_key

def categorize_grocery_list(grocery_list):
    """Categorizes a grocery list into supermarket sections using Gemini."""

    try:
        api_key = load_api_key("gemini-key.json") 
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel()

        prompt = (
            f"You have to categorize items in a grocery list "
            f"to help a customer finding the right "
            f"supermarket section for every product in the list. "
            f"I will give you in input the list "
            f"and you have to return more list divided by " 
            f"category (supermarket section). The grocery "
            f"list includes: {grocery_list}. "
            f"Please categorize the items by supermarket " 
            f"section. Be careful to be "
            f"precise in your categorization")

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:  # Catch any unexpected errors
        print(f"Error categorizing grocery list: {e}")
        return []  # Return an empty list on error

# Example usage
# grocery_list = ["Milk", "Bread", "Apples", "Eggs", "beer", "almonds", "juice"]
# categorized_list = categorize_grocery_list(grocery_list)
# print(categorized_list)
