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
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@method_decorator(csrf_exempt, name="dispatch")
class ChatbotAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ChatbotSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data.get("message")
            if not user_message:
                return Response({"error": "Message is empty"}, status=status.HTTP_400_BAD_REQUEST)

            try:
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

                response = requests.post(url, headers=headers, data=json.dumps(payload))
                response.raise_for_status()  # لو في خطأ هيرمي Exception

                data = response.json()
                bot_reply = data["choices"][0]["message"]["content"]

                return Response({"reply": bot_reply}, status=status.HTTP_200_OK)

            except requests.exceptions.RequestException as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except KeyError:
                return Response({"error": "Unexpected response from OpenAI API"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
