import time
import hashlib
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        logger.debug("APITimestampMiddleware initialized")

    def __call__(self, request):
        # List of paths to exempt from the middleware
        exempt_paths = ['/user/generate-token/']

        # If the request path is in the exempt list, skip the middleware logic
        if request.path in exempt_paths:
            return self.get_response(request)

        logger.debug("APITimestampMiddleware called")

        # 获取请求头中的 token 和 timestamp
        token = request.headers.get('token')
        timestamp = request.headers.get('timestamp')
        password = getattr(settings, 'API_PASSWORD', 'default_password')  # 从 settings 中获取密码

        if not token or not timestamp:
            return JsonResponse({'code': 400, 'msg': 'Missing token or timestamp', 'data': {}}, status=400)

        # 生成正确的 token
        correct_token = hashlib.md5(f"{password}{timestamp}{password}".encode()).hexdigest()

        # 验证时间戳和 token
        if (time.time() - int(timestamp) > 600) or (time.time() - int(timestamp) < 0) or token != correct_token:
            return JsonResponse({'code': 401, 'msg': 'Token invalid', 'data': {}}, status=401)

        return self.get_response(request)
