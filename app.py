import argparse
from google.auth.transport.requests import Request
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage
import io
import sys

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    try:
        creds, _ = default(scopes=SCOPES)
        if not creds.valid:
            creds.refresh(Request())
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error getting Drive service: {e}", file=sys.stderr)
        sys.exit(1)  # Exit with an error code

def get_storage_client():
    try:
        return storage.Client()
    except Exception as e:
        print(f"Error getting Storage client: {e}", file=sys.stderr)
        sys.exit(1)

def copy_drive_to_gcs(drive_service, storage_client, drive_folder_id, gcs_bucket_name):
    try:
        bucket = storage_client.bucket(gcs_bucket_name)
        if not bucket.exists():
            print(f"Error: GCS bucket '{gcs_bucket_name}' does not exist.", file=sys.stderr)
            sys.exit(1)

        results = drive_service.files().list(
            q=f"'{drive_folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()

        items = results.get('files', [])

        if not items:
            print(f"Warning: No files found in the specified Drive folder.", file=sys.stderr)
            return

        for item in items:
            print(f"Processing file: {item['name']}")
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                print(f"Skipping folder: {item['name']}")
                continue

            request = drive_service.files().get_media(fileId=item['id'])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%", end='\r') # Use \r for progress update on same line

            blob = bucket.blob(item['name'])
            fh.seek(0)
            blob.upload_from_file(fh)
            print(f"Uploaded {item['name']} to {gcs_bucket_name}")

    except Exception as e:
        print(f"Error copying files: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Copy files from Google Drive to Google Cloud Storage.')
    parser.add_argument('drive_folder_id', help='ID of the Google Drive folder')
    parser.add_argument('gcs_bucket_name', help='Name of the Google Cloud Storage bucket')
    args = parser.parse_args()

    drive_service = get_drive_service()
    storage_client = get_storage_client()

    print(f"Copying files from Drive folder ID: {args.drive_folder_id} to GCS bucket: {args.gcs_bucket_name}")
    copy_drive_to_gcs(drive_service, storage_client, args.drive_folder_id, args.gcs_bucket_name)

if __name__ == '__main__':
    main()