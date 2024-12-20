from typing import List, Optional
from core.contact_manager import ContactSource, Contact
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import asyncio
import logging
from datetime import datetime
import traceback

SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']
TOKEN_PICKLE_PATH = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'

class GmailContactSource(ContactSource):
    def __init__(self):
        """Initialize Gmail contact source."""
        self.credentials = None
        self.service = None
        
        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Setup logging
        log_filename = os.path.join(logs_dir, f'gmail_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        self.logger = logging.getLogger(__name__)
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
        
        self.logger.info("="*80)
        self.logger.info("Gmail Import Session Started")
        self.logger.info("="*80)
    
    async def _get_service(self):
        """Get or create the Google People API service."""
        if not self.service:
            self.credentials = self._get_credentials()
            self.service = build('people', 'v1', credentials=self.credentials, cache_discovery=False)
        return self.service

    def _get_credentials(self) -> Credentials:
        """Get valid user credentials from storage or user authentication."""
        try:
            self.logger.info("Getting Google credentials...")
            credentials = None
            
            # Try to load saved credentials
            if os.path.exists(TOKEN_PICKLE_PATH):
                self.logger.info("Found saved credentials, loading...")
                with open(TOKEN_PICKLE_PATH, 'rb') as token:
                    credentials = pickle.load(token)
                self.logger.info("Loaded saved credentials")
            
            # If there are no (valid) credentials available, let the user log in
            if not credentials or not credentials.valid:
                self.logger.info("Credentials invalid or missing")
                if credentials and credentials.expired and credentials.refresh_token:
                    self.logger.info("Refreshing expired credentials...")
                    credentials.refresh(Request())
                    self.logger.info("Credentials refreshed")
                else:
                    self.logger.info("Need new credentials...")
                    if not os.path.exists(CREDENTIALS_FILE):
                        self.logger.error(f"Missing {CREDENTIALS_FILE}")
                        raise FileNotFoundError(
                            f"Missing {CREDENTIALS_FILE}. Download it from Google Cloud Console "
                            "and save it in the project root directory."
                        )
                    
                    self.logger.info("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES)
                    credentials = flow.run_local_server(port=0)
                    self.logger.info("OAuth flow completed")
                
                # Save the credentials for the next run
                self.logger.info("Saving credentials...")
                with open(TOKEN_PICKLE_PATH, 'wb') as token:
                    pickle.dump(credentials, token)
                self.logger.info("Credentials saved")
            
            return credentials
            
        except Exception as e:
            self.logger.error("Error getting credentials:")
            self.logger.error(str(e))
            self.logger.error(traceback.format_exc())
            raise
    
    async def fetch_contacts(self) -> List[Contact]:
        """Fetch contacts using Google's People API."""
        try:
            self.logger.info("Starting Gmail contact fetch...")
            service = await self._get_service()
            self.logger.info("Successfully connected to Google People API")
            
            # Call the People API
            self.logger.info("Fetching contacts from Google...")
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=2000,
                personFields='names,emailAddresses,phoneNumbers,addresses,organizations,biographies,birthdays,urls'
            ).execute()
            connections = results.get('connections', [])
            self.logger.info(f"Found {len(connections)} contacts")
            
            contacts = []
            for i, person in enumerate(connections, 1):
                try:
                    self.logger.info(f"\nProcessing contact {i}/{len(connections)}:")
                    
                    # Extract basic info
                    names = person.get('names', [])
                    name = names[0] if names else {}
                    first_name = name.get('givenName', '')
                    last_name = name.get('familyName', '')
                    self.logger.info(f"Name: {first_name} {last_name}")
                    
                    # Extract all phone numbers
                    phones = person.get('phoneNumbers', [])
                    primary_phone = phones[0].get('value') if phones else None
                    additional_phones = [
                        {'type': phone.get('type', 'Other'), 'number': phone.get('value')}
                        for phone in phones[1:]  # Skip the first (primary) phone
                    ]
                    if primary_phone:
                        self.logger.info(f"Primary phone: {primary_phone}")
                    if additional_phones:
                        self.logger.info(f"Additional phones: {additional_phones}")
                    
                    # Extract all email addresses
                    emails = person.get('emailAddresses', [])
                    primary_email = emails[0].get('value') if emails else None
                    additional_emails = [
                        {'type': email.get('type', 'Other'), 'value': email.get('value')}
                        for email in emails[1:]  # Skip the first (primary) email
                    ]
                    if primary_email:
                        self.logger.info(f"Primary email: {primary_email}")
                    if additional_emails:
                        self.logger.info(f"Additional emails: {additional_emails}")
                    
                    # Extract addresses
                    addresses = person.get('addresses', [])
                    if addresses:
                        self.logger.info(f"Found {len(addresses)} addresses")
                    
                    # Extract organization info
                    organizations = person.get('organizations', [])
                    org = organizations[0] if organizations else {}
                    if org:
                        self.logger.info(f"Organization: {org.get('name')} - {org.get('title')}")
                    
                    # Extract biography/notes
                    biographies = person.get('biographies', [])
                    notes = biographies[0].get('value') if biographies else None
                    if notes:
                        self.logger.info("Has notes/biography")
                    
                    # Extract birthday
                    birthdays = person.get('birthdays', [])
                    birthday = birthdays[0].get('date') if birthdays else None
                    if birthday:
                        self.logger.info(f"Has birthday: {birthday}")
                    
                    # Extract websites
                    urls = person.get('urls', [])
                    if urls:
                        self.logger.info(f"Found {len(urls)} websites")
                    
                    contact = Contact(
                        id=f"google_{person['resourceName'].split('/')[-1]}",
                        first_name=first_name,
                        last_name=last_name,
                        email=primary_email,
                        phone=primary_phone,
                        source='google',
                        source_id=person['resourceName'],
                        metadata={
                            'additional_phones': additional_phones,
                            'additional_emails': additional_emails,
                            'addresses': addresses,
                            'company': org.get('name'),
                            'title': org.get('title'),
                            'notes': notes,
                            'birthday': birthday,
                            'websites': urls,
                            'raw_data': person  # Store complete response
                        }
                    )
                    contacts.append(contact)
                    
                except Exception as e:
                    self.logger.error(f"Error processing contact {i}:")
                    self.logger.error(f"Error: {str(e)}")
                    self.logger.error(f"Contact data: {person}")
                    continue
            
            self.logger.info("\nImport Summary:")
            self.logger.info(f"Total contacts found: {len(connections)}")
            self.logger.info(f"Successfully processed: {len(contacts)}")
            self.logger.info("="*40)
            
            return contacts
            
        except Exception as e:
            self.logger.error("Failed to fetch contacts:")
            self.logger.error(str(e))
            self.logger.error(traceback.format_exc())
            raise
    
    def _get_first_name(self, person: dict) -> Optional[str]:
        names = person.get('names', [])
        return names[0].get('givenName') if names else None
    
    def _get_last_name(self, person: dict) -> Optional[str]:
        names = person.get('names', [])
        return names[0].get('familyName') if names else None
    
    def _get_primary_email(self, person: dict) -> Optional[str]:
        emails = person.get('emailAddresses', [])
        return emails[0].get('value') if emails else None
    
    def _get_primary_phone(self, person: dict) -> Optional[str]:
        phones = person.get('phoneNumbers', [])
        return phones[0].get('value') if phones else None
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        """Not implemented for read-only access."""
        raise NotImplementedError("Push contacts is not implemented for Gmail")