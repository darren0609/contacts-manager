import csv
import uuid
from typing import List
from src.core.contact_manager import Contact, ContactSource
from datetime import datetime

class CSVSource(ContactSource):
    def __init__(self, file_path: str, field_mapping: dict):
        self.file_path = file_path
        self.field_mapping = field_mapping
        self.source_id = f"csv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
    async def fetch_contacts(self) -> List[Contact]:
        contacts = []
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        contact = Contact(
                            id=f"csv_{str(uuid.uuid4())}",
                            first_name=row.get(self.field_mapping.get('first_name', ''), '').strip(),
                            last_name=row.get(self.field_mapping.get('last_name', ''), '').strip(),
                            email=row.get(self.field_mapping.get('email', ''), '').strip(),
                            phone=row.get(self.field_mapping.get('phone', ''), '').strip(),
                            source="csv",
                            source_id=self.source_id,
                            metadata={
                                "imported_at": datetime.utcnow().isoformat(),
                                "original_data": row,
                                "import_batch": self.source_id
                            }
                        )
                        contacts.append(contact)
                    except Exception as e:
                        print(f"Error processing CSV row: {str(e)}")
                        print(f"Row data: {row}")
                        continue
                        
            print(f"Successfully processed {len(contacts)} contacts from CSV")
            return contacts
            
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            raise
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        # CSV source is read-only
        return False