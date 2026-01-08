#!/usr/bin/env python3
"""
Google Drive Uploader
Uploads files from a local directory to Google Drive with duplicate detection.
Only uploads if the file doesn't already exist.
"""

import os
import pickle
import hashlib
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Scopes required for Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Handle authentication with one-time browser flow"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # This requires browser interaction on first run
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for subsequent runs
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
    
    def _calculate_md5(self, file_path):
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def file_exists(self, filename, folder_id=None, check_md5=True, local_file_path=None):
        """
        Check if file already exists in Google Drive
        
        Args:
            filename: Name of the file to check
            folder_id: Optional folder ID to search within
            check_md5: If True, also compare MD5 checksums for exact match
            local_file_path: Path to local file for MD5 comparison
        
        Returns:
            tuple: (exists: bool, file_id: str or None)
        """
        try:
            # Build query
            query = f"name='{filename}' and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            # Search for files
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, md5Checksum, size)',
                pageSize=10
            ).execute()
            
            files = response.get('files', [])
            
            if not files:
                return False, None
            
            # If MD5 check is enabled and we have a local file
            if check_md5 and local_file_path:
                local_md5 = self._calculate_md5(local_file_path)
                
                for file in files:
                    # Google Drive returns MD5 for most files
                    drive_md5 = file.get('md5Checksum')
                    if drive_md5 and drive_md5 == local_md5:
                        return True, file.get('id')
                
                # Files with same name exist but MD5 doesn't match
                print(f'  File "{filename}" exists but content differs')
                return False, None
            
            # Just check by name
            return True, files[0].get('id')
            
        except HttpError as error:
            print(f'Error checking file existence: {error}')
            return False, None
    
    def upload_file(self, file_path, folder_id=None, mime_type=None, force=False, check_md5=True):
        """
        Upload a single file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            folder_id: Optional Google Drive folder ID
            mime_type: Optional MIME type
            force: If True, upload even if file exists
            check_md5: If True, compare MD5 checksums for duplicate detection
        
        Returns:
            str: File ID if uploaded, None otherwise
        """
        filename = os.path.basename(file_path)
        
        # Check if file already exists
        if not force:
            exists, file_id = self.file_exists(filename, folder_id, check_md5, file_path)
            if exists:
                print(f'Skipped: {filename} (already exists, ID: {file_id})')
                return file_id
        
        try:
            file_metadata = {'name': filename}
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, md5Checksum'
            ).execute()
            
            print(f'Uploaded: {file.get("name")} (ID: {file.get("id")})')
            return file.get('id')
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def upload_directory(self, directory_path, folder_id=None, pattern='*', force=False, check_md5=True):
        """
        Upload all files matching pattern from directory
        
        Args:
            directory_path: Path to local directory
            folder_id: Optional Google Drive folder ID
            pattern: File pattern to match (default: '*')
            force: If True, upload even if files exist
            check_md5: If True, compare MD5 checksums
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f'Directory {directory_path} does not exist')
            return
        
        files = list(directory.glob(pattern))
        print(f'Found {len(files)} files to process')
        
        uploaded = 0
        skipped = 0
        
        for file_path in files:
            if file_path.is_file():
                exists_before, _ = self.file_exists(
                    file_path.name, 
                    folder_id, 
                    check_md5, 
                    str(file_path)
                )
                
                result = self.upload_file(
                    str(file_path), 
                    folder_id, 
                    force=force, 
                    check_md5=check_md5
                )
                
                if result:
                    if not exists_before:
                        uploaded += 1
                    else:
                        skipped += 1
        
        print(f'\nSummary: {uploaded} uploaded, {skipped} skipped')


def main():
    """Main entry point for the CLI"""
    # Configuration from environment variables
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', './uploads')
    DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', None)
    FILE_PATTERN = os.getenv('FILE_PATTERN', '*')
    FORCE_UPLOAD = os.getenv('FORCE_UPLOAD', 'false').lower() == 'true'
    CHECK_MD5 = os.getenv('CHECK_MD5', 'true').lower() == 'true'
    
    print(f'Google Drive Uploader')
    print(f'Upload directory: {UPLOAD_DIR}')
    print(f'File pattern: {FILE_PATTERN}')
    print(f'MD5 checking: {"enabled" if CHECK_MD5 else "disabled"}')
    print(f'Force upload: {"yes" if FORCE_UPLOAD else "no"}')
    if DRIVE_FOLDER_ID:
        print(f'Target folder ID: {DRIVE_FOLDER_ID}')
    print()
    
    uploader = DriveUploader()
    uploader.upload_directory(
        UPLOAD_DIR, 
        DRIVE_FOLDER_ID, 
        FILE_PATTERN, 
        force=FORCE_UPLOAD,
        check_md5=CHECK_MD5
    )


if __name__ == '__main__':
    main()
