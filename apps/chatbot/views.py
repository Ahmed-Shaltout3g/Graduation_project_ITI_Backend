# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .serializers import ChatbotSerializer
from openai import OpenAI
import os
import json
import traceback
from apps.products.models import Product, Category

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)


def search_products(query):
    """
    Search for products in the database based on title and description
    """
    # Clean and prepare search query
    query = query.lower().strip()

    # Search in title first (more specific)
    products = Product.objects.filter(status='active').filter(
        title__icontains=query
    ).select_related('category')[:10]

    if len(products) == 0:
        # Also search in description if no title matches
        products = Product.objects.filter(status='active').filter(
            description__icontains=query
        ).select_related('category')[:10]

    if len(products) == 0:
        # Also search in category name
        products = Product.objects.filter(status='active').filter(
            category__name__icontains=query
        ).select_related('category')[:10]

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "condition": product.condition,
            "category": product.category.name if product.category else "No category",
            "university": product.university or "Not specified",
            "faculty": product.faculty or "Not specified",
            "seller": {
                "id": product.seller.id,
                "name": product.seller.first_name or product.seller.username,
                "username": product.seller.username,
            } if product.seller else {"name": "Unknown Seller"}
        })

    return results


def get_personalized_recommendations(user):
    """
    Get products recommended for the user's location, university and faculty
    Only recommend if there's a location/university/faculty match
    """
    location = getattr(user, 'location', '') or ''
    university = getattr(user, 'university', '') or ''
    faculty = getattr(user, 'faculty', '') or ''

    print(f"DEBUG: Getting recommendations for {location}, {university}, {faculty}")

    if not location and not university and not faculty:
        # No location/university/faculty info, return empty recommendations
        return []

    # First try products from sellers with same location, university and faculty
    products = Product.objects.filter(status='active').filter(
        seller__location__icontains=location,
        seller__university__icontains=university,
        seller__faculty__icontains=faculty
    ).select_related('category', 'seller')[:5]

    # If not enough, add products from same university and faculty (ignore location)
    if len(products) < 3:
        university_products = Product.objects.filter(status='active').filter(
            seller__university__icontains=university,
            seller__faculty__icontains=faculty
        ).exclude(id__in=[p.id for p in products]).select_related('category', 'seller')[:3]

        products = list(products) + list(university_products)
        products = products[:5]  # Limit to 5

    # If still not enough, add products from same university (ignore faculty)
    if len(products) < 3:
        university_only_products = Product.objects.filter(status='active').filter(
            seller__university__icontains=university
        ).exclude(id__in=[p.id for p in products]).select_related('category', 'seller')[:3]

        products = list(products) + list(university_only_products)
        products = products[:5]  # Limit to 5

    # Don't fall back to general products - only recommend when there's a meaningful match
    # If len(products) == 0 at this point, return empty list

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "condition": product.condition,
            "category": product.category.name if product.category else "No category",
            "university": product.university or "Not specified",
            "faculty": product.faculty or "Not specified",
            "seller": {
                "id": product.seller.id,
                "name": product.seller.first_name or product.seller.username,
                "username": product.seller.username,
            } if product.seller else {"name": "Unknown Seller"}
        })

    return results


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            serializer = ChatbotSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            user_message = serializer.validated_data.get("message")

            # Check if this is a greeting or if we should provide recommendations
            should_provide_recommendations = any(greeting in user_message.lower() for greeting in
                ['hello', 'hi', 'welcome', 'chatbot', 'recommendation', 'suggestion'])
            should_provide_recommendations = should_provide_recommendations or len(user_message.strip()) < 10

            if not OPENAI_API_KEY:
                return Response(
                    {"error": "OpenAI API key not configured"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            client = OpenAI(api_key=OPENAI_API_KEY)

            # Define functions for product search and personalized recommendations
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_products",
                        "description": "Search for available college tools and supplies in our e-commerce store",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The tool or item to search for (e.g., ruler, calculator, thermometer)",
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_personalized_recommendations",
                        "description": "Get personalized product recommendations based on the user's location, university and faculty",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            ]

            system_prompt = """
            You are a helpful AI assistant for a college supplies e-commerce website called "Classifieds".
            You help students find and purchase tools they need for their studies.

            CRITICAL: When a user asks about ANY tools, supplies, or items for sale, ALWAYS use the search_products function first. Do not answer from memory or make up information.

            When a user greets you or opens the chat, provide personalized recommendations using get_personalized_recommendations if they have university/faculty info.

            Available tools and supplies include: rulers, calculators, thermometers, notebooks, pens, pencils, erasers, geometry sets, laboratory equipment, measuring tools, and many other study supplies.

            When products are found:
            - Take direct action: Always navigate the user to the product details page automatically
            - The frontend will handle the automatic navigation when it receives products data
            - Say something brief like "Found it! Taking you to the product details..." followed by navigation

            IMPORTANT: When products are found, the frontend should automatically redirect to show product details. Include navigation message in response.

            If no products are found, suggest alternatives like browsing categories.
            """

            # Always enable tools for this assistant
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini",  # Use a cost-effective model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                tools=tools,
                tool_choice="auto",  # Let AI decide when to use tools
                temperature=0.7,
                max_tokens=500
            )

            response_message = chat_completion.choices[0].message

            # Track if we had a search function call
            searched_products = None
            search_query = None

            # Handle personalized recommendations for new users
            if should_provide_recommendations:
                # Force personalized recommendations for greetings
                print("DEBUG: Providing personalized recommendations")
                personalized_products = get_personalized_recommendations(request.user)

                if personalized_products:  # Only provide recommendations if there are matching products
                    location = getattr(request.user, 'location', '')
                    university = getattr(request.user, 'university', '')
                    faculty = getattr(request.user, 'faculty', '')

                    if location or university or faculty:
                        location_str = f" in {location}" if location else ""
                        university_str = f" at {university}" if university else ""
                        faculty_str = f", {faculty}" if faculty else ""
                        bot_reply = f"For recommendations{location_str}{university_str}{faculty_str}:\n"
                    else:
                        bot_reply = "Here are some recommendations for you:\n"

                    for product in personalized_products[:3]:  # Show up to 3
                        bot_reply += f"We have {product['title']} available from {product['seller']['name']} for ${product['price']} ({product['condition']} condition).\n"

                    return Response({
                        "reply": bot_reply.strip(),
                        "products": personalized_products[:3]  # Include products for auto-navigation
                    }, status=status.HTTP_200_OK)
                else:
                    # No matching products found, provide a general greeting instead
                    return Response({
                        "reply": "Hello! I'm here to help you find college supplies. What are you looking for today?",
                        "products": []
                    }, status=status.HTTP_200_OK)

            # Check if the model wants to call a function
            if response_message.tool_calls:
                # Call the function
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "search_products":
                        # Parse the arguments
                        args = json.loads(tool_call.function.arguments)
                        search_query = args.get("query", "")
                        print(f"DEBUG: Searching for: {search_query}")

                        # Search for products
                        searched_products = search_products(search_query)
                        print(f"DEBUG: Found products: {len(searched_products)}")

                        # Add the function result to the conversation
                        chat_completion = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message},
                                response_message,
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(searched_products)
                                }
                            ],
                            temperature=0.7,
                            max_tokens=500
                        )

                        response_message = chat_completion.choices[0].message
                        print(f"DEBUG: Final response content: '{response_message.content}'")
            else:
                print("DEBUG: No tool calls made by AI")

            # Extract the final response
            bot_reply = response_message.content

            # Prepare response data
            response_data = {"reply": bot_reply}

            # Always include product data if we searched (even if AI response is empty)
            if searched_products is not None:
                response_data["products"] = searched_products
                print(f"DEBUG: Including {len(searched_products)} products in response")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response(
                {
                    "error": "internal_server_error",
                    "detail": str(exc) if settings.DEBUG else "Server error",
                    "trace": traceback.format_exc() if settings.DEBUG else None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
