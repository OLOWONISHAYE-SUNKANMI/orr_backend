import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.apps import apps

schema = {}
for model in apps.get_models():
    model_name = f"{model._meta.app_label}.{model.__name__}"
    fields = []
    for f in model._meta.get_fields():
        fields.append({
            "name": f.name,
            "type": f.get_internal_type() if hasattr(f, 'get_internal_type') else type(f).__name__
        })
    schema[model_name] = fields

with open('db_schema.json', 'w') as f:
    json.dump(schema, f, indent=4)
print("Schema exported to db_schema.json")
