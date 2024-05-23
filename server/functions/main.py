# Imports
import firebase_admin
from firebase_admin import credentials, db
from firebase_functions import https_fn, options
import json
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

# Initialize Firebase app
cred = credentials.Certificate("chiave.json")
firebase_admin.initialize_app(cred, {'databaseURL': 'https://nlp-chatbot-project-420413-default-rtdb.europe-west1.firebasedatabase.app/'})

# Reference to grocery list in database
grocery_list_ref = db.reference("grocery_list")

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
        print("paramatersss:" , parameters)
        print("item to analysze: " , item_to_analyze)
        nutrition_data = get_nutrition_data(item_to_analyze)
        print("nuitritionas data", nutrition_data)
        response_nutrition_data = create_dialogflow_response(f"{nutrition_data}")
        print ("response_nutrition_data", response_nutrition_data)
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
        print("paramatersss:" , parameters)
        print("item to analysze: " , item_to_search_recipe)
        recipe_data = get_recipe_data(item_to_search_recipe)
        print("nuitritionas data", recipe_data)
        response_recipe_data = create_dialogflow_response(f"{recipe_data}")
        print ("response_nutrition_data", response_recipe_data)
        return response_recipe_data
    except Exception as e:
        print("Error searching recipes data:", e)
        response_error = create_dialogflow_response(f"Error searching recipes data: {e}")
        return response_error, 500