from rest_framework import serializers
from admin_portal.models import ClientDocument


class ClientDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    start_date = serializers.DateTimeField(source="created_at", format="%m/%d", read_only=True)
    end_date = serializers.DateTimeField(source="updated_at", format="%m/%d", read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = ClientDocument
        fields = [
            "id",
            "title",
            "description",
            "document_type",
            "start_date",
            "end_date",
            "file_url",
            "is_favorited",
        ]

    def get_file_url(self, obj):
        if obj.document:
            try:
                from decouple import config
                url = obj.document.url
                if url.startswith('/'):
                    api_url = config('BACKEND_URL', default='https://orr-backend-105825824472.asia-southeast2.run.app')
                    return f"{api_url.rstrip('/')}{url}"
                return url
            except Exception:
                return None
        return None

    def get_is_favorited(self, obj):
        user = self.context["request"].user
        return obj.favorited_by.filter(user=user).exists()
