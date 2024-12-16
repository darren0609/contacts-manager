from typing import List, Optional, Tuple
from core.contact_manager import ContactSource, Contact
import vobject
import caldav
from urllib.parse import urlparse
import os
import pickle
import logging
from PySide6.QtWidgets import QApplication
from src.gui.login_dialog import LoginDialog
from authlib.integrations.requests_client import OAuth2Session
import json

TOKEN_PICKLE_PATH = 'carddav_credentials.pickle'

class CardDAVSource(ContactSource):
    provider_settings = {
        'yahoo': {
            'url': 'https://social.yahooapis.com/v1/user/{guid}/contacts',
            'auth_url': 'https://api.login.yahoo.com/oauth2/request_auth',
            'token_url': 'https://api.login.yahoo.com/oauth2/get_token',
            'display_name': 'Yahoo',
            'auth_prompt': 'Please enter your Yahoo credentials:',
            'client_id': None,  # Will be loaded from config
            'client_secret': None  # Will be loaded from config
        },
        'icloud': {
            'url': 'https://contacts.icloud.com',
            'display_name': 'iCloud',
            'auth_prompt': 'Please enter your iCloud credentials:'
        }
    }
    
    def __init__(self, provider='yahoo'):
        """Initialize CardDAV source with provider-specific settings."""
        self.provider = provider
        self.credentials = None
        self.client = None
        self.session = None
        
        # Load OAuth credentials
        if provider == 'yahoo':
            self._load_oauth_config()
        
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
    
    def _load_oauth_config(self):
        """Load OAuth credentials from config file."""
        try:
            with open('yahoo_oauth_credentials.json', 'r') as f:
                config = json.load(f)
                self.provider_settings['yahoo']['client_id'] = config['client_id']
                self.provider_settings['yahoo']['client_secret'] = config['client_secret']
        except Exception as e:
            raise ValueError(f"Failed to load Yahoo OAuth credentials: {e}")
    
    def _setup_oauth_session(self):
        """Setup OAuth session for Yahoo."""
        settings = self.provider_settings['yahoo']
        
        session = OAuth2Session(
            client_id=settings['client_id'],
            client_secret=settings['client_secret'],
            scope='sdps-r',  # Yahoo Contacts read scope
        )
        
        # Get authorization URL
        auth_url = session.create_authorization_url(
            settings['auth_url'],
            redirect_uri='oob'  # Out-of-band for desktop apps
        )
        
        # Show login dialog with auth URL
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            None,
            "Yahoo Authorization Required",
            f"Please visit this URL to authorize the application:\n{auth_url}\n\n"
            "After authorizing, you will receive a verification code."
        )
        
        # Get authorization code from user
        from PySide6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(
            None,
            "Enter Authorization Code",
            "Please enter the verification code:"
        )
        
        if not ok or not code:
            raise ValueError("Authorization cancelled by user")
        
        # Get token
        token = session.fetch_token(
            settings['token_url'],
            authorization_response=code,
            grant_type='authorization_code'
        )
        
        return session, token
    
    def _initialize_connection(self) -> Tuple[bool, str]:
        """Initialize connection with credentials and test it."""
        try:
            self.credentials = self._get_credentials()
            if not self.credentials:
                return False, "No credentials provided"
            
            self.client = self._setup_client()
            
            # Test connection
            success, message = self._test_connection()
            if not success:
                print(f"Connection test failed: {message}")
                # Delete saved credentials if they're invalid
                if os.path.exists(TOKEN_PICKLE_PATH):
                    os.remove(TOKEN_PICKLE_PATH)
                return False, message
            
            print(f"Successfully connected to {self.provider}")
            return True, "Connection successful"
            
        except Exception as e:
            print(f"Error initializing connection: {str(e)}")
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
                
                # Test credentials before saving
                self.credentials = credentials
                success, message = self._test_connection()
                if success:
                    # Save credentials
                    with open(TOKEN_PICKLE_PATH, 'wb') as f:
                        pickle.dump(credentials, f)
                else:
                    print(f"Invalid credentials: {message}")
                    return None
            else:
                return None
        
        return credentials
    
    def _test_connection(self) -> Tuple[bool, str]:
        """Test the connection using OAuth."""
        try:
            if self.provider == 'yahoo':
                if not self.session:
                    self.session, token = self._setup_oauth_session()
                
                # Get user GUID
                response = self.session.get('https://api.login.yahoo.com/openid/v1/userinfo')
                user_info = response.json()
                guid = user_info['sub']
                
                # Test contacts API
                url = self.provider_settings['yahoo']['url'].format(guid=guid)
                response = self.session.get(url)
                
                if response.status_code == 200:
                    return True, "Connection successful"
                else:
                    return False, f"API error: {response.status_code}"
            else:
                # Original CardDAV test for other providers
                return super()._test_connection()
                
        except Exception as e:
            print(f"Connection error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False, str(e)
    
    def _setup_client(self):
        """Setup CardDAV client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials available")
        
        settings = self.provider_settings[self.provider]
        
        # Add debug logging
        print(f"Setting up CardDAV client for {self.provider}")
        print(f"Using URL: {settings['url']}")
        print(f"Username: {self.credentials['username']}")
        
        client = caldav.DAVClient(
            url=settings['url'],
            username=self.credentials['username'],
            password=self.credentials['password'],
            auth=(self.credentials['username'], self.credentials['password'])  # Explicit auth
        )
        
        return client
    
    def _parse_vcard(self, vcard_text: str) -> Contact:
        """Parse vCard text into Contact object."""
        vcard = vobject.readOne(vcard_text)
        
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
            id=f"carddav_{self.provider}_{vcard.uid.value}" if hasattr(vcard, 'uid') else None,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            source=f"carddav_{self.provider}",
            source_id=str(vcard.uid.value) if hasattr(vcard, 'uid') else None,
            metadata={'vcard': vcard_text}
        )
    
    async def fetch_contacts(self) -> List[Contact]:
        """Fetch contacts from CardDAV server."""
        try:
            print(f"Starting {self.provider} CardDAV contact fetch...")
            contacts = []
            
            # Get principal
            principal = self.client.principal()
            
            # Get address books based on provider
            if self.provider == 'yahoo':
                home_sets = principal.get_addressbook_homes()
                if not home_sets:
                    raise ValueError("No address book home found")
                home = home_sets[0]
                abooks = home.get_addressbooks()
            else:
                abooks = principal.addressbooks()
            
            if not abooks:
                print("No address books found")
                return []
            
            # Get contacts from each address book
            for abook in abooks:
                print(f"Fetching from address book: {abook.name if hasattr(abook, 'name') else 'Unknown'}")
                
                try:
                    # Get all vCard objects
                    cards = abook.get_vcard_objects()
                    for card in cards:
                        try:
                            contact = self._parse_vcard(card.get_vcard_data())
                            if contact:
                                contacts.append(contact)
                        except Exception as e:
                            print(f"Error processing contact: {str(e)}")
                except Exception as e:
                    print(f"Error accessing address book: {str(e)}")
            
            print(f"Processed {len(contacts)} contacts")
            return contacts
            
        except Exception as e:
            print(f"Failed to fetch contacts: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        """Not implemented for read-only access."""
        raise NotImplementedError("Push contacts is not implemented for CardDAV") 