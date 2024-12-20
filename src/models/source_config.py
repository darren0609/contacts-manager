from sqlalchemy import Column, String, JSON, DateTime
from src.models.contact_model import Base
from datetime import datetime

class SourceConfig(Base):
    __tablename__ = 'source_configs'
    
    id = Column(String, primary_key=True)
    source_type = Column(String, nullable=False)  # 'csv', 'gmail', 'carddav'
    name = Column(String, nullable=False)
    config = Column(JSON)  # Store source-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 