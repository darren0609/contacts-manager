from typing import List
import aiohttp
from google.oauth2.credentials import Credentials
from src.core.contact_manager import Contact, ContactSource
from src.models.source_config import SourceConfig
from datetime import datetime
import uuid

class GmailContactSource(ContactSource):
    def __init__(self, config: SourceConfig):
        self.config = config
        self.credentials = Credentials(
            token=config.config['token'],
            refresh_token=config.config['refresh_token'],
            token_uri=config.config['token_uri'],
            client_id=config.config['client_id'],
            client_secret=config.config['client_secret'],
            scopes=config.config['scopes']
        )
        self.source_id = "gmail"

    async def fetch_contacts(self) -> List[Contact]:
        contacts = []
        
        # Use aiohttp for async HTTP requests
        async with aiohttp.ClientSession() as session:
            # Get fresh access token if needed
            if not self.credentials.valid:
                self.credentials.refresh(Request())
            
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
                'Accept': 'application/json',
            }
            
            # Fetch contacts from Google People API
            async with session.get(
                'https://people.googleapis.com/v1/people/me/connections'
                '?personFields=names,emailAddresses,phoneNumbers'
                '&pageSize=1000',
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for person in data.get('connections', []):
                        # Extract contact details
                        names = person.get('names', [{}])[0]
                        emails = person.get('emailAddresses', [{}])[0]
                        phones = person.get('phoneNumbers', [{}])[0]
                        
                        contact = Contact(
                            id=f"gmail_{str(uuid.uuid4())}",
                            first_name=names.get('givenName', ''),
                            last_name=names.get('familyName', ''),
                            email=emails.get('value', ''),
                            phone=phones.get('value', ''),
                            source="Gmail",
                            source_id=person.get('resourceName', ''),
                            metadata={
                                "etag": person.get('etag', ''),
                                "last_synced": datetime.utcnow().isoformat(),
                                "raw_data": person
                            }
                        )
                        contacts.append(contact)
                        
                    # Handle pagination
                    next_page_token = data.get('nextPageToken')
                    while next_page_token:
                        async with session.get(
                            f'https://people.googleapis.com/v1/people/me/connections'
                            f'?personFields=names,emailAddresses,phoneNumbers'
                            f'&pageSize=1000&pageToken={next_page_token}',
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                for person in data.get('connections', []):
                                    names = person.get('names', [{}])[0]
                                    emails = person.get('emailAddresses', [{}])[0]
                                    phones = person.get('phoneNumbers', [{}])[0]
                                    
                                    contact = Contact(
                                        id=f"gmail_{str(uuid.uuid4())}",
                                        first_name=names.get('givenName', ''),
                                        last_name=names.get('familyName', ''),
                                        email=emails.get('value', ''),
                                        phone=phones.get('value', ''),
                                        source="Gmail",
                                        source_id=person.get('resourceName', ''),
                                        metadata={
                                            "etag": person.get('etag', ''),
                                            "last_synced": datetime.utcnow().isoformat(),
                                            "raw_data": person
                                        }
                                    )
                                    contacts.append(contact)
                                
                                next_page_token = data.get('nextPageToken')
                            else:
                                break
                                
        return contacts

    async def push_contacts(self, contacts: List[Contact]) -> bool:
        # Implement contact pushing later
        return False