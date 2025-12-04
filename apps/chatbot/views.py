# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import ChatbotSerializer
import requests
import os
import json
from django.conf import settings
import traceback

# Read OpenAI API key from environment or Django settings. Do NOT hardcode keys here.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)

@method_decorator(csrf_exempt, name="dispatch")
class ChatbotAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ChatbotSerializer(data=request.data)
            if serializer.is_valid():
                user_message = serializer.validated_data.get("message")
                if not user_message:
                    return Response({"error": "Message is empty"}, status=status.HTTP_400_BAD_REQUEST)
                if not OPENAI_API_KEY:
                    return Response({"error": "OpenAI API key not configured on server"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                payload = {
                    "model": "gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }

                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

                # Handle common auth failure explicitly
                if response.status_code == 401:
                    return Response({"error": "Unauthorized with OpenAI API - check API key"}, status=status.HTTP_502_BAD_GATEWAY)

                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    # Return OpenAI error message if present
                    try:
                        err = response.json()
                    except Exception:
                        err = {"detail": str(e)}
                    return Response({"error": err}, status=status.HTTP_502_BAD_GATEWAY)

                data = response.json()
                try:
                    bot_reply = data["choices"][0]["message"]["content"]
                except Exception:
                    return Response({"error": "Unexpected response from OpenAI API", "raw": data}, status=status.HTTP_502_BAD_GATEWAY)

                return Response({"reply": bot_reply}, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            tb = traceback.format_exc()
            if settings.DEBUG:
                return Response({"error": "internal_server_error", "detail": str(exc), "trace": tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"error": "internal_server_error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
