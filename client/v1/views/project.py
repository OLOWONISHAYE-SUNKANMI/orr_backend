from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pm.models import PMProject
from ..serializers.project import ClientProjectListSerializer, ClientProjectDetailSerializer
from common.response import api_response
from drf_yasg.utils import swagger_auto_schema

class ClientProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Client Projects"],
        operation_summary="List Client Projects",
        operation_description="Returns a list of projects associated with the authenticated client."
    )
    def get(self, request):
        if not hasattr(request.user, 'client_profile'):
            return Response(api_response(success=False, message="User is not a client."), status=status.HTTP_403_FORBIDDEN)
        
        # Only show projects that are submitted, active, completed, etc. Not drafts.
        # But wait, if PM creates a project and submits it, client sees it. 
        # So we exclude 'draft' status.
        projects = PMProject.objects.filter(client=request.user.client_profile).exclude(status='draft')
        
        serializer = ClientProjectListSerializer(projects, many=True)
        return Response(api_response(data=serializer.data))

class ClientProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Client Projects"],
        operation_summary="Get Client Project Detail",
        operation_description="Returns details of a specific project associated with the authenticated client."
    )
    def get(self, request, pk):
        if not hasattr(request.user, 'client_profile'):
            return Response(api_response(success=False, message="User is not a client."), status=status.HTTP_403_FORBIDDEN)
            
        try:
            project = PMProject.objects.get(pk=pk, client=request.user.client_profile)
        except PMProject.DoesNotExist:
            return Response(api_response(success=False, message="Project not found."), status=status.HTTP_404_NOT_FOUND)
            
        serializer = ClientProjectDetailSerializer(project)
        return Response(api_response(data=serializer.data))
