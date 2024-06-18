# Imports
import firebase_admin
from firebase_admin import credentials, db
from firebase_functions import https_fn, options
import json
import logging
import requests

from edamam_nutrition_api_script import get_nutrition_data
from edamam_recipe_api_script import get_recipe_data
from gemini_api_script import categorize_grocery_list

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

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
    with open(file_path, "r") as f:
        credentials = json.load(f)
    api_key = credentials.get("TELEGRAM_BOT_KEY")
    if not api_key:
        raise ValueError(f"Missing 'TELEGRAM_BOT_KEY' key in {file_path}.")
    return api_key

def load_dialogflow(file_path):
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
PROJECT_ID, AGENT_ID = load_dialogflow("dialogflow_infos.json")
REGION = "europe-west2"  
LANGUAGE_CODE = 'en'

# Configura il logging
logging.basicConfig(level=logging.DEBUG)

# Carica le credenziali di servizio dal file JSON
DIALOGFLOW_CREDENTIALS = service_account.Credentials.from_service_account_file(
    'chiave.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["post"]))
def telegram_webhook(request):
    try:
        request_data = request.get_json()
        if not request_data:
            return {"success": False, "error": "Request data is missing"}, 400

        logging.debug(f"Request data: {request_data}")

        message = None
        update_id = request_data.get('update_id')

        if 'message' in request_data:
            message = request_data['message']
        elif 'edited_message' in request_data:
            message = request_data['edited_message']
        elif 'channel_post' in request_data:
            message = request_data['channel_post']
        elif 'edited_channel_post' in request_data:
            message = request_data['edited_channel_post']
        elif 'my_chat_member' in request_data:
            logging.debug("Chat member update received, no action required.")
            return {"success": True, "message": "Chat member update received."}, 200
        else:
            logging.error("Invalid message format")
            return {"success": False, "error": "Invalid message format"}, 400

        if not message:
            logging.error("No message found in request data")
            return {"success": False, "error": "No message found in request data"}, 400

        chat_id = message.get('chat', {}).get('id')
        text = message.get('text')
        user_id = message.get('from', {}).get('id')
        username = message.get('from', {}).get('username', '')
        message_id = message.get('message_id')
        date = message.get('date')

        # Aggiungi logging per verificare i parametri estratti
        # logging.debug(f"chat_id: {chat_id}, text: {text}, user_id: {user_id}, username: {username}, message_id: {message_id}, date: {date}, update_id: {update_id}")

        if not chat_id or not text:
            # logging.error("Invalid message format")
            return {"success": False, "error": "Invalid message format"}, 400

        session_id = str(chat_id)
        
        # Chiamata a Dialogflow CX con "it" come LANGUAGE_CODE
        dialogflow_response = detect_intent_texts(session_id, text, user_id, username, chat_id, update_id, message_id, date)
        logging.debug(f"Dialogflow response: {dialogflow_response}")

        # Estrai tutti i messaggi di testo da responseMessages
        response_messages = dialogflow_response.get('queryResult', {}).get('responseMessages', [])
        response_texts = []
        for message in response_messages:
            if 'text' in message and 'text' in message['text']:
                response_texts.extend(message['text']['text'])

        # Unisci tutti i messaggi di testo in una singola stringa
        response_text = ' '.join(response_texts) if response_texts else "I didn't get that. May you try again please?"

        # response_text = dialogflow_response.get('queryResult', {}).get('responseMessages',{}).get('text',{}).get('text', 'I didn't get that. May you try again please?')

        # Invia risposta a Telegram
        telegram_response = send_message_to_telegram(chat_id, response_text)
        logging.debug(f"Telegram response: {telegram_response}")
        return {"success": True, "response": telegram_response}
    except Exception as e:
        logging.error(f"Error handling telegram webhook: {e}")
        return {"success": False, "error": str(e)}, 500

def detect_intent_texts(session_id, text, user_id, username, chat_id, update_id, message_id, date):
    # logging.debug(f"detect_intent_texts called with session_id: {session_id}, text: {text}, user_id: {user_id}, username: {username}, chat_id: {chat_id}, update_id: {update_id}, message_id: {message_id}, date: {date}")

    url = f"https://{REGION}-dialogflow.googleapis.com/v3/projects/{PROJECT_ID}/locations/{REGION}/agents/{AGENT_ID}/sessions/{session_id}:detectIntent"

    # Aggiorna il token se necessario
    auth_req = Request()
    DIALOGFLOW_CREDENTIALS.refresh(auth_req)
    token = DIALOGFLOW_CREDENTIALS.token

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    data = {
        "query_input": {
            "language_code": LANGUAGE_CODE,
            "text": {
                "text": text,
            }
        },
        "query_params": {
            "payload": {
                "data": {
                    "update_id": update_id,
                    "message": {
                        "message_id": message_id,
                        "from": {
                            "id": user_id,
                            "is_bot": False,
                            "first_name": username.split()[0] if username else "",
                            "last_name": username.split()[-1] if username else "",
                            "username": username,
                            "language_code": LANGUAGE_CODE
                        },
                        "chat": {
                            "id": chat_id,
                            "first_name": username.split()[0] if username else "",
                            "last_name": username.split()[-1] if username else "",
                            "username": username,
                            "type": "private"
                        },
                        "date": date,
                        "text": text
                    }
                },
                "source": "telegram"
            }
        }
    }

    # Aggiungi un log per stampare l'intero payload JSON
    # logging.debug(f"Payload inviato a Dialogflow: {json.dumps(data, indent=2)}")

    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"Ricevuta risposta da Dialogflow: {response.status_code} {response.text}")
    return response.json()

def send_message_to_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, json=payload)
    logging.debug(f"Ricevuta risposta da Telegram: {response.status_code} {response.text}")
    return response.json()

# Reference to grocery list in database
grocery_list_ref = db.reference("grocery_list")

# HTTP REQUEST: add new elements to grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["post"]))
def add_to_grocery_list(request):
    try:
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        items_to_add = parameters.get("item", {}).get("resolvedValue", [])

        current_items = grocery_list_ref.get()
        if current_items is None:
            current_items = []
        else:
            current_items = list(current_items.values())

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
        request_data = request.get_json()
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400

        parameters = request_data.get("intentInfo", {}).get("parameters", {})
        item_to_analyze = parameters.get("item", {}).get("resolvedValue", [])
        logging.debug(f"item to analyze: {item_to_analyze}")
        nutrition_data = get_nutrition_data(item_to_analyze)
        logging.debug(f"nutrition_data : {nutrition_data }")
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
