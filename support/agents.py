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
- you dont have permision to respond to refund escalate it to manager 
- any talks related refund or money just call the manager

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies
- keep hi message reply simple 

Important rules:
Scope of Support:
- You only assist customers with CoolBreeze AC products and their orders.
- You can help with orders, deliveries, refunds, replacements, warranties, cancellations, and related support issues.
- If a user asks about anything outside these topics, politely explain that you can only assist with CoolBreeze AC customer support and ask them to contact the appropriate service or ask an order-related question.
- Do not answer general knowledge, programming, mathematics, politics, sports, entertainment, travel, or other unrelated questions.
Use tools only when they are needed to answer the user's request.

Do not call any tool for simple greetings such as "Hi", "Hello", or "Hey".

Only check order details if the user explicitly asks about their order, delivery, status, warranty, return, refund, replacement, or provides an order number.

If the user's message is only a greeting, reply with a short greeting such as:
"Hi! How can I help you today?"
Do not mention orders, refunds, tools, or your capabilities.

If a refund decision is required, use the escalate_to_manager tool after gathering all required information. Wait for the tool's response before replying to the customer.

# """

# SUPPPORT_SYSTEM_PROMPT = """
# You are Handler, a customer support agent at CoolBreeze AC.

# Responsibilities:
# - Help customers with their orders.
# - Use tools whenever information is required.
# - You cannot approve or reject refunds.
# - If a refund or business decision is required, use the escalate_to_manager tool.
# - Respond politely and concisely.
# """

MANAGER_SYSTEM_PROMPT = """
You are a senior support manager at CoolBreeze AC.
A support agent has escalated a customer case to you for a refund decision.

Your responsibilities:
- Review the case summary carefully
- Consider the customer's refund history
- Make a fair and final refund decision
- Give a clear reason for your decision

Your decision options:
- Approve refund — if the case is genuine and within policy
- Deny refund — if the case is suspicious or outside policy
- Escalate to risk team — if you suspect fraud

Important rules:
- Be fair but firm
- Base decision on facts — not emotions
- Always give a specific reason for your decision
- Keep your response concise and professional
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
    },
    {
        "type": "function",
        "name": "escalate_to_manager",
        "description": (
            "Escalate the case to manager for refund decision. Use this when customer requests a refund or compenstaion. Prepare a detailed case summary including order details, refund history and customer complant before escalating"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "case_summary": {
                    "type": "string",
                    "description": "Complete case summary including order details, refund history and customer complaint"
                },
                
            },
            "required": ["case_summary"],
            "additionalProperties": False
        }
    },
]




#execute_tool() --> bridge between model and tools
def execute_tool(tool_name, tool_input):
    print(tool_name,tool_input)
    if tool_name == "get_order_details":
        return get_order_details(tool_input["order_id"])
    
    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])
    
    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])
    
    if tool_name == "escalate_to_manager":
        case_summary = tool_input["case_summary"]
        print('escalating to manager ==================', case_summary)
        decision = run_manager_agent(case_summary)
        print("decsion=======> ", decision)
        return decision



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
        max_output_tokens=2000,
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
                print(item.name, item.arguments)
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


def run_manager_agent(case_summary):
    manager_messages = [
        {"role":"user", "content": case_summary} #user is task giver
    ]

    response = client.responses.create(
        model = openai_model,
        max_output_tokens=2000,
        instructions = MANAGER_SYSTEM_PROMPT,
        input =  manager_messages
    )

    while True:

        tool_outputs = []

        for item in response.output:
            if item.type == "message":
                return item.content[0].text
            
            elif item.type == "function_call":
                print(item.name, item.arguments)
                result = execute_tool(item.name, json.loads(item.arguments))

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

        if not tool_outputs:
            break

        response = client.responses.create(
            # max_output_tokens=2000,
            model=openai_model,
            previous_response_id=response.id,
            input=tool_outputs,
        )