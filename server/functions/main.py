# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

# from firebase_functions import https_fn
# from firebase_admin import initialize_app
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_functions import https_fn, options

# Firebase app init
cred = credentials.Certificate("chiave.json")
firebase_admin.initialize_app(cred, {'databaseURL': 'https://nlp-chatbot-project-420413-default-rtdb.europe-west1.firebasedatabase.app/'})

# Grocery list ref in db
grocery_list_ref = db.reference("grocery_list")

# HTTP REQUEST: add new elements to grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["post"]))
def add_to_grocery_list(request):
    try:

        # Get JSON data from HTTP request
        request_data = request.get_json()

        # get items from HTTP request and items in firebase db, if HTTP request is not None
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400
        else:   
            parameters = request_data.get("intentInfo", {}).get("parameters", {})
            items_to_add = parameters.get("item", {}).get("resolvedValue", [])
            
            # Default value for items_already_in, if it is None
            if grocery_list_ref.get() is None:
                items_already_in = []
            else:
                items_already_in = list(grocery_list_ref.get().values())

            items_added = []
            # Pushing items to firebase db, if they're not already in
            for item in items_to_add:
                if (item not in items_already_in):
                    grocery_list_ref.push(item)
                    items_added.append(item)

            if len(items_added) == 0:
                return {"success": True, "message": "No element was added to grocery list. They were all already in."} 
            else:
                return {"success": True, "message": f"New items added to grocery list successfully: {items_added} are now in the list."}
    except Exception as e:
        print("Error adding new items:", e)
        return {"success": False, "error": "Internal server error"}, 500


# HTTP REQUEST: remove (given strings) elements from the grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["delete"]))
def remove_from_grocery_list(request):
    try:

        # Get JSON data from HTTP request
        request_data = request.get_json()

        # get items from HTTP request and items in firebase db, if HTTP request is not None
        if request_data is None:
            return {"success": False, "error": "Request data is missing"}, 400
        else:   
            parameters = request_data.get("intentInfo", {}).get("parameters", {})
            items_to_remove = parameters.get("item", {}).get("resolvedValue", [])
        
            print("ITEMS TO REMOVE: ", items_to_remove)
            items_already_in = list(grocery_list_ref.get().values())
            # Default value for items_already_in, if it is None
            if items_already_in is None:
                items_already_in = []
                return {"success": True, "message": "The grocery list is already empty!"}

            items_removed = []
            for item in items_to_remove:
                if (item in items_already_in):
                    query_result = grocery_list_ref.order_by_value().equal_to(item).get()
                    print("Query result: ", query_result)
                    # Finding key 
                    for key, value in query_result.items():
                        # Se il valore dell'elemento corrente è uguale a 'item', elimina l'elemento
                        if value == item:
                            grocery_list_ref.child(key).delete()
                            items_removed.append(item)
                
            if len(items_removed) == 0:
                return {"success": True, "message": "No element was removed from grocery list. They were not in."} 
            else:
                return {"success": True, "message": f"Items removed from grocery list successfully: {items_removed} are no longer in the list."}
    except Exception as e:
        print("Error removing items:", e)
        return {"success": False, "error": "Internal server error"}, 500

# HTTP REQUEST: view grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get"]))
def view_grocery_list(request):
    try:
        items_in = list(grocery_list_ref.get().values())
        # Default value if data 
        if items_in is None:
            return {"success": False, "error": "Items in the list are None-Type"}, 400
        else:
            return {"success": True, "message": f"Grocery list: {items_in}."}
    except Exception as e:
        print("Error reading items from grocery list:", e)
        return {"success": False, "error": "Internal server error"}, 500

# HTTP REQUEST: clear grocery list
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["delete"]))
def clear_grocery_list(request):
    try:
        grocery_list_ref.delete()
        return {"success": True, "message": "All items removed from grocery list successfully."}
    except Exception as e:
        print("Error removing all items from grocery list:", e)
        return {"success": False, "error": "Internal server error"}, 500