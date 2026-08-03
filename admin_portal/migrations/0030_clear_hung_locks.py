from django.db import migrations

def clear_hung_locks(apps, schema_editor):
    # Originally terminated queries matching 'delete'/'client' or running >5s.
    # This was overly aggressive and could kill legitimate production queries.
    # The actual timeout fix is now handled in ClientDetailView.perform_destroy().
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('admin_portal', '0029_adminprofile_bio_adminprofile_company_name'),
    ]

    operations = [
        migrations.RunPython(clear_hung_locks),
    ]
