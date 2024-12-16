from typing import List, Optional
from core.contact_manager import ContactSource, Contact
import requests
from src.gui.login_dialog import LoginDialog
import os
import pickle
import json
import asyncio
from PySide6.QtWidgets import QMessageBox

TOKEN_PICKLE_PATH = 'yahoo_token.pickle'

class YahooContactSource(ContactSource):
    def __init__(self):
        """Initialize Yahoo contact source."""
        self.credentials = None
        self.session = requests.Session()
        self.base_url = "https://social.yahooapis.com/v1"
    
    def _get_credentials(self) -> Optional[dict]:
        """Get stored credentials or prompt for new ones."""
        credentials = None
        
        # Try to load saved credentials
        if os.path.exists(TOKEN_PICKLE_PATH):
            try:
                with open(TOKEN_PICKLE_PATH, 'rb') as f:
                    credentials = pickle.load(f)
            except Exception:
                pass
        
        if not credentials:
            # Show login dialog
            dialog = LoginDialog("Yahoo")
            if dialog.exec_():
                creds = dialog.get_credentials()
                credentials = {
                    'username': creds['username'],
                    'password': creds['password']
                }
                
                # Save credentials
                with open(TOKEN_PICKLE_PATH, 'wb') as f:
                    pickle.dump(credentials, f)
            else:
                return None
        
        return credentials
    
    async def fetch_contacts(self) -> List[Contact]:
        """Fetch contacts using Yahoo's Contacts API."""
        try:
            print("Starting Yahoo contacts fetch...")
            contacts = []
            
            # Get credentials if we don't have them
            if not self.credentials:
                self.credentials = self._get_credentials()
                if not self.credentials:
                    return contacts
            
            # Get OAuth token
            auth_response = self.session.post(
                "https://login.yahoo.com/oauth2/get_token",
                data={
                    "grant_type": "password",
                    "username": self.credentials['username'],
                    "password": self.credentials['password']
                }
            )
            
            if auth_response.status_code != 200:
                print(f"Auth failed: {auth_response.text}")
                return contacts
            
            token = auth_response.json()['access_token']
            
            # Set up headers for API requests
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            # Get user GUID
            user_response = self.session.get(
                "https://social.yahooapis.com/v1/me/guid",
                headers=headers
            )
            
            if user_response.status_code != 200:
                print(f"Failed to get user GUID: {user_response.text}")
                return contacts
            
            guid = user_response.json()['guid']['value']
            
            # Get contacts
            contacts_response = self.session.get(
                f"https://social.yahooapis.com/v1/user/{guid}/contacts",
                headers=headers,
                params={
                    'format': 'json',
                    'count': 1000  # Max contacts per request
                }
            )
            
            if contacts_response.status_code != 200:
                print(f"Failed to get contacts: {contacts_response.text}")
                return contacts
            
            # Parse contacts
            data = contacts_response.json()
            for contact_data in data.get('contacts', {}).get('contact', []):
                try:
                    fields = {
                        field['type']: field.get('value')
                        for field in contact_data.get('fields', [])
                    }
                    
                    contact = Contact(
                        id=f"yahoo_{contact_data['id']}",
                        first_name=fields.get('givenName'),
                        last_name=fields.get('familyName'),
                        email=fields.get('email'),
                        phone=fields.get('phone'),
                        source='yahoo',
                        source_id=contact_data['id'],
                        metadata=contact_data
                    )
                    contacts.append(contact)
                    
                except Exception as e:
                    print(f"Error processing contact: {str(e)}")
            
            print(f"Successfully fetched {len(contacts)} contacts")
            return contacts
            
        except Exception as e:
            print(f"Failed to fetch contacts: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        """Not implemented for read-only access."""
        raise NotImplementedError("Push contacts is not implemented for Yahoo")