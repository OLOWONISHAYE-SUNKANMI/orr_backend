from rest_framework import serializers
from admin_portal.models import StudioDocument


class StudioDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing documents — omits content payload."""

    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    folder_id = serializers.IntegerField(source='folder.id', read_only=True, allow_null=True)

    class Meta:
        model = StudioDocument
        fields = [
            'id',
            'title',
            'type',
            'folder_id',
            'owner_id',
            'is_ai_generated',
            'is_draft',
            'is_ai_reviewed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class StudioDocumentDetailSerializer(serializers.ModelSerializer):
    """Full serializer including content payload — used for single document fetch."""

    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    folder_id = serializers.IntegerField(source='folder.id', read_only=True, allow_null=True)

    class Meta:
        model = StudioDocument
        fields = [
            'id',
            'title',
            'type',
            'folder_id',
            'owner_id',
            'content',
            'is_ai_generated',
            'is_draft',
            'is_ai_reviewed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class StudioDocumentCreateSerializer(serializers.Serializer):
    """Validates POST body: { title, type, folderId? }"""

    title = serializers.CharField(max_length=500, default='Untitled')
    type = serializers.ChoiceField(choices=['doc', 'sheet', 'slide'])
    folderId = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_folderId(self, value):
        if value is not None:
            from admin_portal.models import VaultFolder
            if not VaultFolder.objects.filter(id=value).exists():
                raise serializers.ValidationError("Folder not found.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        folder_id = validated_data.pop('folderId', None)

        # Set default empty content based on document type
        doc_type = validated_data['type']
        if doc_type == 'doc':
            default_content = ''  # Empty HTML string
        elif doc_type == 'sheet':
            default_content = [
                {
                    'name': 'Sheet1',
                    'celldata': [],
                    'config': {},
                }
            ]
        elif doc_type == 'slide':
            default_content = []
        else:
            default_content = {}

        document = StudioDocument.objects.create(
            title=validated_data['title'],
            type=doc_type,
            folder_id=folder_id,
            owner=user,
            content=default_content,
        )
        return document


class StudioDocumentUpdateSerializer(serializers.Serializer):
    """Validates PUT body: { content, title? }"""

    content = serializers.JSONField(required=False)
    title = serializers.CharField(max_length=500, required=False)
    is_ai_generated = serializers.BooleanField(required=False)
    is_draft = serializers.BooleanField(required=False)
    is_ai_reviewed = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field to update must be provided.")
        return attrs

    def update(self, instance, validated_data):
        if 'content' in validated_data:
            instance.content = validated_data['content']
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'is_ai_generated' in validated_data:
            instance.is_ai_generated = validated_data['is_ai_generated']
        if 'is_draft' in validated_data:
            instance.is_draft = validated_data['is_draft']
        if 'is_ai_reviewed' in validated_data:
            instance.is_ai_reviewed = validated_data['is_ai_reviewed']
        instance.save()
        return instance
