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
        """Handle authentication with headless-friendly options"""
        import json
        
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
                # Check if we should use manual auth mode
                use_manual = os.getenv('MANUAL_AUTH', 'false').lower() == 'true'
                
                if use_manual:
                    # Manual authorization code flow (headless-friendly)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, 
                        SCOPES,
                        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                    )
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    print('\n' + '='*60)
                    print('MANUAL AUTHENTICATION (HEADLESS MODE)')
                    print('='*60)
                    print('Please visit this URL in a browser (on any device):')
                    print()
                    print(auth_url)
                    print()
                    print('After authorizing, you will receive an authorization code.')
                    print('='*60)
                    
                    code = input('Enter the authorization code here: ').strip()
                    
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    
                    print('\n✓ Authentication successful!')
                    print('='*60 + '\n')
                else:
                    # Automatic flow (requires ability to open browser or port forwarding)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    
                    print('\n' + '='*60)
                    print('AUTHENTICATION')
                    print('='*60)
                    print('Starting local server for authentication...')
                    print('If you are on a headless server, set MANUAL_AUTH=true')
                    print('='*60 + '\n')
                    
                    creds = flow.run_local_server(port=0, open_browser=False)
                    
                    print('\n✓ Authentication successful!')
                    print('='*60 + '\n')
            
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
    
    def create_or_get_folder(self, folder_name, parent_id=None):
        """
        Create a folder in Google Drive or get existing folder ID
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional parent folder ID
        
        Returns:
            str: Folder ID
        """
        try:
            # Check if folder already exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()
            
            files = response.get('files', [])
            
            if files:
                print(f'  Found existing folder: {folder_name} (ID: {files[0].get("id")})')
                return files[0].get('id')
            
            # Create new folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
            
            print(f'  Created folder: {folder.get("name")} (ID: {folder.get("id")})')
            return folder.get('id')
            
        except HttpError as error:
            print(f'Error creating/getting folder: {error}')
            return None
    
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
                
                # Files with same name exist but MD5 doesn't match - return file_id to update
                return False, files[0].get('id')
            
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
        else:
            # Force mode: check if file exists to update instead of duplicate
            exists, file_id = self.file_exists(filename, folder_id, check_md5=False, local_file_path=None)
        
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            # Update existing file if file_id is provided, otherwise create new
            if file_id:
                file = self.service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id, name, md5Checksum'
                ).execute()
                print(f'Updated: {file.get("name")} (ID: {file.get("id")})')
            else:
                file_metadata = {'name': filename}
                
                if folder_id:
                    file_metadata['parents'] = [folder_id]
                
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
    
    def upload_directory(self, directory_path, folder_id=None, pattern='*', force=False, check_md5=True, recursive=True):
        """
        Upload all files matching pattern from directory
        
        Args:
            directory_path: Path to local directory
            folder_id: Optional Google Drive folder ID
            pattern: File pattern to match (default: '*')
            force: If True, upload even if files exist
            check_md5: If True, compare MD5 checksums
            recursive: If True, upload subdirectories recursively (default: True)
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f'Directory {directory_path} does not exist')
            return
        
        # Use rglob for recursive, glob for non-recursive
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        # Filter to only files (not directories)
        files = [f for f in files if f.is_file()]
        
        print(f'Found {len(files)} files to process{" (recursive)" if recursive else ""}')
        
        uploaded = 0
        skipped = 0
        
        # Cache for folder IDs to avoid recreating
        folder_cache = {}
        
        for file_path in files:
            # Determine the target folder ID based on relative path
            relative_path = file_path.relative_to(directory)
            target_folder_id = folder_id
            
            # If file is in a subdirectory, create/get the folder structure
            if len(relative_path.parts) > 1:
                # Need to create folder structure
                current_folder_id = folder_id
                folder_parts = relative_path.parts[:-1]  # Exclude filename
                
                for i, folder_name in enumerate(folder_parts):
                    # Build cache key from the path up to this point
                    cache_key = '/'.join(folder_parts[:i+1])
                    
                    if cache_key in folder_cache:
                        current_folder_id = folder_cache[cache_key]
                    else:
                        current_folder_id = self.create_or_get_folder(
                            folder_name,
                            current_folder_id
                        )
                        folder_cache[cache_key] = current_folder_id
                
                target_folder_id = current_folder_id
            
            # Check if file exists
            exists_before, _ = self.file_exists(
                file_path.name, 
                target_folder_id, 
                check_md5, 
                str(file_path)
            )
            
            # Upload file
            result = self.upload_file(
                str(file_path), 
                target_folder_id, 
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
    RECURSIVE = os.getenv('RECURSIVE', 'true').lower() == 'true'
    
    print(f'Google Drive Uploader')
    print(f'Upload directory: {UPLOAD_DIR}')
    print(f'File pattern: {FILE_PATTERN}')
    print(f'Recursive: {"yes" if RECURSIVE else "no"}')
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
        check_md5=CHECK_MD5,
        recursive=RECURSIVE
    )


if __name__ == '__main__':
    main()