import requests
import json

def load_api_key(file_path):
    """Loads the Edamam Recipe API Id and key from a JSON file."""

    with open(file_path, "r") as f:
        credentials = json.load(f)
    app_id = credentials.get("Application_ID")
    api_key = credentials.get("Application_Key")
    if not app_id or not api_key:
        raise ValueError(f"Missing 'Application_ID' or 'Application_Key' in {file_path}.")
    return app_id, api_key


def get_recipe_data(ingredient):

    try:
        app_id, app_key = load_api_key("edamam_recipeAPI_key.json")
        
        url = f'https://api.edamam.com/api/recipes/v2?type=public&q={ingredient}&app_id={app_id}&app_key={app_key}'
        
        headers = {
            'accept': 'application/json'
        }

        response = requests.get(url, headers=headers)
    
        if response.status_code == 200:
            data = response.json()

            recipes_info = []
            for i, recipe in enumerate(data.get("hits", [])[:4], 1):
                recipe_data = recipe["recipe"]

                # Controlla se il valore delle calorie è un dizionario
                if isinstance(recipe_data.get("calories"), dict):
                    calories_quantity = recipe_data["calories"].get("quantity", "N/A")
                    calories_unit = recipe_data["calories"].get("unit", "")
                else:
                    calories_quantity = recipe_data.get("calories", "N/A")
                    calories_unit = ""

                # Selezioniamo solo i campi desiderati con quantitativo e unità di misura
                recipe_info = {
                    "name": recipe_data.get("label", "Unknown"),
                    "image_url": recipe_data.get("image"),
                    "calories": {
                        "quantity": calories_quantity,
                        "unit": calories_unit
                    },
                    "ingredients": recipe_data.get("ingredientLines", []),
                    "recipe_url": recipe_data.get("url", "N/A")
                }

                recipes_info.append(recipe_info)

            formatted_text = ""
            for i, recipe_info in enumerate(recipes_info, 1):
                formatted_text += f"Recipe {i}:\n"
                formatted_text += f"Name: {recipe_info['name']}\n"
                # formatted_text += f"Image URL: {recipe_info['image_url']}\n"
                formatted_text += f"Calories: {recipe_info['calories']['quantity']} {recipe_info['calories']['unit']}\n"
                formatted_text += "Ingredients:\n"
                for ingredient in recipe_info["ingredients"]:
                    formatted_text += f"- {ingredient}\n"
                formatted_text += f"Recipe URL: {recipe_info['recipe_url']}\n"
                formatted_text += "\n"

            return formatted_text
        else:
            return {"success": False, "error": f"Error: {response.status_code}"}
        
    except Exception as e:  # Catch any unexpected errors
        print(f"Error using Edamam Recipe API: {e}")
        return e

# Example usage
# print(get_recipe_data("chicken breast"))