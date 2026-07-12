import os
from openai import OpenAI
from django.conf import settings

from support.models import Conversation
from .tools import *
import json
from support.models import AgentLog
client = OpenAI(api_key=settings.OPENAI_API_KEY)
openai_model = settings.OPENAI_MODEL


#SUPPORT SYSTEM PROMPT --> HANDLER JOB DESCRIPTION
SUPPPORT_SYSTEM_PROMPT = """
You are Handler, a customer support agent at CoolBreeze AC.
You help customers with issues related to theie AC orders

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order detials when customer mentions their order
- Be empathetic but honest
- Refund Handling:
- If the customer requests a refund, you MUST call the manager tool before responding.
- Do not decide or promise a refund yourself.
- After receiving the manager's response, explain it to the customer.

- If the customer is only asking about:
  - the refund policy,
  - the status of an existing refund,
  - whether a refund is available,
  - or any general question about refunds,

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies
- keep hi message reply simple 

Important rules:
Scope of Support:
- You only assist customers with CoolBreeze AC products and their orders.
- you are only allowed to answer the questions about coolBreeze
- You can help with orders, deliveries, refunds, replacements, warranties, cancellations, and related support issues.
- If a user asks about anything outside these topics, politely explain that you can only assist with CoolBreeze AC customer support and ask them to contact the appropriate service or ask an order-related question.
- Do not answer general knowledge, programming, mathematics, politics, sports, entertainment, travel, or other unrelated questions.


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


RISK_SYSTEM_PROMPT = """
You are a fraud risk analyst at CoolBreeze AC.
A support manager has sent you a customer profile for risk assessment.

Your job:
- Analyse the customer's order and refund patterns
- Identify suspicious behaviour
- Return a clear risk verdict

Risk levels:
- LOW — genuine customer, normal behaviour
- MEDIUM — some suspicious signals, proceed with caution
- HIGH — clear fraud pattern, recommend denial

Your response format:
- Risk Level: LOW / MEDIUM / HIGH
- Key Signals: what you found suspicious or genuine
- Recommendation: what manager should do

Important:
- Be objective — base verdict on data only
- One bad refund does not make someone fraudulent
- Look for patterns — not isolated incidents
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
            "consult the manager incase of refund for customer. Use this when customer requests a refund or compenstaion. Prepare a detailed case summary including order details, refund history and customer complant before escalating"
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

MANAGER_TOOLS = [
    {
        "type": "function",
        "name": "assess_fraud_risk",
        "description": (
                "Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID to assess fraud risk for"
                }
                
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
]

RISK_TOOLS = [
    {
        "type": "function",
        "name": "get_customer_risk_profile",
        "description": (
            "Get complete risk profile for a customer including order history, refund patterns and ratio. Use this to assess fraud risk."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID to assess risk for"
                }
                
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
]




#execute_tool() --> bridge between model and tools
def execute_tool(tool_name, tool_input,converstion_id = None):
    print(tool_name,tool_input)
    if tool_name == "get_order_details":
        return get_order_details(tool_input["order_id"])
    
    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])
    
    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])
    
    if tool_name == "escalate_to_manager":
        case_summary = tool_input["case_summary"]
        decision = run_manager_agent(case_summary,converstion_id)
        # print("decsion=======> ", decision)
        return decision
    
    if(tool_name == "assess_fraud_risk"):
        user_id = tool_input['user_id']
        verdict = run_risk_agent(user_id, converstion_id)
        # print("risk verdict ===>", verdict)
        return verdict
    
    if tool_name == "get_customer_risk_profile":
        return get_customer_risk_profile(tool_input["user_id"])


#Agent Loop
def run_support_agent(user_message, conversation_id, order_id, user_id):
    conv = Conversation.objects.get(id = conversation_id)

    conversation_messages = []
    for msg in conv.messages.order_by("created_at"):
        conversation_messages.append({
            "role" : msg.role,
            "content" : msg.content
        })

    print("calling support")
    response = client.responses.create(
        model=openai_model,
        max_output_tokens=2000,
        instructions=SUPPPORT_SYSTEM_PROMPT + f"\n\nContext: This conversation is about order #{order_id}, user: {user_id}",
        tools=SUPPORT_TOOLS,
        input=conversation_messages,
    )

    while True:

        tool_outputs = []
        final_message = None

        for item in response.output:

            if item.type == "function_call":
                AgentLog.objects.create(conversation = conv,event_type = "tool_call", message = f"Calling tool {item.name} with {item.arguments}")

                result = execute_tool(
                    item.name,
                    json.loads(item.arguments),
                    conversation_id
                )

                AgentLog.objects.create(conversation = conv,event_type = "tool_result", message = f"Calling tool {item.name} with {str(result)[:200]}")

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

            elif item.type == "message":
                AgentLog.objects.create(conversation = conv,event_type = "final", message = item.content[0].text)
                final_message = item.content[0].text

        if tool_outputs:
            print("calling support")
            response = client.responses.create(
                model=openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
            )
            continue

        return final_message


def run_manager_agent(case_summary, converstion_id):
    manager_messages = [
        {"role":"user", "content": case_summary} #user is task giver
    ]
    conv =Conversation.objects.get(id = converstion_id)
    AgentLog.objects.create(conversation = conv,event_type = "manager", message = f"case received for review : {case_summary[:200]}")
    print("calling manager")

    response = client.responses.create(
        model = openai_model,
        max_output_tokens=2000,
        instructions = MANAGER_SYSTEM_PROMPT,
        tools = MANAGER_TOOLS,
        input =  manager_messages
    )

    while True:

        tool_outputs = []
        final_message = None

        for item in response.output:

            if item.type == "function_call":
                AgentLog.objects.create(conversation = conv,event_type = "manager", message = "consulting risk agent for fraud assessment")    
                result = execute_tool(
                    item.name,
                    json.loads(item.arguments),\
                    converstion_id
                )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

            elif item.type == "message":
                final_message = item.content[0].text
                AgentLog.objects.create(conversation = conv,event_type = "manager", message = f"descion : {final_message}") 


        if tool_outputs:
            print("calling manager")
            response = client.responses.create(
                model=openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
            )
            continue
        return final_message

def run_risk_agent(user_id, converstion_id):
    conv = Conversation.objects.get(id = converstion_id)
    risk_messages = [
        {"role":"user", "content": f"Please assess the fraud risk for user ID {user_id}, Use your tool to get their profile and return a verdict"} #user is task giver
    ]
    AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"starting fraud asessment for user {user_id}") 
    print("calling risk")
    response = client.responses.create(
        model = openai_model,
        max_output_tokens=2000,
        instructions = RISK_SYSTEM_PROMPT,
        tools = RISK_TOOLS,
        input =  risk_messages
    )

    while True:

        tool_outputs = []
        final_message = None

        for item in response.output:

            if item.type == "function_call":
                AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"Calling {item.name} to get risk profile") 

                result = execute_tool(
                    item.name,
                    json.loads(item.arguments),
                    converstion_id
                )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

            elif item.type == "message":
                final_message = item.content[0].text
                AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"descion : {final_message}") 


        if tool_outputs:
            print("calling risk")
            response = client.responses.create(
                model=openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
            )
            continue
    

        return final_message

