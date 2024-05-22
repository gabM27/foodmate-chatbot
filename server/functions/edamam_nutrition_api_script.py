import requests
import json

def load_api_key(file_path):
    """Loads the Edamam API Id and key from a JSON file."""

    with open(file_path, "r") as f:
        credentials = json.load(f)
    app_id = credentials.get("Application_ID")
    api_key = credentials.get("Application_Key")
    if not app_id or not api_key:
        raise ValueError(f"Missing 'Application_ID' or 'Application_Key' in {file_path}.")
    return app_id, api_key

def get_nutrition_data(ingredient):

    try:
        app_id, app_key = load_api_key("edamam_nutritionAPI_key.json")
        url = f'https://api.edamam.com/api/nutrition-data?app_id={app_id}&app_key={app_key}&nutrition-type=logging&ingr={ingredient}'
        
        headers = {
            'accept': 'application/json'
        }

        response = requests.get(url, headers=headers)
    
        if response.status_code == 200:
            data = response.json()
            # Selezioniamo solo i campi desiderati con quantitativo e unità di misura
            filtered_data = {
                "food_name": data["ingredients"][0]["parsed"][0]["foodMatch"] if data.get("ingredients") and data["ingredients"][0].get("parsed") else "Unknown",
                "cautions": data.get("cautions", []),
                "calories": {
                    "quantity": data["calories"],
                    "unit": "kcal"
                } if data.get("calories") else None,
                "FAT": {
                    "quantity": data["totalNutrients"]["FAT"]["quantity"],
                    "unit": data["totalNutrients"]["FAT"]["unit"]
                } if data.get("totalNutrients") and data["totalNutrients"].get("FAT") else None,
                "Carbohydrates (net)": {
                    "quantity": data["totalNutrients"]["CHOCDF.net"]["quantity"],
                    "unit": data["totalNutrients"]["CHOCDF.net"]["unit"]
                } if data.get("totalNutrients") and data["totalNutrients"].get("CHOCDF.net") else None,
                "Protein": {
                    "quantity": data["totalNutrients"]["PROCNT"]["quantity"],
                    "unit": data["totalNutrients"]["PROCNT"]["unit"]
                } if data.get("totalNutrients") and data["totalNutrients"].get("PROCNT") else None,
                "Sodium (NA)": {
                    "quantity": data["totalNutrients"]["NA"]["quantity"],
                    "unit": data["totalNutrients"]["NA"]["unit"]
                } if data.get("totalNutrients") and data["totalNutrients"].get("NA") else None,
                "totalNutrientsKCal": data.get("totalNutrientsKCal", {})
            }
            
            formatted_text = f"Food Name Matched: {filtered_data['food_name']}\n"
    
            if filtered_data["cautions"]:
                formatted_text += "Cautions: " + ", ".join(filtered_data["cautions"]) + "\n"
            else:
                formatted_text += "Cautions: None\n"

            if filtered_data["calories"]:
                formatted_text += f"Calories: {filtered_data['calories']['quantity']} {filtered_data['calories']['unit']}\n"
            else:
                formatted_text += "Calories: Not available\n"

            if filtered_data["FAT"]:
                formatted_text += f"Fat: {filtered_data['FAT']['quantity']} {filtered_data['FAT']['unit']}\n"
            else:
                formatted_text += "Fat: Not available\n"

            if filtered_data["Carbohydrates (net)"]:
                formatted_text += f"Carbohydrates (net): {filtered_data['Carbohydrates (net)']['quantity']} {filtered_data['Carbohydrates (net)']['unit']}\n"
            else:
                formatted_text += "Carbohydrates (net): Not available\n"

            if filtered_data["Protein"]:
                formatted_text += f"Protein: {filtered_data['Protein']['quantity']} {filtered_data['Protein']['unit']}\n"
            else:
                formatted_text += "Protein: Not available\n"

            if filtered_data["Sodium (NA)"]:
                formatted_text += f"Sodium (NA): {filtered_data['Sodium (NA)']['quantity']} {filtered_data['Sodium (NA)']['unit']}\n"
            else:
                formatted_text += "Sodium (NA): Not available\n"

            nutrient_mapping = {
                "ENERC_KCAL": "Total Kcal",
                "PROCNT_KCAL": "Kcal from protein",
                "FAT_KCAL": "Kcal from fat",
                "CHOCDF_KCAL": "Kcal from carbohydrates"
            }

            formatted_text += "-------\nTotal Nutrients KCal.\n"
            for nutrient, value in filtered_data["totalNutrientsKCal"].items():
                nutrient_name = nutrient_mapping.get(nutrient, nutrient)
                formatted_text += f"  {nutrient_name}: {value['quantity']} {value['unit']}\n"

            return formatted_text
        
        else:
            return {"success": False, "error": f"Error: {response.status_code}"}
        
    except Exception as e:  # Catch any unexpected errors
        print(f"Error using Edamam Nutrition API: {e}")
        return e