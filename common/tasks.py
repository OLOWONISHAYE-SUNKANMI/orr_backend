import subprocess
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
import os

logger = get_task_logger(__name__)

@shared_task
def backup_database():
    """
    Executes the database backup script.
    """
    script_path = os.path.join(settings.BASE_DIR, 'scripts', 'backup_db.sh')
    
    # Ensure it's executable
    os.chmod(script_path, 0o755)
    
    logger.info("Starting automated database backup...")
    try:
        result = subprocess.run(
            [script_path],
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy() # Passes DB_PASSWORD if available
        )
        logger.info(f"Backup completed successfully: {result.stdout}")
        return "Backup successful"
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e.stderr}")
        raise e

@shared_task
def backup_workspace():
    """
    Executes the workspace backup script.
    """
    script_path = os.path.join(settings.BASE_DIR, 'scripts', 'backup_workspace.sh')
    workspace_dir = os.path.join(settings.BASE_DIR, 'workspace_data') # or whatever is needed
    
    # Ensure it's executable
    os.chmod(script_path, 0o755)
    
    logger.info("Starting automated workspace backup...")
    try:
        result = subprocess.run(
            [script_path, workspace_dir],
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )
        logger.info(f"Workspace backup completed successfully: {result.stdout}")
        return "Workspace backup successful"
    except subprocess.CalledProcessError as e:
        logger.error(f"Workspace backup failed: {e.stderr}")
        raise e
