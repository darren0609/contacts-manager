from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from sqlalchemy import select, func, update
from datetime import datetime
from thefuzz import fuzz
import uuid
import asyncio
import traceback
from src.core.app_state import app_state
import json

@dataclass
class Contact:
    id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    source: str
    source_id: str
    metadata: Dict

class ContactSource(ABC):
    @abstractmethod
    async def fetch_contacts(self) -> List[Contact]:
        pass
    
    @abstractmethod
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        pass

class MergeSuggestion:
    contact1: 'Contact'
    contact2: 'Contact'
    confidence: float
    reasons: List[str]

class ContactManager:
    def __init__(self, db_session):
        self.db = db_session
        self.sources: Dict[str, ContactSource] = {}
    
    @property
    def cache_ready(self):
        return app_state.cache_ready
    
    @cache_ready.setter
    def cache_ready(self, value):
        app_state.cache_ready = value
    
    async def add_source(self, source: ContactSource):
        """Register a new contact source with a unique identifier."""
        source_id = source.__class__.__name__
        self.sources[source_id] = source
    
    async def sync_all_sources(self):
        """Fetch and merge contacts from all sources."""
        all_contacts = []
        print(f"Starting sync with {len(self.sources)} sources")
        for source in self.sources.values():
            try:
                print(f"Fetching contacts from {source.__class__.__name__}")
                contacts = await source.fetch_contacts()
                print(f"Fetched {len(contacts)} contacts")
                # Save to database
                for contact in contacts:
                    try:
                        await self._save_contact(contact)
                        all_contacts.append(contact)
                    except Exception as e:
                        print(f"Error saving contact {contact.id}: {str(e)}")
            except Exception as e:
                print(f"Error syncing source {source.__class__.__name__}: {str(e)}")
        print(f"Successfully synced {len(all_contacts)} contacts")
        return all_contacts
    
    async def _save_contact(self, contact: Contact):
        """Save contact to database or update if it already exists."""
        from src.models.contact_model import ContactModel
        
        # Look for existing contact
        stmt = select(ContactModel).where(ContactModel.id == contact.id)
        result = await self.db.execute(stmt)
        existing_contact = result.scalar_one_or_none()
        
        if existing_contact:
            # Update existing contact
            existing_contact.first_name = contact.first_name
            existing_contact.last_name = contact.last_name
            existing_contact.email = contact.email
            existing_contact.phone = contact.phone
            existing_contact.contact_metadata = contact.metadata
            existing_contact.updated_at = datetime.utcnow()
        else:
            # Create new contact
            contact_model = ContactModel(
                id=contact.id,
                first_name=contact.first_name,
                last_name=contact.last_name,
                email=contact.email,
                phone=contact.phone,
                source=contact.source,
                source_id=contact.source_id,
                contact_metadata=contact.metadata,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deleted=False
            )
            self.db.add(contact_model)
    
    async def find_duplicates(self) -> List[Tuple[Contact, Contact, float, List[str]]]:
        """Find potential duplicate contacts using fuzzy matching."""
        duplicates = []
        contacts = []
        
        # Get all contacts from database
        from src.models.contact_model import ContactModel
        stmt = select(ContactModel)
        result = await self.db.execute(stmt)
        db_contacts = result.scalars().all()
        
        # Convert to Contact objects
        for db_contact in db_contacts:
            contact = Contact(
                id=db_contact.id,
                first_name=db_contact.first_name,
                last_name=db_contact.last_name,
                email=db_contact.email,
                phone=db_contact.phone,
                source=db_contact.source,
                source_id=db_contact.source_id,
                metadata=db_contact.contact_metadata
            )
            contacts.append(contact)
        
        # Compare all contacts with each other
        for i, contact1 in enumerate(contacts):
            for contact2 in contacts[i+1:]:
                confidence, reasons = self._calculate_similarity(contact1, contact2)
                if confidence > 0.5:  # Threshold for suggesting merge
                    duplicates.append((contact1, contact2, confidence, reasons))
        
        return sorted(duplicates, key=lambda x: x[2], reverse=True)
    
    def _calculate_similarity(self, contact1: Contact, contact2: Contact) -> Tuple[float, List[str]]:
        """Calculate similarity between two contacts with improved matching logic."""
        scores = []
        reasons = []
        
        # Strong identifiers (high confidence matches)
        if contact1.email and contact2.email:
            if contact1.email.lower() == contact2.email.lower():
                return 1.0, ["Identical email addresses"]
        
        if contact1.phone and contact2.phone:
            phone1 = ''.join(filter(str.isdigit, contact1.phone))
            phone2 = ''.join(filter(str.isdigit, contact2.phone))
            if phone1 == phone2 and len(phone1) >= 10:  # Full phone number match
                return 1.0, ["Identical phone numbers"]
        
        # Name matching with context
        has_full_name1 = bool(contact1.first_name and contact1.last_name)
        has_full_name2 = bool(contact2.first_name and contact2.last_name)
        
        if has_full_name1 and has_full_name2:
            # Both contacts have full names
            first_name_score = fuzz.ratio(contact1.first_name.lower(), contact2.first_name.lower()) / 100
            last_name_score = fuzz.ratio(contact1.last_name.lower(), contact2.last_name.lower()) / 100
            
            if first_name_score > 0.8 and last_name_score > 0.8:
                # Both names match strongly
                scores.append(0.9)
                reasons.append(f"Similar full names: {contact1.first_name} {contact1.last_name} ≈ {contact2.first_name} {contact2.last_name}")
            elif first_name_score > 0.8 and last_name_score < 0.3:
                # Same first name but very different last names - likely different people
                return 0.0, []
        else:
            # At least one contact has partial name
            if contact1.first_name and contact2.first_name:
                first_name_score = fuzz.ratio(contact1.first_name.lower(), contact2.first_name.lower()) / 100
                if first_name_score > 0.8:
                    # Matching first names with partial info needs supporting evidence
                    supporting_evidence = []
                    
                    # Check for partial phone match
                    if contact1.phone and contact2.phone:
                        phone1 = ''.join(filter(str.isdigit, contact1.phone))
                        phone2 = ''.join(filter(str.isdigit, contact2.phone))
                        if len(phone1) >= 7 and len(phone2) >= 7:
                            if phone1[-7:] == phone2[-7:]:
                                supporting_evidence.append("Matching last 7 digits of phone numbers")
                    
                    # Check for similar emails
                    if contact1.email and contact2.email:
                        email_score = fuzz.ratio(contact1.email.lower(), contact2.email.lower()) / 100
                        if email_score > 0.8:
                            supporting_evidence.append(f"Similar email addresses: {contact1.email} ≈ {contact2.email}")
                    
                    if supporting_evidence:
                        scores.append(0.7)
                        reasons.append(f"Matching first name ({contact1.first_name}) with supporting evidence:")
                        reasons.extend(f"  • {evidence}" for evidence in supporting_evidence)
        
        # Partial matches that can support other evidence
        if not scores:  # Only check these if we haven't found stronger matches
            # Email similarity without exact match
            if contact1.email and contact2.email:
                email_score = fuzz.ratio(contact1.email.lower(), contact2.email.lower()) / 100
                if email_score > 0.9:  # Higher threshold for emails
                    scores.append(0.6)
                    reasons.append(f"Very similar email addresses: {contact1.email} ≈ {contact2.email}")
            
            # Partial phone number match
            if contact1.phone and contact2.phone:
                phone1 = ''.join(filter(str.isdigit, contact1.phone))
                phone2 = ''.join(filter(str.isdigit, contact2.phone))
                if len(phone1) >= 7 and len(phone2) >= 7:
                    if phone1[-7:] == phone2[-7:]:
                        scores.append(0.5)
                        reasons.append("Matching last 7 digits of phone numbers")
        
        # Calculate overall confidence
        if not scores:
            return 0.0, []
        
        # Weight the scores based on the number of matching criteria
        confidence = sum(scores) / len(scores)
        if len(scores) > 1:
            # Boost confidence if multiple criteria match
            confidence = min(confidence + 0.1, 1.0)
        
        return confidence, reasons
    
    def suggest_merges(self) -> List[Dict]:
        # Generate smart merge suggestions
        pass 
    
    async def merge_contacts(self, source_id: str, target_id: str, merged_data: dict):
        """Merge two contacts and update with merged data"""
        from src.models.contact_model import ContactModel
        from datetime import datetime
        
        # Removed transaction block; session is managed externally
        # Get both contacts
        source = await self.db.get(ContactModel, source_id)
        target = await self.db.get(ContactModel, target_id)
        
        if not source or not target:
            raise ValueError("One or both contacts not found")
        
        # Update target contact with merged data
        target.first_name = merged_data.get('first_name', target.first_name)
        target.last_name = merged_data.get('last_name', target.last_name)
        target.email = merged_data.get('email', target.email)
        target.phone = merged_data.get('phone', target.phone)
        target.updated_at = datetime.utcnow()
        
        # Delete source contact
        await self.db.delete(source)
    
    async def get_all_contacts(self) -> List[Contact]:
        """Retrieve all contacts from the database."""
        from src.models.contact_model import ContactModel
        from sqlalchemy import select
        
        query = select(ContactModel).where(ContactModel.deleted == False)
        result = await self.db.execute(query)
        contacts = result.scalars().all()
        
        return [
            Contact(
                id=contact.id,
                first_name=contact.first_name,
                last_name=contact.last_name,
                email=contact.email,
                phone=contact.phone,
                source=contact.source,
                source_id=contact.source_id,
                metadata=contact.contact_metadata
            )
            for contact in contacts
        ]
    
    async def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Retrieve a specific contact by ID."""
        from src.models.contact_model import ContactModel
        from sqlalchemy import select
        
        query = select(ContactModel).where(ContactModel.id == contact_id)
        result = await self.db.execute(query)
        contact = result.scalar_one_or_none()
        
        if contact is None:
            return None
            
        return Contact(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            source=contact.source,
            source_id=contact.source_id,
            metadata=contact.contact_metadata
        )
    
    async def delete_contact(self, contact_id: str):
        """Delete a contact from the database."""
        from src.models.contact_model import ContactModel
        
        async with self.db.begin():
            contact = await self.db.get(ContactModel, contact_id)
            if contact:
                await self.db.delete(contact)
    
    async def update_duplicate_cache(self, progress_callback=None):
        """Update the duplicate cache in the background"""
        from src.models.duplicate_cache import DuplicateCache
        from datetime import datetime
        
        try:
            print("Starting duplicate cache update...")
            # Find duplicates
            duplicates = await self.find_duplicates()
            print(f"Found {len(duplicates)} potential duplicates")
            
            if progress_callback:
                await progress_callback(50)
            
            # Clear old cache
            print("Clearing old cache...")
            await self.db.execute(DuplicateCache.__table__.delete())
            
            # Insert new duplicates
            print("Inserting new duplicates...")
            total = len(duplicates)
            for i, (contact1, contact2, confidence, reasons) in enumerate(duplicates):
                cache_entry = DuplicateCache(
                    id=str(uuid.uuid4()),
                    contact1_id=contact1.id,
                    contact2_id=contact2.id,
                    confidence=confidence,
                    reasons=reasons,
                    last_updated=datetime.utcnow()
                )
                self.db.add(cache_entry)
                
                if i % 100 == 0:  # Log progress every 100 entries
                    print(f"Inserted {i}/{total} duplicates")
                
                if progress_callback:
                    progress = 50 + (i / total * 50)
                    await progress_callback(progress)
            
            print("Committing changes...")
            await self.db.flush()
        
            self.cache_ready = True
            print("Duplicate cache update completed successfully")
            
            # Verify the cache
            count_query = select(func.count()).select_from(DuplicateCache)
            result = await self.db.execute(count_query)
            final_count = result.scalar()
            print(f"Verified cache count: {final_count}")
            
        except Exception as e:
            print(f"Error updating cache: {str(e)}")
            print(traceback.format_exc())
            raise