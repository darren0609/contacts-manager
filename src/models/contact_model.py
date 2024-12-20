from sqlalchemy import Column, String, JSON, DateTime, Table, MetaData, Boolean
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
    deleted = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "source": self.source,
            "source_id": self.source_id,
            "metadata": self.contact_metadata
        }