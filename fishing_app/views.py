import hashlib
import json
import math
import time
from datetime import datetime
import random

import pika
import requests

from django.conf import settings
import redis
from django.db import transaction
from django.db.models import Sum, F

# Create your views here.

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status

from .models import User, UserInventory, Fish, FishCatched, ShopItem, ShoppedItem
from rest_framework.views import APIView
from rest_framework.response import Response
from decimal import Decimal
from .tasks import send_purchase_confirmation_email

class FishCatchedSerializer(serializers.ModelSerializer):
    fish_type_name = serializers.CharField(source='fish_type.type')

    class Meta:
        model = FishCatched
        fields = ['id', 'fish_type_name', 'weight', 'rarity_level', 'image_url', 'caught_at', 'price']

class UserInventorySerializer(serializers.ModelSerializer):
    fish_catched = FishCatchedSerializer(many=True)

    class Meta:
        model = UserInventory
        fields = ['fish_catched', 'total_value']

class ChatGeneralView(APIView):
    def post(self, request):
        api_key = settings.OPENAI_API_KEY
        message = request.data.get('message')
        if not message:
            return JsonResponse({
                'code': 400,
                'message': 'Message is required'
            })
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'user', 'content': message}
            ]
        }
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            filtered_result = result['choices'][0]['message']['content'] if result.get('choices') else 'No content'
            return Response({"message": filtered_result}, status=200)
        else:
            return Response(
                {"message": "Failed to get a response from OpenAI"},
                status=response.status_code
            )


class ChatCommandView(APIView):
    @csrf_exempt
    def post(self, request):
        api_key = settings.OPENAI_API_KEY
        message = request.data.get('message')
        key_words = ['fish', 'play', 'sell']
        key_words_str = ",".join(key_words)
        prompt = f'Given the keywords [{key_words_str}], please match them to the message: "{message}" and return the matched keywords. And return the closest matched keyword. Cannot return none. Just return the keyword without any description!'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            filtered_result = result['choices'][0]['message']['content'] if result.get('choices') else 'No content'
            return Response({"message": filtered_result}, status=200)
        else:
            return Response(
                {"message": "Failed to get a response from OpenAI"},
                status=response.status_code
            )

class ChatDrawView(APIView):
    @csrf_exempt
    def post(self, request):
        try:
            api_key = settings.OPENAI_API_KEY  # 从 settings 文件中获取 OpenAI API 密钥

            prompt = request.data.get('prompt')

            # 检查 prompt 是否存在
            if not prompt:
                return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)

            # 根据样例构建详细的 prompt
            detailed_prompt = f"Given the keywords [{prompt}], draw an image that relates to the keywords - requirements: Note: the image created should be more realistic, rather than in cartoon style."

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            data = {
                'prompt': detailed_prompt,
                'n': 1,
                'size': '1024x1024'
            }

            response = requests.post('https://api.openai.com/v1/images/generations', headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                image_url = result.get('data', [])[0].get('url', 'No content')
                return Response({'image_url': image_url}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Failed to generate image'}, status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# User views
class UserExistView(APIView):
    def get(self, request):
        user_id = request.GET.get('user_id')
        user = User.objects.filter(user_id=user_id).first()
        if user:
            return JsonResponse({
                'code': 200,
                'msg': 'User exists',
                'data': {'exist': 1}
            })
        else:
            return JsonResponse({
                'code': 404,
                'msg': 'User does not exist',
                'data': {'exist': 0}
            })

class CreateUserView(APIView):
    @csrf_exempt
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'code': 400, 'msg': 'Invalid JSON'}, status=400)

        user_id = data.get('user_id')
        user_name = data.get('user_name')

        if not user_id:
            return JsonResponse({'code': 400, 'msg': 'parameter error'}, status=400)
        if User.objects.filter(user_id=user_id).exists():
            return JsonResponse({'code': 409, 'msg': 'already exist'}, status=409)

        User.objects.create(
            user_id=user_id,
            user_name=user_name,
            coins=1000.00,
            diamonds=100.00,
            level=1,
            current_experience=0,
            experience_for_next_level=1,
            rod_type='Plastic Rod',
            fish_inventory=[]
        )
        return JsonResponse({'code': 201, 'msg': 'success'}, status=201)


class UserBasicView(APIView):
    @csrf_exempt
    def get(self, request):
        user_id = request.GET.get('user_id')
        user = User.objects.filter(user_id=user_id).first()

        if user:
            return JsonResponse({
                'code': 200,
                'data': {
                    'user_id': user.user_id,
                    'user_name': user.user_name,
                }
            })
        else:
            return JsonResponse({
                'code': 404,
                'msg': 'User does not exist'
            })

class UserFinanceView(APIView):
    def get(self, request):
        user_id = request.GET.get('user_id')
        user = User.objects.filter(user_id=user_id).first()

        if user:
            return JsonResponse({
                'code': 200,
                'data': {
                    'coins': user.coins,
                    'diamonds': user.diamonds,
                }
            })
        else:
            return JsonResponse({
                'code': 404,
                'msg': 'User does not exist'
            })

class UserLevelView(APIView):
    def get(self, request):
        user_id = request.GET.get('user_id')
        user = User.objects.filter(user_id=user_id).first()

        if user:
            return JsonResponse({
                'code': 200,
                'data': {
                    'level': user.level,
                    'current_experience': user.current_experience,
                    'experience_for_next_level': user.experience_for_next_level
                }
            })
        else:
            return JsonResponse({
                'code': 404,
                'msg': 'User does not exist'
            })


class UserInventoryView(APIView):
    @csrf_exempt
    def get(self, request):
        user_id = request.GET.get('user_id')
        user = User.objects.filter(user_id=user_id).first()
        if not user:
            return JsonResponse({'code': 400, 'message': 'User not found'})

        try:
            # Fetch a single instance of UserInventory
            inventory = UserInventory.objects.get(user=user)
        except UserInventory.DoesNotExist:
            return Response({'code': 404, 'message': 'Inventory does not exist'}, status=404)

        serializer = UserInventorySerializer(inventory)
        return Response({
            'code': 200,
            'data': {
                'user_name': user.user_name,
                'inventory': serializer.data
            }
        })



def user_achievement(request):
    return JsonResponse({"message": "User achievement info"})


class FishCatchView(APIView):
    @csrf_exempt
    def post(self, request):
        user_id = request.data.get('user_id')
        user = User.objects.filter(user_id=user_id).first()

        if not user:
            return JsonResponse({'code': 400, 'message': 'User not found'})

        fish_list = Fish.objects.filter(status=True)
        fish_chosen = self.probability_helper(fish_list)
        fish_weight = self.weight_helper(fish_chosen)
        url = self.image_helper(fish_chosen, fish_weight)
        rarity_level = self.level_helper(fish_chosen, fish_weight)
        price = Decimal('20.00')

        # Retrieve or create the user's inventory
        inventory, created = UserInventory.objects.get_or_create(
            user=user,
            defaults={'total_value': Decimal('0.00')}
        )

        # Create the FishCatched instance
        fish_catched = FishCatched.objects.create(
            user=user,
            fish_type=fish_chosen,
            weight=fish_weight,
            rarity_level=rarity_level,
            image_url=url,
            caught_at=datetime.now(),
            price=price
        )

        # Add the caught fish to the inventory and update total value
        inventory.fish_catched.add(fish_catched)
        inventory.total_value += price
        inventory.save()

        return JsonResponse({
            'code': 200,
            'fish_catched': {
                'id': fish_catched.id,
                'type': fish_catched.fish_type.type,
                'weight': fish_catched.weight,
                'rarity_level': fish_catched.rarity_level,
                'image_url': fish_catched.image_url,
                'caught_at': fish_catched.caught_at,
                'price': str(fish_catched.price)
            }
        })

    def probability_helper(self, fish_list):
        probability_sum = fish_list.aggregate(total_prob=Sum('probability'))['total_prob']
        random_prob = random.random() * probability_sum
        cur_sum = 0
        for fish in fish_list:
            cur_sum += fish.probability
            if cur_sum >= random_prob:
                return fish
        return fish_list.last()

    def weight_helper(self, fish):
        # mean = fish.get('mean', 1.75)
        # standard_deviation = fish.get('standard_deviation', 0.625)
        mean = getattr(fish, 'mean', 1.75)
        standard_deviation = getattr(fish, 'standard_deviation', 0.625)
        u1 = random.random()
        u2 = random.random()
        rand_std_normal = math.sqrt(-2 * math.log(u1)) * math.sin(2 * math.pi * u2)
        return mean + standard_deviation * rand_std_normal

    def image_helper(self, fish, weight):
        return '*this is a sample link*'

    def level_helper(self, fish, weight):
        s_weight, a_weight, b_weight, c_weight = fish.s_weight, fish.a_weight, fish.b_weight, fish.c_weight
        if weight > s_weight:
            return "SS"
        elif weight > a_weight:
            return "S"
        elif weight > b_weight:
            return "A"
        elif weight > c_weight:
            return "B"
        else:
            return "C"


class FishSellView(APIView):
    @csrf_exempt
    def post(self, request):
        user_id = request.data.get('user_id')
        user = User.objects.filter(user_id=user_id).first()

        if not user:
            return JsonResponse({'code': 400, 'message': 'User not found'})

        try:
            # Fetch a single instance of UserInventory
            inventory = UserInventory.objects.get(user=user)
        except UserInventory.DoesNotExist:
            return Response({'code': 404, 'message': 'Inventory does not exist'}, status=404)

        revenue_by_type_map = {}

        with transaction.atomic():
            for fish_catched in inventory.fish_catched.all():
                fish_type = fish_catched.fish_type.type  # Get the type of the fish
                price = fish_catched.price

                # Accumulate revenue for each fish type
                if fish_type in revenue_by_type_map:
                    revenue_by_type_map[fish_type] += price
                else:
                    revenue_by_type_map[fish_type] = price

            total_value = inventory.total_value
            UserInventory.objects.filter(user=user).delete()
            User.objects.filter(user_id=user_id).update(
                coins=F('coins') + total_value
            )
        revenue_by_type_list = [{'type': fish_type, 'revenue': revenue} for fish_type, revenue in revenue_by_type_map.items()]
        return JsonResponse({
            'code': 200,
            'total_revenue': total_value,
            'revenue_by_type': revenue_by_type_list
        })


class FishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fish
        fields = '__all__'


class FishCreateView(APIView):
    @csrf_exempt
    def post(self, request):
        # 获取请求中的数据
        fish_data = request.data

        # 使用序列化器验证并保存数据
        serializer = FishSerializer(data=fish_data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Fish type created successfully!", "data": serializer.data}, status=200)
        else:
            return Response({"errors": serializer.errors}, status=400)


class ShopListView(APIView):
    @csrf_exempt
# Shop views
    def get(self, request):
        items = list(ShopItem.objects.all().values())

        return JsonResponse({
            'code': 200,
            'data': items
        })

class AddShopItemView(APIView):
    @csrf_exempt
    def post(self, request):
        name = request.data.get('name')
        category = request.data.get('category')
        coins = request.data.get('coins')
        diamonds = request.data.get('diamonds')

        # check for duplicate
        exist_item = ShopItem.objects.filter(name=name)
        if exist_item:
            return JsonResponse({'code': 400, 'message': 'Item already exists'}, status=400)

        ShopItem.objects.create(
            name=name, category=category, coins=coins, diamonds=diamonds
        )
        return JsonResponse({
            'code': 200,
            'message': f'Successfully created shop item {name}'
        })

class DeleteShopItemView(APIView):
    @csrf_exempt
    def delete(self, request):
        name = request.data.get('name')
        ShopItem.objects.filter(name=name).delete()
        return JsonResponse({
            'code': 200,
            'message': f'Successfully deleted shop item {name}'
        })

redis_instance = redis.Redis(host='localhost', port=6379, db=0)
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='shop_purchase_queue')

class ShopPurchaseView(APIView):

    def determine_currency(self, category):
        diamond_categories = ['Time Acceleration Card', 'Food']
        return 'diamonds' if category in diamond_categories else 'coins'

    @csrf_exempt
    def post(self, request):
        user_id = request.data.get('user_id')
        item_name = request.data.get('item_name')
        category = request.data.get('category')

        lock_key = f"shop_items_lock_{user_id}_{item_name}"
        lock = redis_instance.set(lock_key, 1, nx=True, ex=10)  # 锁定10秒，避免并发操作

        if not lock:
            return Response({"message": "Too many requests! Try again later!"}, status=429)

        try:
            user = User.objects.filter(user_id=user_id).first()
            if not user:
                return Response({"message": "User not found"}, status=404)

            item = ShopItem.objects.filter(category=category, name=item_name).first()
            if not item:
                return Response({"message": "Item not found"}, status=404)

            currency = self.determine_currency(category)
            price = getattr(item, currency)

            if getattr(user, currency) < price:
                return Response({"message": f"User does not have enough {currency}"}, status=400)

            setattr(user, currency, getattr(user, currency) - price)
            user.save()

            shopped_item, created = ShoppedItem.objects.get_or_create(
                user_id=user_id,
                product_type=category,
                product_name=item_name,
                defaults={'quantity': 1}
            )

            if not created:
                shopped_item.quantity += 1
                shopped_item.save()

            purchase_info = {
                'user_id': user_id,
                'item_name': item_name,
                'category': category,
                'price': price
            }
            channel.basic_publish(
                exchange='',
                routing_key='shop_purchase_queue',
                body=json.dumps(purchase_info)
            )
            send_purchase_confirmation_email.delay(user_id, item_name, category)

            return Response({"message": "Successfully purchased item!"})

        finally:
            redis_instance.delete(lock_key)

        # user = User.objects.filter(user_id=user_id).first()
        # if not user:
        #     return Response({"message": "User not found"}, status=404)
        #
        # item = ShopItem.objects.filter(category=category, name=item_name).first()
        # if not item:
        #     return Response({"message": "Item not found"}, status=404)
        #
        # currency = self.determine_currency(category)
        # price = getattr(item, currency)
        #
        # if getattr(user, currency) < price:
        #     return Response({"message": f"User does not have enough {currency}"}, status=400)
        #
        # setattr(user, currency, getattr(user, currency) - price)
        # user.save()
        #
        # shopped_item, created = ShoppedItem.objects.get_or_create(
        #     user_id=user_id,
        #     product_type=category,
        #     product_name=item_name,
        #     defaults={'quantity': 1}
        # )
        #
        # if not created:
        #     shopped_item.quantity += 1
        #     shopped_item.save()
        #
        # return Response({"message": "Successfully purchased item!"})

class UserShoppedItemView(APIView):
    @csrf_exempt
    def get(self, request):
        user_id = request.data.get('user_id')
        user = User.objects.filter(user_id=user_id).first()
        print(user)
        if not user:
            return Response({"message": "User not found"}, status=404)
        items = list(ShoppedItem.objects.filter(user_id=user_id).all().values())
        return JsonResponse({
            'code': 200,
            'data': items
        })


@csrf_exempt
def generate_token(request):
    timestamp = str(int(time.time()))
    password = getattr(settings, 'API_PASSWORD', 'default_password')
    hashed = hashlib.md5(f"{password}{timestamp}{password}".encode()).hexdigest()
    return JsonResponse({
        'token': hashed,
        'timestamp': timestamp,
    })

# 453ba182f8206bfdacfa914e0753bb0c
# 1724030834
# curl -X GET "http://localhost:8000/user/basic/?user_id=1" \
# -H "token: 453ba182f8206bfdacfa914e0753bb0c" \
# -H "timestamp: 1724030834"
