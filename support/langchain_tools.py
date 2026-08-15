from langchain.tools import tool
from support.tools import get_order_details as _get_order_details, get_refund_history as _get_refund_history, check_delivery_status as _check_delivery_status, get_customer_risk_profile as _get_customer_risk_profile, search_knowledge_base as _search_knowledge_base

@tool    
def get_order_details(order_id :int) -> dict: # here -> dict means in which formot it should return the data, in this case it should return a dictionary
    """
    Fetch complete order details including status, carrier, 
    tracking number, and days since the order was placed. 
    Use this when the customer mentions their order or asks
    about delivery.
    """
    return _get_order_details(order_id)

@tool
def get_refund_history(user_id :int) -> dict:
    """
     "Retrieve the refund request history for a user. "
    "Returns the total number of refund requests along with "
    "details such as order ID, product name, refund reason, "
    "current status, and request date."
    """
    return _get_refund_history(user_id)

@tool
def check_delivery_status(tracking_number :str, carrier :str) -> dict:
    """
    "Retrieve the current delivery status of a shipment using "
    "its tracking number and carrier."
    """
    return _check_delivery_status(tracking_number, carrier)

@tool
def search_knowledge_base(query :str) -> dict:
    """
     "Search the company knowledge base for information related to refund policies, "
    "warranty terms, product FAQs, troubleshooting guides, shipping policies, "
    "and other support documentation. Use this tool whenever the user's question "
    "requires factual information that should come from the knowledge base. "
    "Base your response only on the retrieved information. If no relevant "
    "information is found, state that the knowledge base does not contain the answer."
    """
    return _search_knowledge_base(query)

@tool
def get_customer_risk_profile(user_id :int) -> dict:
    """
     "Get complete risk profile for a customer including order history, refund patterns and ratio. Use this to assess fraud risk."
    """
    return _get_customer_risk_profile(user_id)