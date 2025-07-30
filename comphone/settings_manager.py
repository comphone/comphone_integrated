# comphone/settings_manager.py

import os
import json
from io import BytesIO
from flask import current_app
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Local imports to avoid circular dependencies.
# These functions will be called within other functions.

SETTINGS_FILE = 'settings.json'

# ค่าตั้งต้นของแอปพลิเคชัน
_DEFAULT_APP_SETTINGS_STORE = {
    'report_times': {
        'appointment_reminder_hour_thai': 7,
        'outstanding_report_hour_thai': 20,
        'customer_followup_hour_thai': 9
    },
    'line_recipients': {
        'admin_group_id': os.environ.get('LINE_ADMIN_GROUP_ID', ''),
        'technician_group_id': os.environ.get('LINE_TECHNICIAN_GROUP_ID', ''),
        'manager_user_id': ''
    },
    'equipment_catalog': [],
    'auto_backup': { 'enabled': False, 'hour_thai': 2, 'minute_thai': 0 },
    'shop_info': { 'contact_phone': '081-XXX-XXXX', 'line_id': '@ComphoneService' },
    'technician_list': []
}

def load_settings_from_file():
    """Loads settings from the local settings.json file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            current_app.logger.error(f"Error handling settings.json: {e}")
            if os.path.exists(SETTINGS_FILE) and os.path.getsize(SETTINGS_FILE) == 0:
                os.remove(SETTINGS_FILE)
                current_app.logger.warning(f"Empty settings.json deleted. Using default settings.")
    return None

def save_settings_to_file(settings_data):
    """Saves the provided settings data to the local settings.json file."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        current_app.logger.error(f"Error writing to settings.json: {e}")
        return False

def get_app_settings():
    """
    Gets the application settings, merging defaults with saved settings.
    Creates settings.json if it doesn't exist.
    """
    app_settings = json.loads(json.dumps(_DEFAULT_APP_SETTINGS_STORE))
    loaded_settings = load_settings_from_file()

    if loaded_settings:
        for key, default_value in app_settings.items():
            if key in loaded_settings:
                if isinstance(default_value, dict) and isinstance(loaded_settings[key], dict):
                    app_settings[key].update(loaded_settings[key])
                else:
                    app_settings[key] = loaded_settings[key]
    else:
        # If no settings file exists, create one with defaults
        save_settings_to_file(app_settings)

    # Add a computed property for common equipment items for convenience
    equipment_catalog = app_settings.get('equipment_catalog', [])
    app_settings['common_equipment_items'] = sorted(list(set(item.get('item_name') for item in equipment_catalog if item.get('item_name'))))

    return app_settings

def save_app_settings(settings_data):
    """
    Saves new settings by merging them with the current settings.
    """
    current_settings = get_app_settings()

    for key, value in settings_data.items():
        if isinstance(value, dict) and key in current_settings and isinstance(current_settings[key], dict):
            current_settings[key].update(value)
        else:
            current_settings[key] = value

    return save_settings_to_file(current_settings)

def load_settings_from_drive_on_startup():
    """
    Attempts to load the latest settings backup from Google Drive on app startup.
    """
    from .google_services import find_or_create_drive_folder, get_google_drive_service, _execute_google_api_call_with_retry, GOOGLE_DRIVE_FOLDER_ID

    settings_backup_folder_id = find_or_create_drive_folder("Settings_Backups", GOOGLE_DRIVE_FOLDER_ID)
    if not settings_backup_folder_id:
        current_app.logger.error("Could not find or create Settings_Backups folder. Skipping settings restore.")
        return False

    service = get_google_drive_service()
    if not service:
        current_app.logger.error("Could not get Drive service for settings restore.")
        return False

    try:
        query = f"name = 'settings_backup.json' and '{settings_backup_folder_id}' in parents and trashed = false"
        response = _execute_google_api_call_with_retry(service.files().list, q=query, spaces='drive', fields='files(id, name)', orderBy='modifiedTime desc', pageSize=1)
        files = response.get('files', [])

        if files:
            latest_backup_file_id = files[0]['id']
            current_app.logger.info(f"Found latest settings backup on Drive (ID: {latest_backup_file_id})")

            request = service.files().get_media(fileId=latest_backup_file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)

            downloaded_settings = json.loads(fh.read().decode('utf-8'))

            if save_settings_to_file(downloaded_settings):
                current_app.logger.info("Successfully restored settings from Google Drive backup.")
                return True
            else:
                current_app.logger.error("Failed to save restored settings to local file.")
                return False
        else:
            current_app.logger.info("No settings backup found on Google Drive for automatic restore.")
            return False
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during settings restore from Drive: {e}")
        return False

def backup_settings_to_drive():
    """
    Backs up the current settings.json to a specific folder in Google Drive.
    Deletes any previous backup file.
    """
    from .google_services import find_or_create_drive_folder, get_google_drive_service, _execute_google_api_call_with_retry, GOOGLE_DRIVE_FOLDER_ID

    settings_backup_folder_id = find_or_create_drive_folder("Settings_Backups", GOOGLE_DRIVE_FOLDER_ID)
    if not settings_backup_folder_id:
        current_app.logger.error("Cannot back up settings: Could not find or create Settings_Backups folder.")
        return False

    service = get_google_drive_service()
    if not service:
        current_app.logger.error("Cannot back up settings: Google Drive service is unavailable.")
        return False

    try:
        # Delete old backup file first
        query = f"name = 'settings_backup.json' and '{settings_backup_folder_id}' in parents and trashed = false"
        response = _execute_google_api_call_with_retry(service.files().list, q=query, spaces='drive', fields='files(id)')
        for file_item in response.get('files', []):
            _execute_google_api_call_with_retry(service.files().delete, fileId=file_item['id'])
            current_app.logger.info(f"Deleted old settings_backup.json (ID: {file_item['id']}) from Drive.")

        # Upload new backup file
        settings_data = get_app_settings()
        settings_json_bytes = BytesIO(json.dumps(settings_data, ensure_ascii=False, indent=4).encode('utf-8'))

        file_metadata = {'name': 'settings_backup.json', 'parents': [settings_backup_folder_id]}
        media = MediaIoBaseUpload(settings_json_bytes, mimetype='application/json', resumable=True)

        _execute_google_api_call_with_retry(
            service.files().create,
            body=file_metadata, media_body=media, fields='id'
        )
        current_app.logger.info("Successfully saved current settings to settings_backup.json on Google Drive.")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to backup settings to Google Drive: {e}", exc_info=True)
        return False
