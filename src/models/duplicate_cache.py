from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from src.models.contact_model import Base

class DuplicateCache(Base):
    __tablename__ = 'duplicate_cache'
    
    id = Column(String, primary_key=True)
    contact1_id = Column(String, ForeignKey('contacts.id'))
    contact2_id = Column(String, ForeignKey('contacts.id'))
    confidence = Column(Float)
    reasons = Column(JSON)
    last_updated = Column(DateTime) 