import os
from openai import OpenAI
from django.conf import settings
from .tools import *

client = OpenAI(api_key=settings.OPENAI_API_KEY)
openai_model = settings.OPENAI_MODEL


#SUPPORT SYSTEM PROMPT --> HANDLER JOB DESCRIPTION
SUPPPORT_SYSTEM_PROMPT = """
You are Handler, a customer support agent at CoolBreeze AC.
You help customers with issues related to theie AC orders

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order detials when customer mentions their order
- Check refund history before making any refund decisions
- Be empathetic but honest

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies

Important rules:
- Always check order detials first before responding
- Never approve or deny a refund yourself
- If refund decision is needed - tell customer you are checking with your team

"""


# SUPPORT TOOLS --> Tools schemas
SUPPORT_TOOLS = [
    {
        "name" : "get_order_details",
        "description" : "fetch complete order details including status, carrier, tracking number and days since order was placed. use this when customer mentions their order or complains about delivery.",
        "input_schema" : {
            "type" : "object",
            "properties" : {
                "order_id" : {
                    "type" : "integer",
                    "description" : "The order ID to look up"
                }
            },
            "required" : ["order_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_refund_history",
            "description": "Retrieve the refund request history for a user. Returns the total number of refund requests along with details such as order ID, product name, refund reason, current status, and request date.",
            "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                "type": "integer",
                "description": "The unique ID of the user whose refund history should be retrieved."
                }
            },
            "required": [
                "user_id"
            ],
            "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_delivery_status",
            "description": "Retrieve the current delivery status of a shipment using its tracking number and carrier. Returns the shipment status, last known location, latest tracking update, estimated delivery date, and any delay reason if available. Use this when csutomer complains about delayed or missing delivery",
            "parameters": {
            "type": "object",
            "properties": {
                "tracking_number": {
                "type": "string",
                "description": "The shipment tracking number provided by the carrier."
                },
                "carrier": {
                "type": "string",
                "description": "The shipping carrier handling the package (e.g., FedEx, UPS, DHL, USPS)."
                }
            },
            "required": [
                "tracking_number",
                "carrier"
            ],
            "additionalProperties": False
            }
        }
    }
]




#execute_tool() --> bridge between model and tools
def execute_tool(tool_name, tool_input):
    if tool_name == "get_order_details":
        return get_order_details(tool_input["order_id"])
    
    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])
    
    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])



#Agent Loop