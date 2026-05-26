import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_portal.models import Client, VaultFolder
from admin_portal.v1.serializers.client import VaultFolderSerializer

# Fetch first existing client
client = Client.objects.first()

if client:
    print(f"Using Client ID: {client.id}, Company: {client.company}, User Name: {client.user.get_full_name()}")
    
    # Create folder
    folder = VaultFolder.objects.create(name='Test Client Folder', client=client)

    try:
        serializer = VaultFolderSerializer(folder)
        print("=== SERIALIZED FOLDER DATA ===")
        print(serializer.data)
    finally:
        # Cleanup
        folder.delete()
else:
    print("No client found in DB!")
