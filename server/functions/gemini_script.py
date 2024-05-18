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

        prompt = f"You have to categorize items in a grocery list to help a customer finding the right supermarket section for every product in the list. I will give you in input the list and you have to return more list divided by category (supermarket section). The grocery list includes: {grocery_list}. Please categorize the items by supermarket section. Be careful to be precise in your categorization"
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:  # Catch any unexpected errors
        print(f"Error categorizing grocery list: {e}")
        return []  # Return an empty list on error

# Example usage
# grocery_list = ["Milk", "Bread", "Apples", "Bananas", "Eggs", "Laundry detergent", "Water bottle", "beer", "almonds", "peanuts butter"]
# categorized_list = categorize_grocery_list(grocery_list)
# print(categorized_list)
