from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from ..serializers.contact import ContactMessageSerializer


@extend_schema(tags=["main page"])
class ContactMessageView(APIView):
    permission_classes = [AllowAny]  # public contact form
    serializer_class = ContactMessageSerializer

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Message sent successfully"}, status=200)
        return Response(serializer.errors, status=400)
