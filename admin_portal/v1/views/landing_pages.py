from rest_framework import generics
from admin_portal.models_cms import CustomLandingPage
from rest_framework import serializers
from admin_portal.permissions import CanCreateContent

class CustomLandingPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomLandingPage
        fields = '__all__'

class CustomLandingPageListView(generics.ListCreateAPIView):
    queryset = CustomLandingPage.objects.all()
    serializer_class = CustomLandingPageSerializer
    permission_classes = [CanCreateContent]

class CustomLandingPageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomLandingPage.objects.all()
    serializer_class = CustomLandingPageSerializer
    permission_classes = [CanCreateContent]
    lookup_field = 'slug'
