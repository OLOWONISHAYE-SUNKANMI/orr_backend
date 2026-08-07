from rest_framework import serializers
from pm.models import PMProject, PMProjectDocument

class ClientProjectListSerializer(serializers.ModelSerializer):
    service_category_display = serializers.CharField(source='get_service_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PMProject
        fields = [
            'id', 'project_id', 'title', 'service_category_display', 
            'status', 'status_display', 'target_deadline', 'created_at'
        ]

class ClientProjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PMProjectDocument
        fields = ['id', 'document_type', 'file_name', 'file', 'uploaded_at']

class ClientProjectDetailSerializer(serializers.ModelSerializer):
    service_category_display = serializers.CharField(source='get_service_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    documents = serializers.SerializerMethodField()
    
    class Meta:
        model = PMProject
        fields = [
            'id', 'project_id', 'title', 'service_category', 'service_category_display',
            'status', 'status_display', 'client_objective', 'proposed_scope',
            'expected_deliverable', 'target_deadline', 'created_at', 'documents'
        ]

    def get_documents(self, obj):
        # Client can only see certain documents, maybe client_uploads or linked_client_doc or final deliverables
        # Assuming we just show documents with visibility='client_and_consultant' or 'client_only', 
        # but PMProjectDocument doesn't have visibility. Let's just return linked_client_doc for now.
        docs = PMProjectDocument.objects.filter(project=obj, document_type__in=['linked_client_doc', 'other'])
        return ClientProjectDocumentSerializer(docs, many=True).data
