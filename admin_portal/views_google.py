from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Client, ClientDocument, VaultFolder
from services.google_service import GoogleService
from django.shortcuts import get_object_or_404
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_google_doc(request):
    title = request.data.get('title', 'Untitled Document')
    client_id = request.data.get('client_id')
    doc_type = request.data.get('type', 'google_doc') # google_doc or google_sheet
    
    client = get_object_or_404(Client, id=client_id)
    
    # Track sandbox mode flag
    is_sandbox_mode = False
    file_id = None
    
    # 1. Create the Doc/Sheet/Slide
    if doc_type == 'google_sheet':
        try:
            gs = GoogleService(service_type='sheets')
            doc = gs.create_sheet(title)
            file_id = doc.get('spreadsheetId')
        except Exception as e:
            print(f"Google Sheets API failed. Falling back to Sandbox Mode. Error: {e}")
            is_sandbox_mode = True
            file_id = f"mock_sheet_{uuid.uuid4().hex[:12]}"
    elif doc_type == 'google_slide':
        try:
            # Create slides using drive API mimeType (simplest way)
            drive_gs = GoogleService(service_type='drive')
            doc_metadata = {'name': title, 'mimeType': 'application/vnd.google-apps.presentation'}
            doc = drive_gs.service.files().create(body=doc_metadata, fields='id').execute()
            file_id = doc.get('id')
        except Exception as e:
            print(f"Google Slides API failed. Falling back to Sandbox Mode. Error: {e}")
            is_sandbox_mode = True
            file_id = f"mock_slide_{uuid.uuid4().hex[:12]}"
    else: # Default to google_doc
        try:
            gs = GoogleService(service_type='docs')
            doc = gs.create_doc(title)
            file_id = doc.get('documentId')
        except Exception as e:
            print(f"Google Docs API failed. Falling back to Sandbox Mode. Error: {e}")
            is_sandbox_mode = True
            file_id = f"mock_doc_{uuid.uuid4().hex[:12]}"

    if not file_id:
        # Emergency backup ID
        is_sandbox_mode = True
        file_id = f"mock_doc_{uuid.uuid4().hex[:12]}"

    # 4. Share with the client email (if exists) and make public for studio (Only if NOT in sandbox mode)
    if not is_sandbox_mode:
        try:
            drive_gs = GoogleService(service_type='drive')
            # Make public so it can be embedded in studio without permission issues
            drive_gs.make_public(file_id, role='writer') 
            
            if client.user.email:
                drive_gs.share_file(file_id, client.user.email, role='writer')
        except Exception as e:
            print(f"Error sharing file: {e}")

    try:
        # 5. Save to database
        folder_id = request.data.get('folder_id')
        
        # If a folder is provided, ensure the document belongs to the folder's client
        # to prevent visibility issues.
        if folder_id:
            try:
                folder = VaultFolder.objects.get(id=folder_id)
                if folder.client:
                    client = folder.client
            except VaultFolder.DoesNotExist:
                pass

        client_doc = ClientDocument.objects.create(
            client=client,
            folder_id=folder_id,
            title=title,
            document_source=doc_type,
            google_drive_id=file_id,
            uploaded_by=request.user,
            is_visible_to_client=True
        )

        # 6. Create Audit Log
        from .models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='create',
            model_name='ClientDocument',
            object_id=str(client_doc.id),
            description=f"Created {'sandbox ' if is_sandbox_mode else ''}{doc_type.replace('_', ' ')}: {title} for client {client.company}",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            'id': client_doc.id,
            'title': client_doc.title,
            'google_drive_id': client_doc.google_drive_id,
            'webViewLink': client_doc.get_document_link(request)
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_vault_documents(request):
    user = request.user
    # If client_id is passed as query param (for admins)
    client_id = request.query_params.get('client_id')
    
    if client_id:
        docs = ClientDocument.objects.filter(client_id=client_id)
    else:
        client = getattr(user, 'client_profile', None)
        if client:
            docs = ClientDocument.objects.filter(client=client, is_visible_to_client=True)
        else:
            # For Admin (all docs)
            docs = ClientDocument.objects.all()
        
    data = []
    for doc in docs:
        data.append({
            'id': doc.id,
            'name': doc.title,
            'type': 'sheet' if doc.document_source == 'google_sheet' else 'slide' if doc.document_source == 'google_slide' else 'doc' if doc.document_source == 'google_doc' else 'file',
            'size': 'N/A', 
            'lastModified': doc.updated_at.strftime('%Y-%m-%d'),
            'link': doc.get_document_link(request),
            'google_drive_id': doc.google_drive_id
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_client_activity(request):
    from .models import AuditLog
    logs = AuditLog.objects.filter(user=request.user).order_by('-timestamp')[:50]
    
    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'user': 'You',
            'action': log.get_action_display(),
            'item': log.description.split(': ')[-1] if ': ' in log.description else log.description,
            'description': log.description,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'time': log.timestamp.strftime('%b %d, %H:%M'),
            'model': log.model_name
        })
    return Response(data)
