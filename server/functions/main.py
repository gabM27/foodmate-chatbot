# Imports
import firebase_admin
from firebase_admin import credentials, db
from firebase_functions import https_fn, options
import json
# from flask import Flask
# import os

import requests
from gemini_api_script import categorize_grocery_list
from edamam_nutrition_api_script import get_nutrition_data
from edamam_recipe_api_script import get_recipe_data

# Helper function to create Dialogflow response
def create_dialogflow_response(message_text):
    response = {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [
                            message_text
                        ]
                    }
                }
            ]
        }
    }
    return json.dumps(response)

def load_telegram_key(file_path):
    """Loads the Telegram botfather API key from a JSON file."""

    with open(file_path, "r") as f:
        credentials = json.load(f)
    api_key = credentials.get("TELEGRAM_BOT_KEY")
    if not api_key:
        raise ValueError(f"Missing 'gemini_api_key' key in {file_path}.")
    return api_key

def load_dialogflow(file_path):
    """Loads the Dialogflow infos from a JSON file."""

    with open(file_path, "r") as f:
        credentials = json.load(f)
    project_ID = credentials.get("PROJECT_ID")
    agent_ID = credentials.get("AGENT_ID")
    if not project_ID or not agent_ID:
        raise ValueError(f"Missing 'PROJECT_ID' or 'AGENT_ID' in {file_path}.")
    return project_ID, agent_ID

# Initialize Firebase app
cred = credentials.Certificate("chiave.json")
firebase_admin.initialize_app(cred, {'databaseURL': 'https://nlp-chatbot-project-420413-default-rtdb.europe-west1.firebasedatabase.app/'})

# Token del bot Telegram
TELEGRAM_BOT_TOKEN = load_telegram_key("telegram_bot_father_key.json")

# Configurazione del client Dialogflow CX
PROJECT_ID, AGENT_ID = load_dialogflow("dialogflow_infos.json")
LOCATION = 'europe-west2' 
LANGUAGE_CODE = 'en' 

def detect_intent_texts(text):
    url = f"https://dialogflow.googleapis.com/v3/projects/{PROJECT_ID}/locations/{LOCATION}/agents/{AGENT_ID}/sessions/{text}/detectIntent"
    headers = {
        'Authorization': f'Bearer {TELEGRAM_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "query_input": {
            "text": {
                "text": text,
                "language_code": LANGUAGE_CODE
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    try:
        response_data = response.json()
        return response_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from Dialogflow: {e}")
        print(f"Response content: {response.content}")
        return None

def send_message_to_telegram(chat_id, text):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    try:
        response_data = response.json()
        if not response_data.get("ok"):
            print(f"Error from Telegram: {response_data}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from Telegram: {e}")
        print(f"Response content: {response.content}")

# Reference to grocery list in database
grocery_list_ref = db.reference("grocery_list")

# Firebase Function per gestire le richieste da Telegram
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["post"]))
def telegram_webhook(request):
    try:
        request_data = request.get_json()
        if not request_data:
            return {"success": False, "error": "Request data is missing"}, 400

        message = request_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text')

        if not chat_id or not text:
            return {"success": False, "error": "Invalid message format"}, 400

        # Chiamata a Dialogflow CX
        dialogflow_response = detect_intent_texts(text)
        if not dialogflow_response:
            return {"success": False, "error": "Error from Dialogflow"}, 500
        
        response_text = dialogflow_response.get('queryResult', {}).get('fulfillmentText', 'Nessuna risposta trovata.')

        # Invia risposta a Telegram
        send_message_to_telegram(chat_id, response_text)
        return {"success": True}, 200
    except Exception as e:
        print("Error handling telegram webhook:", e)
        return {"success": False, "error": str(e)}, 500

# HTTP REQUEST: add new elements to grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["post"]))
def add_to_grocery_list(request):
    try:
        # Get JSON data from HTTP request
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        items_to_add = parameters.get("item", {}).get("resolvedValue", [])

        # Get current items in grocery list or set to empty list if None
        current_items = grocery_list_ref.get()
        if current_items is None:
            current_items = []
        else:
            current_items = list(current_items.values())

        # Add items that are not already in the list
        items_added = []
        for item in items_to_add:
            if item not in current_items:
                grocery_list_ref.push(item)
                items_added.append(item)

        if not items_added:
            response_no_items_added = create_dialogflow_response("No element was added to grocery list. They were all already in.")
            return response_no_items_added
        else:
            response_items_added = create_dialogflow_response(f"New items added to grocery list successfully: {items_added} are now in the list.")
            return response_items_added

    except Exception as e:
        print("Error adding new items:", e)
        response_error = create_dialogflow_response(f"Error adding new items: {e}")
        return response_error, 500

# HTTP REQUEST: remove (given strings) elements from the grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["delete"]))
def remove_from_grocery_list(request):
    try:
        # Get JSON data from HTTP request
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        items_to_remove = parameters.get("item", {}).get("resolvedValue", [])

        current_items = grocery_list_ref.get()
        if current_items is None:
            response_no_items_ = create_dialogflow_response("The grocery list is already empty!")
            return response_no_items_
        else:
            current_items = list(current_items.values())
            items_removed = []

            for item in items_to_remove:
                if item in current_items:
                    query_result = grocery_list_ref.order_by_value().equal_to(item).get()
                    for key, value in query_result.items():
                        if value == item:
                            grocery_list_ref.child(key).delete()
                            items_removed.append(item)

            if not items_removed:
                response_no_items_removed = create_dialogflow_response("No element was removed from grocery list. They were not in.")
                return response_no_items_removed
            else:
                response_items_removed = create_dialogflow_response(f"Items removed from grocery list successfully: {items_removed} are no longer in the list.")
                return response_items_removed

    except Exception as e:
        print("Error removing items:", e)
        response_error = create_dialogflow_response(f"Error removing items: {e}")
        return response_error, 500

# HTTP REQUEST: view grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get"]))
def view_grocery_list(request):
    try:
        grocery_list = grocery_list_ref.get()
        if grocery_list is None or not grocery_list.values():
            response_no_items_in_the_list = create_dialogflow_response("The grocery list is empty.")
            return response_no_items_in_the_list

        items_in = list(grocery_list.values())
        response_categorized_items = create_dialogflow_response(categorize_grocery_list(items_in))
        return response_categorized_items

    except Exception as e:
        print("Error reading items from grocery list:", e)
        response_error = create_dialogflow_response(f"Error reading items from grocery list: {e}")
        return response_error, 500

# HTTP REQUEST: clear grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["delete"]))
def clear_grocery_list(request):
    try:
        current_items = grocery_list_ref.get()
        if current_items is None:
            response_no_items_ = create_dialogflow_response("The grocery list is already empty!")
            return response_no_items_
        else:
            grocery_list_ref.delete()
            response_success_delete = create_dialogflow_response("All items removed from grocery list successfully.")
            return response_success_delete
    except Exception as e:
        print("Error removing all items from grocery list:", e)
        response_error = create_dialogflow_response(f"Error removing all items from grocery list: {e}")
        return response_error, 500


# HTTP REQUEST: get nutrition analysis from Edamam.com API
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get"]))
def get_nutrition_analysis_single_ingredient(request):
    try:
        # Get JSON data from HTTP request
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        item_to_analyze = parameters.get("item", {}).get("resolvedValue", [])
        
        nutrition_data = get_nutrition_data(item_to_analyze)
        response_nutrition_data = create_dialogflow_response(f"{nutrition_data}")

        return response_nutrition_data
    except Exception as e:
        print("Error analyzing nutrition data:", e)
        response_error = create_dialogflow_response(f"Error analyzing nutrition data: {e}")
        return response_error, 500
    

# HTTP REQUEST: get recipes searching from Edamam.com API
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get"]))
def get_recipes_search(request):
    try:
        # Get JSON data from HTTP request
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        item_to_search_recipe = parameters.get("item", {}).get("resolvedValue", [])

        recipe_data = get_recipe_data(item_to_search_recipe)
        response_recipe_data = create_dialogflow_response(f"{recipe_data}")

        return response_recipe_data
    except Exception as e:
        print("Error searching recipes data:", e)
        response_error = create_dialogflow_response(f"Error searching recipes data: {e}")
        return response_error, 500
    
# if __name__ == "__main__":
#     from flask import Flask, request
#     app = Flask(__name__)

#     @app.route('/telegram_webhook', methods=['POST'])
#     def telegram_webhook_route():
#         return telegram_webhook(request)

#     @app.route('/add_to_grocery_list', methods=['POST'])
#     def add_to_grocery_list_route():
#         return add_to_grocery_list(request)

#     @app.route('/remove_from_grocery_list', methods=['DELETE'])
#     def remove_from_grocery_list_route():
#         return remove_from_grocery_list(request)

#     @app.route('/view_grocery_list', methods=['GET'])
#     def view_grocery_list_route():
#         return view_grocery_list(request)

#     @app.route('/clear_grocery_list', methods=['DELETE'])
#     def clear_grocery_list_route():
#         return clear_grocery_list(request)

#     @app.route('/get_nutrition_analysis_single_ingredient', methods=['GET'])
#     def get_nutrition_analysis_single_ingredient_route():
#         return get_nutrition_analysis_single_ingredient(request)

#     @app.route('/get_recipes_search', methods=['GET'])
#     def get_recipes_search_route():
#         return get_recipes_search(request)

#     # Run the app
#     port = int(os.environ.get('PORT', 8080))
#     app.run(host='0.0.0.0', port=port)