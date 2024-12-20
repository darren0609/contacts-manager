import sys
from pathlib import Path
import asyncio
import tempfile
import os
import csv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func, update
from src.core.contact_manager import ContactManager
from src.db.database import init_db
from src.models.contact_model import ContactModel
from src.models.source_config import SourceConfig
import uuid
from src.core.background_tasks import BackgroundTaskManager
from src.core.app_state import app_state
from src.sources.csv_source import CSVSource
from datetime import datetime
import secrets
from google_auth_oauthlib.flow import Flow
from src.sources.gmail_source import GmailContactSource

class ContactCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="src/web/templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
@app.on_event("startup")
async def startup_event():
    app.state.db_session = await init_db("sqlite+aiosqlite:///contacts.db")
    
    # Signal that the web app is ready immediately
    with open("web_app_ready.txt", "w") as f:
        f.write("ready")

# Add to app initialization
app.state.task_manager = BackgroundTaskManager()

@app.get("/api/tasks/status")
async def get_tasks_status():
    """Get status of all background tasks"""
    return {
        "tasks": app.state.task_manager.tasks
    }

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

@app.get("/api/contacts")
async def list_contacts():
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            contacts = await manager.get_all_contacts()
            return {"contacts": [
                {
                    "id": c.id,
                    "first_name": c.first_name or "",
                    "last_name": c.last_name or "",
                    "email": c.email or "",
                    "phone": c.phone or "",
                    "source": c.source,
                }
                for c in contacts
            ]}
    except Exception as e:
        import traceback
        print(f"Error fetching contacts: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts")
async def create_contact(contact: ContactCreate):
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            new_contact = {
                "id": str(uuid.uuid4()),
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "phone": contact.phone,
                "source": "manual",
                "source_id": str(uuid.uuid4()),
                "metadata": {}
            }
            await manager._save_contact(new_contact)
            return {"success": True, "contact": new_contact}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: str, contact: ContactCreate):
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            existing = await manager.get_contact(contact_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            updated_contact = {
                "id": contact_id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "phone": contact.phone,
                "source": existing.source,
                "source_id": existing.source_id,
                "metadata": existing.metadata
            }
            await manager._save_contact(updated_contact)
            return {"success": True, "contact": updated_contact}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: str):
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            # Add delete_contact method to ContactManager if it doesn't exist
            await manager.delete_contact(contact_id)
            return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def sync_contacts():
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            await manager.sync_all_sources()
            return {"success": True}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/sources")
async def sources_page(request: Request):
    return templates.TemplateResponse(
        "sources.html",
        {
            "request": request,
            "sources": [
                {
                    "name": "Gmail",
                    "type": "gmail",
                    "status": "Connected",
                    "last_sync": "2024-01-17 14:57:36",
                    "contact_count": 150
                },
                {
                    "name": "CSV Import",
                    "type": "csv",
                    "status": "Available",
                    "last_sync": None,
                    "contact_count": 0
                },
                {
                    "name": "CardDAV",
                    "type": "carddav",
                    "status": "Not Configured",
                    "last_sync": None,
                    "contact_count": 0
                }
            ]
        }
    )

@app.post("/api/sources/{source_name}/sync")
async def sync_source(source_name: str):
    try:
        async with app.state.db_session() as session:
            # First check if this is a valid source
            exists_query = select(func.count()).select_from(ContactModel).where(ContactModel.source == source_name)
            result = await session.execute(exists_query)
            exists = result.scalar() > 0

            if not exists and source_name != "Gmail":  # Allow Gmail even if no contacts yet
                raise HTTPException(status_code=404, detail="Source not found")

            # Handle different source types
            if source_name.startswith('csv_'):
                return {
                    "success": True, 
                    "message": "CSV sources are read-only. To update contacts, please re-import the CSV file."
                }
            elif source_name == "Gmail":
                try:
                    # Get Gmail configuration outside transaction
                    query = (
                        select(SourceConfig)
                        .where(SourceConfig.name == 'Gmail')
                        .order_by(SourceConfig.updated_at.desc())
                        .limit(1)
                    )
                    result = await session.execute(query)
                    config = result.scalar_one_or_none()
                    
                    if not config:
                        return {
                            "success": False,
                            "message": "Gmail not configured. Please authorize Gmail access first."
                        }
                    
                    # Create Gmail source and fetch contacts outside transaction
                    source = GmailContactSource(config)
                    contacts = await source.fetch_contacts()
                    
                    # Now do all database operations in a single transaction
                    async with session.begin():
                        # Mark existing Gmail contacts as deleted
                        await session.execute(
                            update(ContactModel)
                            .where(
                                ContactModel.source == "Gmail",
                                ContactModel.deleted == False
                            )
                            .values(deleted=True)
                        )
                        
                        # Save new contacts without starting a new transaction
                        manager = ContactManager(session)
                        for contact in contacts:
                            # Save without internal transaction
                            stmt = select(ContactModel).where(ContactModel.id == contact.id)
                            result = await session.execute(stmt)
                            existing_contact = result.scalar_one_or_none()
                            
                            if existing_contact:
                                existing_contact.first_name = contact.first_name
                                existing_contact.last_name = contact.last_name
                                existing_contact.email = contact.email
                                existing_contact.phone = contact.phone
                                existing_contact.contact_metadata = contact.metadata
                                existing_contact.updated_at = datetime.utcnow()
                            else:
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
                                session.add(contact_model)
                    
                    return {
                        "success": True,
                        "message": f"Successfully synced {len(contacts)} contacts from Gmail",
                        "synced": len(contacts)
                    }
                    
                except Exception as e:
                    print(f"Error syncing Gmail contacts: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    return {
                        "success": False,
                        "message": f"Error syncing Gmail contacts: {str(e)}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Sync is not yet available for {source_name}. No contacts were updated."
                }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing source {source_name}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/sources/{source_name}/disconnect")
async def disconnect_source(source_name: str):
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            # TODO: Implement source disconnection logic
            return {"success": True}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/sources")
async def list_sources():
    """Get all configured sources"""
    try:
        async with app.state.db_session() as session:
            from sqlalchemy import select, func, text
            from src.models.contact_model import ContactModel
            
            # Get unique sources and their contact counts using SQLAlchemy
            query = select(
                ContactModel.source,
                func.count().label('contact_count'),
                func.max(ContactModel.updated_at).label('last_sync')
            ).group_by(ContactModel.source)
            
            result = await session.execute(query)
            sources = []
            
            for row in result:
                if row.source:  # Skip null sources
                    sources.append({
                        "name": row.source,
                        "type": "csv" if row.source.startswith("csv_") else row.source.lower(),
                        "status": "Connected",
                        "contact_count": row.contact_count,
                        "last_sync": row.last_sync.isoformat() if row.last_sync else None
                    })
            
            return {"sources": sources}
    except Exception as e:
        print(f"Error listing sources: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts/duplicates")
async def find_duplicate_contacts(request: Request):
    try:
        app_state.check_duplicate_cache_status()
        if not app_state.cache_ready:
            return {
                "not_ready": True,
                "message": "Duplicate analysis is in progress. Please try again in a moment.",
                "count": 0,
                "duplicates": []
            }
        
        # Rest of the duplicate checking code...
    except Exception as e:
        print("Error retrieving duplicates:", str(e))
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts/merge")
async def merge_contacts(merge_data: dict):
    try:
        async with app.state.db_session() as session:
            manager = ContactManager(session)
            await manager.merge_contacts(
                merge_data["source_id"],
                merge_data["target_id"],
                merge_data["merged_data"]
            )
            return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/status")
async def get_cache_status():
    """Get the current status of the duplicate cache"""
    app_state.check_duplicate_cache_status()
    return {
        "ready": app_state.cache_ready,
        "last_updated": app_state.last_cache_update
    }

@app.post("/api/sources/csv/preview")
async def preview_csv(file: UploadFile = File(...)):
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Read CSV headers and first few rows
        with open(tmp_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            preview_rows = []
            for _ in range(3):  # Get 3 rows for preview
                try:
                    preview_rows.append(next(reader))
                except StopIteration:
                    break
        
        os.unlink(tmp_path)  # Clean up temp file
        
        return {
            "headers": headers,
            "preview": preview_rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sources/csv/import")
async def import_csv(
    file: UploadFile = File(...),
    field_mapping: dict = Body(...)
):
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Create CSV source
        source = CSVSource(tmp_path, field_mapping)
        
        # Import contacts
        async with app.state.db_session() as session:
            # Create source config
            source_config = SourceConfig(
                id=source.source_id,
                source_type='csv',
                name=source.source_id,  # Use source_id as name
                config={
                    'field_mapping': field_mapping,
                    'original_filename': file.filename
                }
            )
            session.add(source_config)
            
            # Import contacts
            manager = ContactManager(session)
            contacts = await source.fetch_contacts()
            
            for contact in contacts:
                await manager._save_contact(contact)
            
            await session.commit()
        
        os.unlink(tmp_path)  # Clean up temp file
        
        return {
            "success": True,
            "imported": len(contacts)
        }
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/{source_name}/info")
async def get_source_info(source_name: str):
    """Get information about a source before syncing"""
    try:
        async with app.state.db_session() as session:
            # Get source statistics first
            stats_query = select(
                func.count(ContactModel.id).label('contact_count'),
                func.max(ContactModel.updated_at).label('last_sync')
            ).where(ContactModel.source == source_name)
            
            stats = await session.execute(stats_query)
            stats = stats.first()
            
            # Try to get source configuration if it exists
            from src.models.source_config import SourceConfig
            query = (
                select(SourceConfig)
                .where(SourceConfig.name == source_name)
                .order_by(SourceConfig.updated_at.desc())  # Get most recent config
                .limit(1)
            )
            result = await session.execute(query)
            config = result.scalar_one_or_none()
            
            # Also clean up any old configs
            if config:
                cleanup_query = (
                    select(SourceConfig)
                    .where(
                        SourceConfig.name == source_name,
                        SourceConfig.id != config.id
                    )
                )
                old_configs = await session.execute(cleanup_query)
                for old_config in old_configs.scalars():
                    await session.delete(old_config)
                await session.commit()
            
            # Return info even if no config exists
            return {
                "source_type": config.source_type if config else "unknown",
                "field_mapping": config.config.get('field_mapping') if config else None,
                "contact_count": stats.contact_count if stats else 0,
                "last_sync": stats.last_sync.isoformat() if stats and stats.last_sync else None,
                "has_config": bool(config)
            }
            
    except Exception as e:
        print(f"Error getting source info: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sources/{source_name}/configure")
async def configure_source(
    source_name: str,
    config: dict = Body(...)
):
    """Update source configuration"""
    try:
        async with app.state.db_session() as session:
            # Get or create source config
            query = select(SourceConfig).where(SourceConfig.name == source_name)
            result = await session.execute(query)
            source_config = result.scalar_one_or_none()
            
            if not source_config:
                source_config = SourceConfig(
                    id=str(uuid.uuid4()),
                    name=source_name,
                    source_type=config.get('type', 'unknown'),
                    config={}
                )
                session.add(source_config)
            
            # Update configuration
            source_config.config.update(config)
            source_config.updated_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "success": True,
                "message": f"Configuration updated for {source_name}"
            }
            
    except Exception as e:
        print(f"Error configuring source {source_name}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Store OAuth states temporarily
oauth_states = {}

@app.get("/api/sources/gmail/auth/start")
async def start_gmail_auth():
    """Start Gmail OAuth flow"""
    try:
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/contacts.readonly'],
            redirect_uri='http://127.0.0.1:8000/api/sources/gmail/auth/callback'
        )
        
        # Generate state token
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            'timestamp': datetime.utcnow(),
            'completed': False
        }
        
        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return {
            "auth_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        print(f"Error starting Gmail auth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/gmail/auth/callback")
async def gmail_auth_callback(request: Request):
    """Handle Gmail OAuth callback"""
    try:
        # Get state and code
        state = request.query_params.get('state')
        code = request.query_params.get('code')
        
        if not state or state not in oauth_states:
            raise HTTPException(status_code=400, detail="Invalid state")
        
        # Complete OAuth flow
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/contacts.readonly'],
            redirect_uri='http://127.0.0.1:8000/api/sources/gmail/auth/callback',
            state=state
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save credentials
        async with app.state.db_session() as session:
            source_config = SourceConfig(
                id=str(uuid.uuid4()),
                name='Gmail',
                source_type='gmail',
                config={
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
            )
            session.add(source_config)
            await session.commit()
        
        # Mark auth as completed
        oauth_states[state]['completed'] = True
        oauth_states[state]['success'] = True
        
        # Show success page
        return templates.TemplateResponse(
            "oauth_success.html",
            {"request": request}
        )
        
    except Exception as e:
        print(f"Error in Gmail callback: {str(e)}")
        if state in oauth_states:
            oauth_states[state]['completed'] = True
            oauth_states[state]['success'] = False
            oauth_states[state]['error'] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/gmail/auth/check")
async def check_gmail_auth(state: str):
    """Check Gmail OAuth status"""
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    status = oauth_states[state]
    if status['completed']:
        # Clean up state
        del oauth_states[state]
    
    return status

@app.on_event("shutdown")
async def shutdown_event():
    # ... existing shutdown code ...
    
    # Clean up the ready file
    try:
        Path("web_app_ready.txt").unlink()
    except FileNotFoundError:
        pass