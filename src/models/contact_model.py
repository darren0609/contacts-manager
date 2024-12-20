from sqlalchemy import Column, String, JSON, DateTime, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ContactModel(Base):
    __tablename__ = 'contacts'
    
    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    source = Column(String)
    source_id = Column(String)
    contact_metadata = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime) 