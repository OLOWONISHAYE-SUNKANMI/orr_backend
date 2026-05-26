import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_portal.models import Client, VaultFolder
from admin_portal.v1.serializers.client import VaultFolderSerializer

print("=== REAL DATABASE VAULT FOLDERS ===")
for folder in VaultFolder.objects.all():
    serializer = VaultFolderSerializer(folder)
    print(f"ID: {folder.id}")
    print(f"  Name: {folder.name}")
    print(f"  Client Field: {folder.client}")
    print(f"  Client ID (FK): {folder.client_id}")
    if folder.client:
        print(f"  Client Company: {folder.client.company}")
        print(f"  Client User ID: {folder.client.user.id}")
        print(f"  Client Full Name: {folder.client.user.get_full_name()}")
    print(f"  Serialized Data: {serializer.data}")
