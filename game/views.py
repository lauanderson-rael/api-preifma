from rest_framework.views import APIView
from rest_framework.response import Response

class PlaceholderView(APIView):
    def get(self, request):
        return Response({"message": "Banco de dados em manutenção para migração."})
