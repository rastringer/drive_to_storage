# Drive to Storage

A simple CLI to copy Google Drive files to Google Cloud Storage. 
Supported file types:
* Google Docs / Docx
* PDFs
* Images

## Prerequsites

A Google Drive folder
A GCP project with billing and Cloud Storage and Google Drive APIs enabled.
A Google Cloud Storage bucket.

## Authentication

Authentication is simply via local command line. This saves the need for credentials / token files.

```
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform
```

## Usage

`git clone` this repo
Enter the directory `cd drive_to_storage`
Install packages `pip install -r requirements.txt`

Run:
`python3 main.py "<your drive folder>", "<your storage bucket>"`