# # middleware.py
# from django.http import Http404
# from app.cafe.models import Cafe

# class CafeTenantMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         host = request.get_host().split(':')[0]
#         subdomain = host.split('.')[0] 
        
#         try:
#             request.cafe = Cafe.objects.get(slug=subdomain, is_active=True)
#         except Cafe.DoesNotExist:
#             raise Http404("Cafe not found")

#         response = self.get_response(request)
#         return response

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cafe = request.headers.get("X-Cafe")
        return self.get_response(request)