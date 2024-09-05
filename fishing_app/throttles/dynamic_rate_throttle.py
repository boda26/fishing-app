from rest_framework.throttling import UserRateThrottle
import os


class DynamicRateThrottle(UserRateThrottle):
    def allow_request(self, request, view):

        load_average = os.getloadavg()[0]

        if load_average > 2.0:
            self.rate = '10/hour'  # 降低速率为每小时10
        else:
            self.rate = '1000/day'  # 否则使用正常的速率

        return super().allow_request(request, view)
