from django.contrib import admin
from support.models import *
# Register your models here.


admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(AgentLog)