import argparse
from googleapiclient.discovery import build
from google.cloud import storage
import io
from googleapiclient.http import MediaIoBaseDownload
import os

IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/tiff',
    'image/webp'  # Add other image types as needed
]

def get_drive_folder_id(drive_folder_name):
    """Finds the ID of a Google Drive folder by its name."""
    try:
        drive_service = build('drive', 'v3')
        results = drive_service.files().list(
            q=f"name='{drive_folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)",
            pageSize=1000,
        ).execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        else:
            raise FileNotFoundError(f"Folder '{drive_folder_name}' not found in Google Drive.")
    except Exception as e:
        print(f"Error getting folder ID: {e}")
        return None


def copy_folder_to_gcs(drive_folder_id, gcs_bucket_name, parent_gcs_path=""):
    """Recursively copies a Google Drive folder and its contents to GCS."""
    try:
        drive_service = build('drive', 'v3')
        results = drive_service.files().list(
            q=f"'{drive_folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType, parents)",
            pageSize=1000,
        ).execute()
        items = results.get('files', [])

        for item in items:
            file_id = item['id']
            file_name = item['name']
            mime_type = item['mimeType']
            parents = item.get('parents')
            gcs_path = os.path.join(parent_gcs_path, file_name)

            if mime_type == 'application/vnd.google-apps.folder':
                copy_folder_to_gcs(file_id, gcs_bucket_name, gcs_path)
            elif mime_type == 'application/pdf' or mime_type in IMAGE_MIME_TYPES:
                download_and_upload_file(drive_service, file_id, gcs_bucket_name, gcs_path)
            elif mime_type in ['application/vnd.google-apps.document', 'application/vnd.google-apps.spreadsheet', 'application/vnd.google-apps.presentation']:
                export_and_upload_file(drive_service, file_id, gcs_bucket_name, gcs_path, mime_type)
            else:
                print(f"Skipping file '{file_name}' with unsupported MIME type: {mime_type}")

    except Exception as e:
        print(f"An error occurred: {e}")


def download_and_upload_file(drive_service, file_id, gcs_bucket_name, gcs_path):
    """Downloads and uploads a file (optimized for PDFs and images)."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Downloading {gcs_path}: {int(status.progress() * 100)}%")
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(fh.getvalue())
        print(f"Uploaded '{gcs_path}' to gs://{gcs_bucket_name}/{gcs_path}")
    except Exception as e:
        print(f"Error processing file '{gcs_path}': {e}")


def export_and_upload_file(drive_service, file_id, gcs_bucket_name, gcs_path, mime_type):
    """Exports and uploads Google Docs, Sheets, Slides, etc."""
    try:
        export_mime_type = get_export_mime_type(mime_type)
        request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Exporting and downloading: {int(status.progress() * 100)}%")
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(fh.getvalue())
        print(f"Uploaded '{gcs_path}' to gs://{gcs_bucket_name}/{gcs_path}")
    except Exception as e:
        print(f"Error processing file '{gcs_path}': {e}")


def get_export_mime_type(mime_type):
    if mime_type == 'application/vnd.google-apps.document':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif mime_type == 'application/vnd.google-apps.spreadsheet':
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif mime_type == 'application/vnd.google-apps.presentation':
        return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")


def main():
    parser = argparse.ArgumentParser(description='Copy a Google Drive folder to Google Cloud Storage.')
    parser.add_argument('drive_folder_name', help='Name of the Google Drive folder')
    parser.add_argument('gcs_bucket_name', help='Name of the Google Cloud Storage bucket')
    args = parser.parse_args()

    drive_folder_id = get_drive_folder_id(args.drive_folder_name)
    if drive_folder_id:
        copy_folder_to_gcs(drive_folder_id, args.gcs_bucket_name)


if __name__ == "__main__":
    main()