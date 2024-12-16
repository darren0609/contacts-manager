from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class Command:
    """Base class for all commands"""
    def execute(self):
        raise NotImplementedError
    
    def undo(self):
        raise NotImplementedError
    
    @property
    def description(self) -> str:
        raise NotImplementedError

@dataclass
class MergeCommand(Command):
    """Command for merging contacts"""
    manager: Any  # ContactManager
    source_id: str
    target_id: str
    merged_data: Dict
    original_source: Optional[Dict] = None
    original_target: Optional[Dict] = None
    
    async def execute(self):
        # Store original state for undo
        async with self.manager.db.begin():
            from src.models.contact_model import ContactModel
            source = await self.manager.db.get(ContactModel, self.source_id)
            target = await self.manager.db.get(ContactModel, self.target_id)
            
            self.original_source = {
                'id': source.id,
                'first_name': source.first_name,
                'last_name': source.last_name,
                'email': source.email,
                'phone': source.phone,
                'source': source.source,
                'source_id': source.source_id,
                'contact_metadata': source.contact_metadata
            }
            
            self.original_target = {
                'id': target.id,
                'first_name': target.first_name,
                'last_name': target.last_name,
                'email': target.email,
                'phone': target.phone,
                'source': target.source,
                'source_id': target.source_id,
                'contact_metadata': target.contact_metadata
            }
        
        # Perform merge
        await self.manager.merge_contacts(self.source_id, self.target_id, self.merged_data)
    
    async def undo(self):
        """Restore contacts to their original state"""
        from src.models.contact_model import ContactModel
        
        async with self.manager.db.begin():
            # Restore target contact
            target = await self.manager.db.get(ContactModel, self.target_id)
            for key, value in self.original_target.items():
                setattr(target, key, value)
            
            # Recreate source contact
            source = ContactModel(**self.original_source)
            self.manager.db.add(source)
    
    @property
    def description(self) -> str:
        return f"Merge contacts {self.source_id} into {self.target_id}"

@dataclass
class EditCommand(Command):
    """Command for editing a contact"""
    manager: Any
    contact_id: str
    new_data: Dict
    original_data: Optional[Dict] = None
    
    async def execute(self):
        # Store original state
        async with self.manager.db.begin():
            from src.models.contact_model import ContactModel
            contact = await self.manager.db.get(ContactModel, self.contact_id)
            self.original_data = {
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'email': contact.email,
                'phone': contact.phone
            }
            
            # Update contact
            for key, value in self.new_data.items():
                setattr(contact, key, value)
            contact.updated_at = datetime.utcnow()
    
    async def undo(self):
        async with self.manager.db.begin():
            from src.models.contact_model import ContactModel
            contact = await self.manager.db.get(ContactModel, self.contact_id)
            for key, value in self.original_data.items():
                setattr(contact, key, value)
            contact.updated_at = datetime.utcnow()
    
    @property
    def description(self) -> str:
        return f"Edit contact {self.contact_id}" 