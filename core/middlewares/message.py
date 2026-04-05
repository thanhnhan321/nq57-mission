import json
import time

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.contrib.messages import get_messages

from utils.json import jsonify

class MessageMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)


    async def __call__(self, request):
        response = await self.get_response(request)
        hx_trigger = request.headers.get('HX-Trigger', {})
        if hx_trigger:
            hx_trigger = json.loads(hx_trigger) if hx_trigger.startswith('{') else { hx_trigger: True}
        hx_trigger['new-message'] = [
            {
                'message': message.message,
                'level': message.level,
                'id': time.time_ns()
            } for message in get_messages(request)
        ]
        response.headers['HX-Trigger'] = jsonify(hx_trigger)
        return response