from django.shortcuts import render, get_object_or_404
import json
from django.http import JsonResponse
import time
from orders.models import Order
from support.agents import run_support_agent
from .models import *
# Create your views here.

def chat(request, order_id):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message =  data.get("message")

        if not user_message:
            return JsonResponse({"error" : "Empty Message"}, status=400)
        
        order = get_object_or_404(Order, id = order_id, user = request.user)

        conversation, created = Conversation.objects.get_or_create(user = request.user, order = order)

        Message.objects.create(Conversation = conversation, role = "user", content = user_message)

        #send user message ad converation to LLM

        reply = run_support_agent(user_message, conversation.id, order.id, request.user.id)
        #store LLM reply
        Message.objects.create(Conversation = conversation, role = "assistant", content = reply)

        return JsonResponse({'reply' : reply})