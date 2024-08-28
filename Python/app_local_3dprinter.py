from flask import Flask, render_template, request, url_for, jsonify, Response
from flask import jsonify
import threading
import logging
import datetime
import configparser
import time
import random
import json
import os
import requests
from math import radians, sin, cos, sqrt, atan2
app = Flask(__name__)

# GraphQL endpoint URL
graph_url = "http://localhost:1337/graphql"

# Global variables to store data
strapi_data                  = None
select_data                  = None
providers_list               = None
domain_id                    = None
provider_id                  = None
provider_uri                 = None
location_country             = None
selected_obj                 = None
init_obj                     = None
confirm_obj                  = None
fulfillments_init            = None
billing_init                 = None
fulfillments_confirm         = None
billing_confirm              = None
fulfillments_status          = None
billing_status               = None
total_cost                   = None
tax_amount                   = None
cost_with_tax                = None
selected_provider_id_confirm = None

# Define the request headers for graphql request
headers = {
    "Content-Type": "application/json",
}

# Keywords for searching the assembly services
assembly_keywords = {
    'assembly': 'all',
    'assembly service': 'all',
    'assembly services': 'all',
    'ets': 'ETS-Assembly',
    'ets assembly': 'ETS-Assembly',
    'steel': 'ETS-Assembly',
    'steel assembly': 'ETS-Assembly',
    'outbox': 'Outbox-Assembly',
    'outbox assembly': 'Outbox-Assembly',
    'box assembly': 'Outbox-Assembly',
    'cardboard assembly': 'Outbox-Assembly',
    'abs': 'ABS-Assembly',
    'abs assembly': 'ABS-Assembly',
    'brake': 'ABS-Assembly',
    'brake assembly': 'ABS-Assembly',
    'brake system assembly': 'ABS-Assembly',
    'wirth': 'Wirth-Werkzeugbau',
    'wirth-werkzeugbau': 'Wirth-Werkzeugbau',
    'car assembly': 'Wirth-Werkzeugbau',
    'car engine assembly': 'Wirth-Werkzeugbau',
    'automotive assembly': 'Wirth-Werkzeugbau',
    'circuit': 'PCBA-Assembly',
    'circuit board': 'PCBA-Assembly',
    'circuit board assembly': 'PCBA-Assembly',
    'furniture': 'Zapf-umzuge',
    'furniture assembly': 'Zapf-umzuge',
    'kitchen': 'Zapf-umzuge',
    'kitchen assembly': 'Zapf-umzuge',
    'industrial': 'Reiner-Assembly',
    'industrial assembly': 'Reiner-Assembly',
    'supply chain assembly': 'Reiner-Assembly'
}

# Keywords for searching the 3d-printing services
printing_3d = {
    '3d printing': 'all',
    '3d-printing': 'all',
    'makerspace': 'Makerspace-3d-printing-service'
}

@app.route('/')
def index():
    return render_template('index.html')

# This function is to send the response on_search message to the BppClient
@app.route('/search', methods=['POST'])
def search():
    request_data = request.get_json()
    radius_val_user = request_data['message']['intent']['provider']['locations'][0]['circle']['radius']['value']
    gps_coordinates_user = request_data['message']['intent']['provider']['locations'][0]['circle']['gps']   
    user_lat, user_lon = map(float, gps_coordinates_user.split(','))
    user_input = str(request_data['message']['intent']['category']['descriptor']['code']) # comparing the user_input with assembly_keywords
    user_input = user_input.lower().strip()
    user_rating_filter = request_data['message']['intent']['provider']['rating'] # the result would be like gt, gte, lt and lte, for example gte>4
    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.search.ets.json')
    with open(file_path, 'r') as json_file:
        template_data = json.load(json_file)   
    # Read Graphql data
    fetch_graphql_provider_data()
    # Creating a provider's list from the strapi output
    create_provider_list()
    provider_list_search = list(providers_list)
    # Check if the user provided a radius filter
    if radius_val_user != '0.0':
        radius_filter_enabled = True
    else:
        radius_filter_enabled = False 

    if user_rating_filter != 'lte<5':
        rating_filter_enabled = True
    else:
        rating_filter_enabled = False 

    # Initialize selected_provider to a default value
    selected_provider = 'default'

    # Check if user_input is in the assembly_keywords dictionary
    if user_input in assembly_keywords:
        selected_provider = assembly_keywords[user_input]

    if selected_provider == 'all':
         # Include all providers in providers_list
        if (radius_filter_enabled == True) or (rating_filter_enabled ==True):
            filtered_providers = []
            for provider in provider_list_search:
                provider_location = provider['location'][0]['gps']
                provider_lat, provider_lon = map(float, provider_location.split(','))
                distance_from_user = haversine(user_lat, user_lon, provider_lat, provider_lon) 
                provider_rating = float(provider['rating'])
                if 'gte>' in user_rating_filter:
                    user_rating_operator = 'gte'
                    user_rating_value = float(user_rating_filter.replace('gte>', ''))
                elif 'gt' in user_rating_filter:
                    user_rating_operator = 'gt'
                    user_rating_value = float(user_rating_filter.replace('gt>', ''))
                elif 'lte<' in user_rating_filter:
                    user_rating_operator = 'lte'
                    user_rating_value = float(user_rating_filter.replace('lte<', ''))
                elif 'lt<' in user_rating_filter:
                    user_rating_operator = 'lt'
                    user_rating_value = float(user_rating_filter.replace('lt<', ''))          

                if (radius_filter_enabled and distance_from_user > float(radius_val_user)) or (rating_filter_enabled and not (
                                                                            (user_rating_operator == 'gt' and provider_rating > user_rating_value) or
                                                                            (user_rating_operator == 'gte' and provider_rating >= user_rating_value) or
                                                                            (user_rating_operator == 'lt' and provider_rating < user_rating_value) or
                                                                            (user_rating_operator == 'lte' and provider_rating <= user_rating_value)
                    )) :
                        continue  # Skip to the next provider if the distance filter is not satisfied

                # If the provider satisfies both distance and rating filters, add it to the list
                filtered_providers.append(provider)

            provider_list_search = filtered_providers
        else:
            pass
    else:
        provider_list_search = [provider for provider in provider_list_search if provider['descriptor']['name'] == selected_provider]
    # Update template_data with the providers list
    template_data['context']['domain'] = domain_id
    template_data['context']['bpp_id'] = provider_id
    template_data['context']['bpp_uri'] = provider_uri
    template_data['context']['country'] = location_country
    template_data['message']['catalog']['descriptor']['name'] = '3d printing service'
    template_data['message']['catalog']['providers'] = provider_list_search
    return jsonify(template_data)

# This function is to send the response on_select message to the BppClient    
@app.route('/select', methods=['POST'])
def select():
    global selected_obj
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    # Read the request
    request_data = request.get_json()
    selected_provider_id = request_data['message']['order']['provider']['id']
    select_stage         = request_data['message']['order']['tags'][0]['descriptor']['name']
    select_response = create_select_response(selected_provider_id, select_stage)
    if select_response == 0:
        return jsonify("Error","The user has not selected the correct response")

    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.select.json')
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)

    # Update template_data with the providers list
    response_data['context']['domain'] = domain_id
    response_data['context']['bpp_id'] = provider_id
    response_data['context']['bpp_uri'] = provider_uri
    response_data['context']['country'] = location_country
    response_data['message']['order'] = selected_obj
    return jsonify(response_data)

# This function is to create the response structure for select as per Beckn format
def create_select_response(selected_id, select_stage):
    global selected_obj
    global strapi_data
    global total_cost
    global tax_amount
    global cost_with_tax
    tax_rate = 45
    fulfillments = [
        {"id": "f1", "type": "Delivery", "tracking": False},
        {"id": "f2", "type": "Self-Pickup", "tracking": False}
    ]
    # Fetch the url from strapi
    fetch_graphql_select_data()
    form_url  = select_data["data"]["inputs"]["data"][0]["attributes"]["form_url"] 
    config_id  = select_data["data"]["inputs"]["data"][0]["attributes"]["form_id"] 
    # Fetching data provided by user
    query_path = os.path.join(os.path.dirname(__file__), 'template', 'assembly-user-data.graphql')
    # Read the GraphQL query from the template file
    with open(query_path, 'r') as query_template_file:
        query = query_template_file.read()
    # Create the request payload
    data = {
        "query": query,
    }
    # Send the GraphQL request
    response = requests.post(graph_url, json=data, headers=headers)
    user_data = response.json() 
    form_id   = user_data["data"]["inputDetails"]["data"][0]["attributes"]["form_id"]
    total_cost = user_data["data"]["inputDetails"]["data"][0]["attributes"]["form_data"]["Total_Cost"]
    tax_amount = total_cost * (tax_rate / 100)
    cost_with_tax = total_cost + tax_amount
    # Declaring an empty list
    selected_obj = []
    # Loop through each provider in the GraphQL response
    for provider_data in strapi_data["data"]["providers"]["data"]:
        # check provider id
        if provider_data["id"] == selected_id:
            provider_attributes = provider_data["attributes"]
            # Extract logo url
            logo_data = provider_attributes["logo"]["data"]["attributes"]
            logo_url = logo_data["url"]
            # Extract provider name
            provider_name = provider_attributes["provider_name"]
            short_desc = provider_attributes["short_desc"]
            long_desc = provider_attributes["long_desc"]
            if select_stage == 'select-1':
                quote_data = {
                    "price": {
                        "currency":"Euro",
                        "value":"100"
                    }
                }
            else:
                quote_data = {
                        "breakup": [
                            {
                                "price": {
                                    "currency": "EUR",
                                    "value": str(total_cost)
                                },
                                "title": "Base Price"
                            },
                            {
                                "price": {
                                    "currency": "EUR",
                                    "value": str(tax_amount)
                                },
                                "title": "Tax"
                            }
                        ],
                        "price": {
                            "currency": "EUR",
                            "value": str(cost_with_tax)
                        }
                    }
            if select_stage == 'select-1': 
                xinput_data = {
                    "required":True,
                    "form":{
                         "mime_type":"text/html",
                        "url":form_url,
                        "resubmit":False,
                        "auth":{
                            "descriptor":{
                            "code":str(config_id)
                            },
                            "value":"eyJhbGciOiJIUzI.eyJzdWIiOiIxMjM0NTY3O.SflKxwRJSMeKKF2QT4"
                        }
                    }
                }
            tags, price = update_tags_and_price(provider_name)
            category_ids = provider_attributes["category_ids"]["data"]
            categories_list = [
            {
                "id": category["id"],
            }
            for category in category_ids
            ]
            items_data = provider_attributes["items"]["data"]
            if select_stage == 'select-1':
                items_list = [
                    {
                        "id": item["id"],
                        "descriptor": {
                            "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                            "name": item["attributes"]["name"]
                        },
                        "category_id": categories_list, 
                        "tags": tags,
                        "xinput": xinput_data,
                        "price":price            
                    }
                    for item in items_data
                ]
            else:
                items_list = [
                    {
                        "id": item["id"],
                        "descriptor": {
                            "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                            "name": item["attributes"]["name"]
                        },
                        "category_id": categories_list, 
                        "tags": tags,
                        "price":price            
                    }
                    for item in items_data
                ]
            # Construct the provider object
            selected_obj = {
                "provider": {
                    "id": provider_data["id"],
                    "descriptor": {
                        "images": [{"url": logo_url}],
                        "name": provider_name,
                        "short_desc": short_desc,
                        "long_desc": long_desc
                    }
                },
                "items": items_list,
                "fulfillments":fulfillments,
                "quote": quote_data 
            }
    if selected_obj == []:
        return 0
    else:
        return 1

# This function is to send the response on_init message to the BppClient
@app.route('/init', methods=['POST'])
def init():   
    global fulfillments_init
    global billing_init
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    # Declaring empty list for fulfillments_init
    fulfillments_init = []
    billing_init      = []
    # Read the request
    request_data = request.get_json()
    fulfillments_init = request_data['message']['order']['fulfillments']
    billing_init      = request_data['message']['order']['billing']
    selected_provider_id = request_data['message']['order']['provider']['id']
    init_response = create_init_response(selected_provider_id)
    if init_response == 0:
        return jsonify("Error","The user has not selected the correct response")

    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.init.json')
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)

    # Update template_data with the providers list
    response_data['context']['domain'] = domain_id
    response_data['context']['bpp_id'] = provider_id
    response_data['context']['bpp_uri'] = provider_uri
    response_data['context']['country'] = location_country
    response_data['message']['order'] = init_obj
    return jsonify(response_data)

# This function is to create the response structure for init as per Beckn format
def create_init_response(selected_id):
    global init_obj
    global strapi_data
    global fulfillments_init
    global billing_init
    global total_cost
    global tax_amount
    global cost_with_tax
    # Declaring an empty list
    init_obj = []
    # Check if strapi_data is None
    if strapi_data is None:
        # Fetch GraphQL data if strapi_data is None
        fetch_graphql_provider_data()
    # Loop through each provider in the GraphQL response
    for provider_data in strapi_data["data"]["providers"]["data"]:
        # check provider id
        if provider_data["id"] == selected_id:
            provider_attributes = provider_data["attributes"]
            # Extract logo url
            logo_data = provider_attributes["logo"]["data"]["attributes"]
            logo_url = logo_data["url"]
            # Extract provider name
            provider_name = provider_attributes["provider_name"]
            short_desc = provider_attributes["short_desc"]
            long_desc = provider_attributes["long_desc"]
            tags, price = update_tags_and_price(provider_name)
            category_ids = provider_attributes["category_ids"]["data"]
            categories_list = [
            {
                "id": category["id"],
            }
            for category in category_ids
            ]
            items_data = provider_attributes["items"]["data"]
            items_list = [
                {
                    "id": item["id"],
                    "descriptor": {
                        "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                        "name": item["attributes"]["name"]
                    },
                    "category_id": categories_list, 
                    "tags": tags,
                    "price":price            
                }
                for item in items_data
            ] 
            payment_details = [
               { 
                "collected_by": "BPP",
                "params": {
                    "amount": str(cost_with_tax),
                    "currency": "EUR",
                    "bank_account_number": "1234002341",
                    "bank_code": "INB0004321",
                    "bank_account_name": "Makerspace Assembly Ltd"
                        },
                "status": "NOT-PAID",
                "type": "PRE-ORDER"
               }
            ]
            quote_detail = {
                "breakup": [
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(total_cost)
                        },
                        "title": "Base Price"
                    },
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(tax_amount)
                        },
                        "title": "Tax"
                    }
                    ],
                    "price": {
                        "currency": "EUR",
                        "value": str(cost_with_tax)
                    }
            }
            # Construct the provider object
            init_obj = {
                "provider": {
                    "id": provider_data["id"],
                    "descriptor": {
                        "images": [{"url": logo_url}],
                        "name": provider_name,
                        "short_desc": short_desc,
                        "long_desc": long_desc
                    }
                },
                "items": items_list,
                "fulfillments": fulfillments_init,
                "billing": billing_init,
                "payments": payment_details,
                "quote": quote_detail,
                "type":  "DEFAULT"
            }
    if init_obj == []:
        return 0
    else:
        return 1

# This function is to send the response on_confirm message to the BppClient
@app.route('/confirm', methods=['POST'])
def confirm():   
    global fulfillments_confirm
    global billing_confirm
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    global selected_provider_id_confirm
    # Declaring empty list for fulfillments_init
    fulfillments_confirm = []
    billing_confirm     = []
    # Read the request
    request_data = request.get_json()
    fulfillments_confirm = request_data['message']['order']['fulfillments']
    # Add the new attributes to the existing fulfillment
    fulfillments_confirm[0]["state"] = {
        "descriptor": {
            "code": "ORDER_ACCEPTED",
            "short_desc": "Order has been confirmed..."
        }
    }
    billing_confirm      = request_data['message']['order']['billing']
    selected_provider_id_confirm = request_data['message']['order']['provider']['id']
    confirm_response = create_confirm_response(selected_provider_id_confirm)
    if confirm_response == 0:
        return jsonify("Error","The user has not selected the correct response")

    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.confirm.json')
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)

    # Update template_data with the providers list
    response_data['context']['domain'] = domain_id
    response_data['context']['bpp_id'] = provider_id
    response_data['context']['bpp_uri'] = provider_uri
    response_data['context']['country'] = location_country
    response_data['message']['order'] = confirm_obj
    form_url  = select_data["data"]["inputs"]["data"][1]["attributes"]["form_url"] 
    response = requests.post(form_url)
    return jsonify(response_data)

# This function is to create the response structure for confirm as per Beckn format
def create_confirm_response(selected_id):
    global confirm_obj
    global strapi_data
    global fulfillments_confirm
    global billing_confirm
    global total_cost
    global tax_amount
    global cost_with_tax
    # Declaring an empty list
    confirm_obj = []
    # Check if strapi_data is None
    if strapi_data is None:
        # Fetch GraphQL data if strapi_data is None
        fetch_graphql_provider_data()
    # Loop through each provider in the GraphQL response
    for provider_data in strapi_data["data"]["providers"]["data"]:
        # check provider id
        if provider_data["id"] == selected_id:
            provider_attributes = provider_data["attributes"]
            # Extract logo url
            logo_data = provider_attributes["logo"]["data"]["attributes"]
            logo_url = logo_data["url"]
            # Extract provider name
            provider_name = provider_attributes["provider_name"]
            short_desc = provider_attributes["short_desc"]
            long_desc = provider_attributes["long_desc"]
            tags, price = update_tags_and_price(provider_name)
            category_ids = provider_attributes["category_ids"]["data"]
            categories_list = [
            {
                "id": category["id"],
            }
            for category in category_ids
            ]
            items_data = provider_attributes["items"]["data"]
            items_list = [
                {
                    "id": item["id"],
                    "descriptor": {
                        "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                        "name": item["attributes"]["name"]
                    },
                    "category_id": categories_list, 
                    "tags": tags,
                    "price":price            
                }
                for item in items_data
            ] 
            payment_details = [
                {
                "collected_by": "BPP",
                "params": {
                    "amount": str(cost_with_tax),
                    "currency": "EUR",
                    "bank_account_number": "1234002341",
                    "bank_code": "INB0004321",
                    "bank_account_name": "Makerspace Assembly Ltd"
                        },
                "status": "PAID",
                "type": "PRE-ORDER",
                "transaction_id":"a35b56cf-e5cf-41f1-9b5d-fa99d8d5ac8c"
                }
            ]
            quote_detail = {
                "breakup": [
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(total_cost)
                        },
                        "title": "Base Price"
                    },
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(tax_amount)
                        },
                        "title": "Tax"
                    }
                    ],
                    "price": {
                        "currency": "EUR",
                        "value": str(cost_with_tax)
                    }
            }
            cancellation_field = [
                {
                    "cancellation_fee": {
                        "amount": {
                            "currency": "EUR",
                            "value": "100"
                        }
                    }
                }
            ]
            # Construct the provider object
            confirm_obj = {
                "id":"b989c9a9-f603-4d44-b38d-26fd72286b38",
                "provider": {
                    "id": provider_data["id"],
                    "descriptor": {
                        "images": [{"url": logo_url}],
                        "name": provider_name,
                        "short_desc": short_desc,
                        "long_desc": long_desc
                    }
                },
                "items": items_list,
                "fulfillments": fulfillments_confirm,
                "billing": billing_confirm,
                "payments": payment_details,
                "quote": quote_detail,
                "cancellation_terms": cancellation_field,
                "type":  "DEFAULT"
            }
    if init_obj == []:
        return 0
    else:
        return 1

# This function is to send the response on_status message to the BppClient
@app.route('/status', methods=['POST'])
def status():   
    global fulfillments_status
    global billing_status
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    global selected_provider_id_confirm
    # Declaring empty list for fulfillments_init
    fulfillments_status = []
    billing_status      = []
    # Read the request
    #request_data = request.get_json()
    fulfillments_status = fulfillments_confirm
    # Fetch the status from the Application
    fetch_graphql_select_data()
    form_url  = select_data["data"]["inputs"]["data"][2]["attributes"]["form_url"] 
    order_status = requests.post(form_url)
    order_status_json = order_status.json()
    # Add the new attributes to the existing fulfillment
    fulfillments_status[0]["state"] = {
        "descriptor": {
            "code": "ORDER_Status",
            "short_desc": order_status_json.get("status")
        },
        "updated_at":"2023-05-25T05:23:04.443Z"
    }
    billing_status       = billing_confirm
    #selected_provider_id = request_data['message']['order']['provider']['id']
    selected_provider_id = selected_provider_id_confirm
    status_response = create_status_response(selected_provider_id)
    if status_response == 0:
        return jsonify("Error","The user has not selected the correct response")

    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.status.json')
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)

    # Update template_data with the providers list
    response_data['context']['domain'] = domain_id
    response_data['context']['bpp_id'] = provider_id
    response_data['context']['bpp_uri'] = provider_uri
    response_data['context']['country'] = location_country
    response_data['message']['order'] = status_obj
    return jsonify(response_data)

# This function is to create the response structure for status as per Beckn format
def create_status_response(selected_id):
    global status_obj
    global strapi_data
    global fulfillments_status
    global billing_status
    global total_cost
    global tax_amount
    global cost_with_tax
    # Declaring an empty list
    status_obj = []
    # Check if strapi_data is None
    if strapi_data is None:
        # Fetch GraphQL data if strapi_data is None
        fetch_graphql_provider_data()
    # Loop through each provider in the GraphQL response
    for provider_data in strapi_data["data"]["providers"]["data"]:
        # check provider id
        if provider_data["id"] == selected_id:
            provider_attributes = provider_data["attributes"]
            # Extract logo url
            logo_data = provider_attributes["logo"]["data"]["attributes"]
            logo_url = logo_data["url"]
            # Extract provider name
            provider_name = provider_attributes["provider_name"]
            short_desc = provider_attributes["short_desc"]
            long_desc = provider_attributes["long_desc"]
            tags, price = update_tags_and_price(provider_name)
            category_ids = provider_attributes["category_ids"]["data"]
            categories_list = [
            {
                "id": category["id"],
            }
            for category in category_ids
            ]
            items_data = provider_attributes["items"]["data"]
            items_list = [
                {
                    "id": item["id"],
                    "descriptor": {
                        "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                        "name": item["attributes"]["name"]
                    },
                    "category_id": categories_list, 
                    "tags": tags,
                    "price":price            
                }
                for item in items_data
            ] 
            payment_details = [
                {
                "collected_by": "BPP",
                "params": {
                    "amount": str(cost_with_tax),
                    "currency": "EUR",
                    "bank_account_number": "1234002341",
                    "bank_code": "INB0004321",
                    "bank_account_name": "Makerspace Assembly Ltd"
                        },
                "status": "PAID",
                "type": "PRE-ORDER",
                "transaction_id":"a35b56cf-e5cf-41f1-9b5d-fa99d8d5ac8c"
                }
            ]
            quote_detail = {
                "breakup": [
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(total_cost)
                        },
                        "title": "Base Price"
                    },
                    {
                        "price": {
                            "currency": "EUR",
                            "value": str(tax_amount)
                        },
                        "title": "Tax"
                    }
                    ],
                    "price": {
                        "currency": "EUR",
                        "value": str(cost_with_tax)
                    }
            }
            cancellation_field = [
                {
                    "cancellation_fee": {
                        "amount": {
                            "currency": "EUR",
                            "value": "100"
                        }
                    }
                }
            ]
            # Construct the provider object
            status_obj = {
                "id":"b989c9a9-f603-4d44-b38d-26fd72286b38",
                "provider": {
                    "id": provider_data["id"],
                    "descriptor": {
                        "images": [{"url": logo_url}],
                        "name": provider_name,
                        "short_desc": short_desc,
                        "long_desc": long_desc
                    }
                },
                "items": items_list,
                "fulfillments": fulfillments_status,
                "billing": billing_status,
                "payments": payment_details,
                "quote": quote_detail,
                "cancellation_terms": cancellation_field,
                "type":  "DEFAULT"
            }
    if init_obj == []:
        return 0
    else:
        return 1

# This function is to create the response format and send the response on_track message to the BppClient
@app.route('/track', methods=['POST'])
def track():   
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    # Fetch the status from the Application
    fetch_graphql_select_data()
    track_url  = select_data["data"]["inputs"]["data"][3]["attributes"]["form_url"]  
    track_id  = select_data["data"]["inputs"]["data"][3]["attributes"]["form_id"]    
    track_obj = {
        "tracking": {
                "id": str(track_id),
                "url": track_url,
                "status": "active"
            }
        }
    file_path = os.path.join(os.path.dirname(__file__), 'response', 'response.track.json')
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)

    # Update template_data with the providers list
    response_data['context']['domain']  = domain_id
    response_data['context']['bpp_id']  = provider_id
    response_data['context']['bpp_uri'] = provider_uri
    response_data['context']['country'] = location_country
    response_data['message']            = track_obj
    return jsonify(response_data)

# This function creates a list of all the providers fetched from Strapi
def create_provider_list():
    global providers_list
    global strapi_data
    global domain_id 
    global provider_id 
    global provider_uri 
    global location_country
    fulfillments = [
        {"id": "f1", "type": "Delivery", "tracking": False},
        {"id": "f2", "type": "Self-Pickup", "tracking": False}
    ]
    # Initialize providers_list as an empty list
    providers_list = [] 
    # Loop through each provider in the GraphQL response
    for provider_data in strapi_data["data"]["providers"]["data"]:
        # Extract provider attributes
        provider_attributes = provider_data["attributes"]
        provider_data_id         = provider_data["id"]
        # Extract category data
        category_ids = provider_attributes["category_ids"]["data"]
        categories_list = [
            {
                "id": category["id"],
                "descriptor": {
                    "code": category["attributes"]["category_code"],
                    "name": category["attributes"]["value"]
                }
            }
            for category in category_ids
        ]

        # Extract location data
        location_data    = provider_attributes["location_id"]["data"]["attributes"]
        location_country = location_data["country"]
        location_state   = location_data["state"]
        location_city    = location_data["city"]
        location_lat     = location_data["latitude"]
        location_long    = location_data["longitude"]
        location_zip     = location_data["zip"]
        
        # Extract logo data
        logo_data = provider_attributes["logo"]["data"]["attributes"]
        logo_id = provider_attributes["logo"]["data"]["id"]
        logo_url = logo_data["url"]

        # Extract other provider attributes
        domain_id = provider_attributes["domain_id"]["data"]["attributes"]["DomainName"]
        provider_id = provider_attributes["provider_id"]
        provider_name = provider_attributes["provider_name"]
        provider_uri = provider_attributes["provider_uri"]
        short_desc = provider_attributes["short_desc"]
        long_desc = provider_attributes["long_desc"]
        # Call the function to update tags and price
        tags, price = update_tags_and_price(provider_name)
        rating      = str(get_provider_rating(provider_name))
        location    = get_provider_location(provider_name, location_lat, location_long, location_city,location_zip )
        # Extract item data
        items_data = provider_attributes["items"]["data"]
        items_list = [
            {
                "id": item["id"],
                "descriptor": {
                    "images": [{"url": item["attributes"]["image"]["data"][0]["attributes"]["url"]}],
                    "name": item["attributes"]["name"]
                }, 
                "tags": tags,
                "price":price,            
            }
            for item in items_data
        ] 
       
        # Construct the provider object
        provider_obj = {
            "id": provider_data_id,
            "rating": rating,
            "location":location,
            "descriptor": {
                "images": [{"url": logo_url}],
                "name": provider_name,
                "short_desc": short_desc,
                "long_desc": long_desc
            },
            "categories": categories_list,
            "items": items_list,
            "fulfillments": fulfillments
            # Add other provider attributes as needed
        }
        # Append the provider to the list
        providers_list.append(provider_obj)

# This function is to provide the ratings of the provider
def get_provider_rating(provider_name):
    if provider_name == "ETS-Assembly":
        return 3.7
    elif provider_name == "Outbox-Assembly":
        return 2.9
    elif provider_name == "Wirth-Werkzeugbau":
        return 4.5
    elif provider_name == "ABS-Assembly":
        return 4.0
    elif provider_name == "PCBA-Assembly":
        return 4.2
    elif provider_name == "Zapf-umzuge":
        return 3.1
    elif provider_name == "Reiner-Assembly":
        return 3.8

# This Function is to calculate the distance between the two gps cordinates
def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in miles
    R = 3959.0
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    # Calculate the change in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    # Calculate the distance
    distance = R * c
    return distance

# This function is to fetch the provider list from Strapi database
def fetch_graphql_provider_data():
    global strapi_data
    query_path = os.path.join(os.path.dirname(__file__), 'template', 'assembly-providers.graphql')
    # Read the GraphQL query from the template file
    with open(query_path, 'r') as query_template_file:
        query = query_template_file.read()
    # Create the request payload
    data = {
        "query": query,
    }
    # Send the GraphQL request
    response = requests.post(graph_url, json=data, headers=headers)
    strapi_data = response.json()

# This function is to fetch the selected providers details
def fetch_graphql_select_data():
    global select_data
    query_path = os.path.join(os.path.dirname(__file__), 'template', 'assembly-selectQuery.graphql')
    # Read the GraphQL query from the template file
    with open(query_path, 'r') as query_template_file:
        query = query_template_file.read()
    # Create the request payload
    data = {
        "query": query,
    }
    # Send the GraphQL request
    response = requests.post(graph_url, json=data, headers=headers)
    select_data = response.json()

# This function is to provide the location of the provider
def get_provider_location(provider_name, location_lat, location_long, location_city,location_zip ):
    location = []

    if provider_name == "ETS-Assembly":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "Zapf-umzuge":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "Outbox-Assembly":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "PCBA-Assembly":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "Wirth-Werkzeugbau":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "Reiner-Assembly":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    elif provider_name == "ABS-Assembly":
        location = [
           {
             "gps": f"{location_lat}, {location_long}",
             "city":{
                "name": location_city,
                "code": location_zip
             }  
           }
        ]
    return location

# This function is to update the tags and price of the provider
def update_tags_and_price(provider_name):
    tags = []
    price = {}

    if provider_name == "ETS-Assembly":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Steel container Box Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 10 EUR"
        }
    elif provider_name == "Zapf-umzuge":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Furniture Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 60 EUR"
        }
    elif provider_name == "Outbox-Assembly":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Cardboard Box Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 25 EUR"
        }
    elif provider_name == "PCBA-Assembly":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Circuit Board Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 150 EUR"
        }
    elif provider_name == "Wirth-Werkzeugbau":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Car Engine Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 700 EUR"
        }
    elif provider_name == "Reiner-Assembly":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Industrial Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 700 EUR"
        }
    elif provider_name == "ABS-Assembly":
        tags = [
            {
                "descriptor": {
                    "code": "product-info",
                    "name": "Product Information"
                },
                "list": [
                    {
                        "descriptor": {
                            "name": "product-type"
                        },
                        "value": "Brake System Assembly"
                    }
                ],
                "display": True
            },
            # Add other tags as needed
        ]
        price = {
            "currency": "EUR",
            "value": "starting from 580 EUR"
        }

    return tags, price

if __name__ == '__main__':
    app.run(debug=False)