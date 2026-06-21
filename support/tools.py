from orders.models import Order, RefundRequest
from django.utils import timezone
from support.tracking_data import DELIVERY_DATA


def get_order_details(order_id):
    try:
        order = Order.objects.get(id = order_id)
        return {
            "order_id" : order.id,
            "product_name" : order.product_name,
            "amount" : str(order.amount),
            "status" : order.status,
            "carrier" : order.carrier,
            "tracking_number" : order.tracking_number,
            "delivery_address" : order.delivery_address,
            "order_on" : order.created_at.strftime("%d %b %Y"),
            "days_since_order" : (timezone.now() - order.created_at).days, 
        }
    except Order.DoesNotExist:
        return {'error': f"Order #{order_id} not found"}


def get_refund_history(user_id):
    refunds = RefundRequest.objects.filter(user = user_id).order_by("-created_at")
    

    history = []
    for refund in refunds:
        history.append({
            "order_id" : refund.order.id,
            "product" : refund.order.product_name,
            "reason" : refund.reason,
            'status' : refund.status,
            "requested_on": refund.created_at.strftime("%d %b %Y"),
        })

    return {
        "total_refund_request" : len(history),
        "history" : history
    }


