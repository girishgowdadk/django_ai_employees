from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from support.langchain_tools import get_order_details, get_refund_history, check_delivery_status, search_knowledge_base, get_customer_risk_profile
from support.agents import SUPPPORT_SYSTEM_PROMPT, MANAGER_SYSTEM_PROMPT, RISK_SYSTEM_PROMPT
from langgraph.checkpoint.memory import InMemorySaver 
from .models import Conversation, AgentLog
from langchain.agents.middleware import wrap_tool_call
from .event_queue import publish, DONE
from langchain.tools import tool

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY
)

SUPPORT_TOOLS = [
    get_order_details,
    get_refund_history,
    check_delivery_status,
    search_knowledge_base
]


checkpointer = InMemorySaver() 





def run_support_agent_langchain(user_message, conversation_id, order_id, user_id):
    config = {"configurable": {"thread_id": str(conversation_id)}}
    conv = Conversation.objects.get(id=conversation_id)
    context = f"Conversation ID: {conversation_id}, Order ID: {order_id}, User ID: {user_id} , {user_message}"

    
    @tool
    def escalate_to_manager(case_summary :str) -> dict:
        """
        "consult the manager incase of refund for customer. Use this when customer requests a refund or compenstaion. Prepare a detailed case summary including order details, refund history and customer complant before escalating"

        """
        return run_manager_agent_langchain(case_summary, conversation_id)

    @wrap_tool_call
    def log_tool_calls_middleware(request, handler):
        print("about to log tool calls")
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]

        event = {"type": "tool_result", "message" : f"Calling tool {tool_name} with {tool_args}"}
        publish(conversation_id,event)

        AgentLog.objects.create(conversation = conv,event_type = "tool_call", message = f"Calling tool {tool_name} with {tool_args}")
        result = handler(request) #this is where the tools are being executed
        print("tool call finisnhed, logging to db")

        event = {"type": "tool_result", "message" : f"Calling tool {tool_name} with {str(result.content)[:100]}..."}
        publish(conversation_id,event)

        AgentLog.objects.create(conversation = conv,event_type = "tool_result", message = f"Calling tool {tool_name} with {result.content}")
        return result

    support_agent = create_agent(
        model = llm,
        tools = SUPPORT_TOOLS + [escalate_to_manager],
        system_prompt = SUPPPORT_SYSTEM_PROMPT,
        checkpointer = checkpointer,
        middleware = [log_tool_calls_middleware]
    )
    
    result = support_agent.invoke(
        {"messages": [{"role": "user", "content": context}]},
        config=config,
    )
    final_reply = result["messages"][-1].content

    event = {"type": "final", "message" : final_reply}
    publish(conversation_id,event) 
    AgentLog.objects.create(conversation = conv,event_type = "final", message = final_reply)

    publish(conversation_id,DONE) 
    return final_reply


def run_manager_agent_langchain(case_summary, conversation_id):
    conv =Conversation.objects.get(id = conversation_id)
    event = {"type": "manager", "message" :f"case received for review : {case_summary[:200]}"}
    publish(conversation_id,event)
    AgentLog.objects.create(conversation = conv,event_type = "manager", message = f"case received for review : {case_summary[:200]}")

    @tool
    def assess_risk(user_id :int) -> dict:
        """
        "Consult the risk agent to assess fraud risk for a customer. Use this when refund request looks suspicious or customer has multiple refund requests. Pass the user_id to get a risk verdict."
        """
        return run_risk_agent_langchain(user_id, conversation_id)

    @wrap_tool_call
    def log_tool_calls_middleware(request, handler):
        print("about to log tool calls")
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]

        event = {"type": "manager", "message" : f"Calling tool {tool_name} with {tool_args}"}
        publish(conversation_id,event)

        AgentLog.objects.create(conversation = conv,event_type = "manager", message = f"Calling tool {tool_name} with {tool_args}")
        result = handler(request) #this is where the tools are being executed

    
        return result


    manager_agent = create_agent(
            model = llm,
            tools = [assess_risk],
            system_prompt = MANAGER_SYSTEM_PROMPT,
            # checkpointer = checkpointer,
            middleware = [log_tool_calls_middleware]
        )

    result = manager_agent.invoke(
        {"messages": [{"role": "user", "content": case_summary}]},
        # config=config,
    )

    decision = result["messages"][-1].content
    event = {"type": "manager", "message" :f"case received for review : {case_summary[:200]}"}
    publish(conversation_id,event)
    AgentLog.objects.create(conversation = conv,event_type = "manager", message = f"case received for review : {decision[:200]}")
    return decision


def run_risk_agent_langchain(user_id, conversation_id):
    conv = Conversation.objects.get(id = conversation_id)
    risk_messages = [
        {"role":"user", "content": f"Please assess the fraud risk for user ID {user_id}, Use your tool to get their profile and return a verdict"} #user is task giver
    ]
    event = {"type": "risk", "message" :f"starting fraud asessment for user {user_id}"}
    publish(conversation_id,event)

    @wrap_tool_call
    def log_tool_calls_middleware(request, handler):
        print("about to log tool calls")
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]

        event = {"type": "risk", "message" : f"Calling tool {tool_name} to get customer risk profile with {tool_args}"}
        publish(conversation_id,event)

        AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"Calling tool {tool_name} with {tool_args}")
        result = handler(request) #this is where the tools are being executed

    
        return result
    AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"starting fraud asessment for user {user_id}") 
    risk_agent = create_agent(
            model = llm,
            tools = [get_customer_risk_profile],
            system_prompt = RISK_SYSTEM_PROMPT,
            # checkpointer = checkpointer,
            middleware = [log_tool_calls_middleware]      
            )

    result = risk_agent.invoke(
        {"messages": [{"role": "user", "content": f"Please assess the fraud risk for user ID {user_id}, Use your tool to get their profile and return a verdict"}]},
        # config=config,
    )
    verdict = result["messages"][-1].content
    event = {"type": "risk", "message" :f"descion : {verdict}"}
    publish(conversation_id,event)
    
    AgentLog.objects.create(conversation = conv,event_type = "risk", message = f"descion : {verdict[:200]}") 
    return verdict