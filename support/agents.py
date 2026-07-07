import os
from openai import OpenAI
from django.conf import settings

from support.models import Conversation
from .tools import *
import json
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
- keep hi message reply simple 

Important rules:
Use tools only when they are needed to answer the user's request.

Do not call any tool for simple greetings such as "Hi", "Hello", or "Hey".

Only check order details if the user explicitly asks about their order, delivery, status, warranty, return, refund, replacement, or provides an order number.

If the user's message is only a greeting, reply with a short greeting such as:
"Hi! How can I help you today?"
Do not mention orders, refunds, tools, or your capabilities.
- Never approve or deny a refund yourself
- If refund decision is needed - tell customer you are checking with your team

"""


# SUPPORT TOOLS --> Tools schemas
SUPPORT_TOOLS = [
    {
        "type": "function",
        "name": "get_order_details",
        "description": (
            "Fetch complete order details including status, carrier, "
            "tracking number, and days since the order was placed. "
            "Use this when the customer mentions their order or asks "
            "about delivery."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "The order ID to look up"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "type": "function",
        "name": "get_refund_history",
        "description": (
            "Retrieve the refund request history for a user. "
            "Returns the total number of refund requests along with "
            "details such as order ID, product name, refund reason, "
            "current status, and request date."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The unique ID of the user."
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "check_delivery_status",
        "description": (
            "Retrieve the current delivery status of a shipment using "
            "its tracking number and carrier."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tracking_number": {
                    "type": "string",
                    "description": "Shipment tracking number."
                },
                "carrier": {
                    "type": "string",
                    "description": "Shipping carrier."
                }
            },
            "required": ["tracking_number", "carrier"],
            "additionalProperties": False
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
def run_support_agent(user_message, conversation_id, order_id, user_id):
    conv = Conversation.objects.get(id = conversation_id)

    conversation_messages = []
    for msg in conv.messages.order_by("created_at"):
        conversation_messages.append({
            "role" : msg.role,
            "content" : msg.content
        })

    
    response = client.responses.create(
        model=openai_model,
        instructions=SUPPPORT_SYSTEM_PROMPT + f"\n\nContext: This conversation is about order #{order_id}, user: {user_id}",
        tools=SUPPORT_TOOLS,
        input=conversation_messages,
    )

    while True:

        tool_outputs = []

        for item in response.output:

            if item.type == "message":
                return item.content[0].text

            elif item.type == "function_call":
                print(item.name)
                print(item.arguments)
                print("=============================")
                result = execute_tool(item.name, json.loads(item.arguments))

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

        if not tool_outputs:
            break

        response = client.responses.create(
            model=openai_model,
            previous_response_id=response.id,
            input=tool_outputs,
        )

