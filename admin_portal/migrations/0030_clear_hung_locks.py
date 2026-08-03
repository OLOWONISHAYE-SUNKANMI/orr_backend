from django.db import migrations

def clear_hung_locks(apps, schema_editor):
    try:
        with schema_editor.connection.cursor() as cursor:
            # Check if using PostgreSQL
            if schema_editor.connection.vendor == 'postgresql':
                # Terminate any queries holding database locks or running longer than 5 seconds
                cursor.execute("""
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE pid != pg_backend_pid()
                      AND (
                        query ILIKE '%delete%' 
                        OR query ILIKE '%client%' 
                        OR age(clock_timestamp(), query_start) > interval '5 seconds'
                      );
                """)
    except Exception:
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('admin_portal', '0029_adminprofile_bio_adminprofile_company_name'),
    ]

    operations = [
        migrations.RunPython(clear_hung_locks),
    ]
