from typing import List, Optional
from core.contact_manager import ContactSource, Contact
import imaplib
import email
import vobject
import os
import pickle
from src.gui.login_dialog import LoginDialog

TOKEN_PICKLE_PATH = 'imap_credentials.pickle'

class IMAPContactSource(ContactSource):
    provider_settings = {
        'yahoo': {
            'imap_host': 'imap.mail.yahoo.com',
            'imap_port': 993,
            'display_name': 'Yahoo',
            'auth_prompt': 'Please enter your Yahoo credentials:'
        },
        # Add other providers as needed
    }
    
    def __init__(self, provider='yahoo'):
        """Initialize IMAP source with provider-specific settings."""
        self.provider = provider
        self.credentials = None
        self.connection = None
        
        # Try to initialize up to 3 times
        for attempt in range(3):
            success, message = self._initialize_connection()
            if success:
                break
            elif attempt < 2:
                from PySide6.QtWidgets import QMessageBox
                retry = QMessageBox.question(
                    None,
                    "Connection Failed",
                    f"Failed to connect to {provider}: {message}\nWould you like to try again?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if retry != QMessageBox.Yes:
                    raise ValueError(f"User cancelled {provider} connection")
            else:
                raise ValueError(f"Failed to initialize {provider} connection: {message}")
    
    def _initialize_connection(self) -> tuple[bool, str]:
        """Initialize IMAP connection."""
        try:
            self.credentials = self._get_credentials()
            if not self.credentials:
                return False, "No credentials provided"
            
            settings = self.provider_settings[self.provider]
            
            # Create IMAP connection
            self.connection = imaplib.IMAP4_SSL(
                settings['imap_host'],
                settings['imap_port']
            )
            
            # Login
            self.connection.login(
                self.credentials['username'],
                self.credentials['password']
            )
            
            return True, "Connection successful"
            
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {str(e)}")
            return False, str(e)
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False, str(e)
    
    def _get_credentials(self) -> Optional[dict]:
        """Get stored credentials or prompt for new ones."""
        credentials = None
        
        # Try to load saved credentials
        if os.path.exists(TOKEN_PICKLE_PATH):
            try:
                with open(TOKEN_PICKLE_PATH, 'rb') as f:
                    stored_creds = pickle.load(f)
                    if stored_creds.get('provider') == self.provider:
                        credentials = stored_creds
            except Exception:
                pass
        
        if not credentials:
            settings = self.provider_settings[self.provider]
            
            # Show login dialog
            dialog = LoginDialog(settings['display_name'])
            if dialog.exec_():
                creds = dialog.get_credentials()
                credentials = {
                    'provider': self.provider,
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
        """Fetch contacts from IMAP server."""
        try:
            print(f"Starting {self.provider} IMAP contact fetch...")
            contacts = []
            
            # List all folders with their full paths
            print("Listing folders...")
            _, folders = self.connection.list()
            available_folders = []
            for folder in folders:
                # Parse folder string
                parts = folder.decode().split('" "')
                if len(parts) >= 2:
                    folder_name = parts[-1].strip('"')
                    print(f"Found folder: {folder_name}")
                    available_folders.append(folder_name)
            
            # For Yahoo, try these folder variations
            if self.provider == 'yahoo':
                contact_folders = [
                    'Contacts',
                    'Contacts/VCard',
                    '@Contacts',
                    '@C',
                    'Contact',
                    'Yahoo/Contacts',
                    'Yahoo/Contact'
                ]
            else:
                contact_folders = ['Contacts', 'Contacts/VCard']
            
            # Try each potential contacts folder
            found_folder = False
            for folder_name in contact_folders:
                try:
                    print(f"Trying folder: {folder_name}")
                    # Try with and without quotes
                    for folder_format in [f'"{folder_name}"', folder_name]:
                        try:
                            result = self.connection.select(folder_format)
                            if result[0] == 'OK':
                                found_folder = True
                                print(f"Successfully selected folder: {folder_name}")
                                break
                        except Exception as e:
                            print(f"Failed to select {folder_format}: {str(e)}")
                    if found_folder:
                        break
                except Exception as e:
                    print(f"Error selecting folder {folder_name}: {str(e)}")
                    continue
            
            if not found_folder:
                # Try to find any folder containing 'contact' in the name
                contact_like_folders = [f for f in available_folders if 'contact' in f.lower()]
                if contact_like_folders:
                    print(f"Found potential contact folders: {contact_like_folders}")
                    for folder in contact_like_folders:
                        try:
                            result = self.connection.select(f'"{folder}"')
                            if result[0] == 'OK':
                                found_folder = True
                                print(f"Successfully selected folder: {folder}")
                                break
                        except Exception as e:
                            print(f"Error selecting folder {folder}: {str(e)}")
                
                if not found_folder:
                    print("Available folders:", available_folders)
                    raise ValueError("Could not find contacts folder. Available folders: " + 
                                  ", ".join(available_folders))
            
            # Search for all contacts
            print("Searching for contacts...")
            _, message_numbers = self.connection.search(None, 'ALL')
            if not message_numbers[0]:
                print("No messages found in contacts folder")
                return contacts
            
            print(f"Found {len(message_numbers[0].split())} potential contact messages")
            
            # Process each message
            for num in message_numbers[0].split():
                try:
                    # Fetch the contact data
                    print(f"Fetching message {num}")
                    _, msg_data = self.connection.fetch(num, '(RFC822)')
                    if not msg_data or not msg_data[0]:
                        print(f"No data for message {num}")
                        continue
                        
                    email_body = msg_data[0][1]
                    message = email.message_from_bytes(email_body)
                    
                    # Process each part of the message
                    found_contact = False
                    for part in message.walk():
                        content_type = part.get_content_type()
                        print(f"Found part with content type: {content_type}")
                        
                        if content_type in ['text/x-vcard', 'text/vcard']:
                            vcard_data = part.get_payload(decode=True).decode()
                            contact = self._parse_vcard(vcard_data, num)
                            if contact:
                                contacts.append(contact)
                                found_contact = True
                                print(f"Successfully parsed contact: {contact.first_name} {contact.last_name}")
                            break
                    
                    if not found_contact:
                        print(f"No contact data found in message {num}")
                
                except Exception as e:
                    print(f"Error processing contact {num}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
            
            print(f"Processed {len(contacts)} contacts")
            return contacts
            
        except Exception as e:
            print(f"Failed to fetch contacts: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
        finally:
            try:
                # Close the connection
                self.connection.close()
                self.connection.logout()
            except:
                pass
    
    def _parse_vcard(self, vcard_data: str, message_id: bytes) -> Optional[Contact]:
        """Parse vCard data into Contact object."""
        try:
            vcard = vobject.readOne(vcard_data)
            
            # Extract basic fields
            first_name = last_name = email = phone = None
            
            # Get name components
            if hasattr(vcard, 'n'):
                names = vcard.n.value
                last_name = str(names.family) if names.family else None
                first_name = str(names.given) if names.given else None
            elif hasattr(vcard, 'fn'):  # Fallback to full name
                full_name = str(vcard.fn.value).split()
                first_name = full_name[0] if full_name else None
                last_name = full_name[-1] if len(full_name) > 1 else None
            
            # Get email
            if hasattr(vcard, 'email'):
                email = str(vcard.email.value)
            
            # Get phone
            if hasattr(vcard, 'tel'):
                phone = str(vcard.tel.value)
            
            return Contact(
                id=f"imap_{self.provider}_{message_id.decode()}",
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                source=f"imap_{self.provider}",
                source_id=message_id.decode(),
                metadata={'vcard': vcard_data}
            )
            
        except Exception as e:
            print(f"Error parsing vCard: {str(e)}")
            return None
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        """Not implemented for read-only access."""
        raise NotImplementedError("Push contacts is not implemented for IMAP") 