from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from auth import GoogleAuth
from graph_database import GraphDatabase
from contacts_service import ContactsService
from linkedin_service import LinkedInService
from backup_service import BackupService
from geocoding_service import GeocodingService
from models import SyncResponse, Contact, ContactEdge, TagRequest, NotesRequest, OrganizationNode, LinkedInSyncResponse

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

load_dotenv(BACKEND_DIR / ".env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ContactSphere API", version="1.0.0")

# CORS middleware for frontend (optional when served from same origin)
cors_allow_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
frontend_url_env = os.getenv("FRONTEND_URL", "").strip()

if cors_allow_origins_env:
    cors_allow_origins = [
        origin.strip()
        for origin in cors_allow_origins_env.split(",")
        if origin.strip()
    ]
elif frontend_url_env:
    cors_allow_origins = [frontend_url_env]
else:
    cors_allow_origins = ["http://localhost:8080", "http://localhost:9090"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
google_auth = GoogleAuth()
db = GraphDatabase()
contacts_service = ContactsService(db)
linkedin_service = LinkedInService(db)
backup_service = BackupService(db)
geocoding_service = GeocodingService(db)

@app.on_event("startup")
async def startup():
    await db.init_db()
    logger.info("ContactSphere API started")

@app.get("/", include_in_schema=False)
async def root():
    if FRONTEND_INDEX_FILE.is_file():
        return FileResponse(FRONTEND_INDEX_FILE)

    return {"message": "ContactSphere API", "version": "1.0.0"}

@app.get("/auth/google")
async def google_auth_start():
    """Start Google OAuth flow"""
    try:
        auth_url = google_auth.get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Auth start failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

from urllib.parse import urlparse, urlunparse

@app.get("/auth/google/callback")
async def google_auth_callback(code: str, state: str = None):
    """Handle Google OAuth callback"""
    # Get configured frontend port
    frontend_port = os.getenv('FRONTEND_PORT', '8080')
    
    # Get frontend URL from env or default
    default_frontend = f'http://localhost:{frontend_port}'
    frontend_url = os.getenv('FRONTEND_URL', default_frontend)
    
    # Auto-adjust port in frontend_url if FRONTEND_PORT is set and differs
    if os.getenv('FRONTEND_PORT'):
        try:
            parsed = urlparse(frontend_url)
            if parsed.port and str(parsed.port) != frontend_port:
                new_netloc = parsed.netloc.replace(f":{parsed.port}", f":{frontend_port}")
                frontend_url = urlunparse(parsed._replace(netloc=new_netloc))
        except Exception:
            pass

    try:
        credentials = google_auth.exchange_code(code)
        # Store credentials
        google_auth.store_credentials(credentials)
        return RedirectResponse(url=f"{frontend_url}?auth=success")
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        return RedirectResponse(url=f"{frontend_url}?auth=error")

@app.get("/api/auth/status")
async def get_auth_status():
    """Check if user is authenticated with Google"""
    return {"authenticated": google_auth.has_credentials()}

@app.post("/api/sync")
async def sync_contacts() -> SyncResponse:
    """Sync contacts from Google and infer relationships"""
    try:
        logger.info("Starting contact sync")
        
        if not google_auth.has_credentials():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Sync contacts from Google
        result = await contacts_service.sync_contacts(google_auth.get_credentials())
        
        logger.info(f"Sync completed: {result.imported} imported, {result.updated} updated")
        return result
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.post("/api/sync/linkedin")
async def sync_linkedin_contacts() -> LinkedInSyncResponse:
    """Sync contacts from LinkedIn and match with existing contacts"""
    try:
        logger.info("Starting LinkedIn contact sync")
        
        # Sync contacts from LinkedIn
        result = await linkedin_service.sync_linkedin_contacts()
        
        # If authenticated with Google, push updates for matched contacts
        if google_auth.has_credentials() and result.matched > 0:
            try:
                logger.info("Pushing LinkedIn updates to Google Contacts...")
                # Get contacts that were recently updated with LinkedIn data
                # We can filter by last_linkedin_sync being very recent
                # For simplicity, let's get all contacts with linkedin_connected_date
                # A better approach would be to have the service return the IDs, but let's query DB
                
                # We'll fetch all contacts and filter in memory or add a DB query
                # Adding a specific DB query is better
                # Use a small buffer time to ensure we catch all updates
                since_time = (result.created_at or datetime.now(timezone.utc))
                
                updated_contacts = await db.get_contacts_updated_since(since_time)
                
                # Filter contacts that have a Google ID
                contacts_to_update = [
                    c for c in updated_contacts 
                    if c.id and not c.id.startswith('linkedin_')
                ]
                
                if contacts_to_update:
                    count = contacts_service.batch_update_contacts_google(
                        google_auth.get_credentials(), 
                        contacts_to_update
                    )
                    logger.info(f"Pushed updates to {count} Google Contacts")
                else:
                    logger.info("No Google Contacts to update")
                
            except Exception as e:
                logger.error(f"Failed to push updates to Google: {e}")
        
        logger.info(f"LinkedIn sync completed: {result.imported} imported, {result.updated} updated, {result.matched} matched")
        return result
        
    except Exception as e:
        logger.error(f"LinkedIn sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"LinkedIn sync failed: {str(e)}")

@app.get("/api/contacts", response_model=List[Contact])
async def get_contacts(search: Optional[str] = None) -> List[Contact]:
    """Get all contacts with optional search"""
    try:
        contacts = await db.get_contacts(search_query=search)
        return contacts
    except Exception as e:
        logger.error(f"Get contacts failed: {e}")
        return []

@app.get("/api/contacts/uncategorized", response_model=List[Contact])
async def get_uncategorized_contacts() -> List[Contact]:
    """Get contacts missing relationship data"""
    try:
        contacts = await db.get_uncategorized_contacts()
        return contacts or []
    except Exception as e:
        logger.error(f"Get uncategorized contacts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get uncategorized contacts: {str(e)}")

@app.get("/api/contacts/{contact_id}", response_model=Contact)
async def get_contact(contact_id: str) -> Contact:
    """Get specific contact by ID"""
    try:
        contact = await db.get_contact_by_id(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get contact failed for ID {contact_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve contact: {str(e)}")

@app.get("/api/edges", response_model=List[ContactEdge])
async def get_edges() -> List[ContactEdge]:
    """Get all relationship edges"""
    try:
        edges = await db.get_edges()
        logger.info(f"Retrieved {len(edges)} edges from database")
        return edges or []
    except Exception as e:
        logger.error(f"Get edges failed: {e}")
        return []

@app.post("/api/contacts/{contact_id}/tags")
async def add_contact_tag(contact_id: str, tag_request: TagRequest):
    """Add manual tag to contact"""
    try:
        await db.add_contact_tag(contact_id, tag_request.tag)
        
        # Sync to Google if authenticated
        if google_auth.has_credentials():
            try:
                contact = await db.get_contact_by_id(contact_id)
                if contact:
                    contacts_service.update_contact_google(
                        google_auth.get_credentials(), 
                        contact
                    )
            except Exception as e:
                logger.error(f"Failed to sync tag to Google: {e}")
                
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Add tag failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add tag")

@app.delete("/api/contacts/{contact_id}/tags/{tag}")
async def remove_contact_tag(contact_id: str, tag: str):
    """Remove tag from contact"""
    try:
        await db.remove_contact_tag(contact_id, tag)
        
        # Sync to Google if authenticated
        if google_auth.has_credentials():
            try:
                contact = await db.get_contact_by_id(contact_id)
                if contact:
                    contacts_service.update_contact_google(
                        google_auth.get_credentials(), 
                        contact
                    )
            except Exception as e:
                logger.error(f"Failed to sync tag removal to Google: {e}")
                
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Remove tag failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove tag")

@app.put("/api/contacts/{contact_id}/notes")
async def update_contact_notes(contact_id: str, notes_request: NotesRequest):
    """Update notes for contact"""
    try:
        # Update local DB first
        await db.update_contact_notes(contact_id, notes_request.notes)
        
        # Try to update in Google Contacts if authenticated
        if google_auth.has_credentials():
            try:
                # Fetch the full updated contact to sync all fields
                contact = await db.get_contact_by_id(contact_id)
                if contact:
                    contacts_service.update_contact_google(
                        google_auth.get_credentials(), 
                        contact
                    )
            except Exception as e:
                logger.error(f"Failed to update Google Contacts: {e}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Update notes failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notes")

@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get graph statistics"""
    try:
        stats = await db.get_graph_statistics()
        return stats
    except Exception as e:
        logger.error(f"Get graph stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get graph statistics")

@app.get("/api/graph/path/{source_id}/{target_id}")
async def get_shortest_path(source_id: str, target_id: str):
    """Find shortest path between two contacts"""
    try:
        path = await db.find_shortest_path(source_id, target_id)
        if not path:
            raise HTTPException(status_code=404, detail="No path found between contacts")
        return path
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get shortest path failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to find path")

@app.get("/api/graph/communities")
async def get_communities():
    """Get community detection results"""
    try:
        communities = await db.get_community_detection()
        return communities
    except Exception as e:
        logger.error(f"Get communities failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get communities")

@app.get("/api/backup/download")
async def download_backup():
    """Create and download a backup of all data"""
    try:
        logger.info("Starting backup download request")
        backup_data = await backup_service.create_backup_data()
        logger.info("Backup data created successfully")
        return backup_data
        
    except Exception as e:
        logger.error(f"Backup download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backup download failed: {str(e)}")

@app.post("/api/backup/restore")
async def restore_backup(backup_data: dict, clear_existing: bool = False):
    """Restore data from uploaded backup data"""
    try:
        result = await backup_service.restore_backup_from_data(backup_data, clear_existing)
        return {
            "status": "success",
            "message": "Data restored successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@app.get("/api/organizations", response_model=List[OrganizationNode])
async def get_organizations() -> List[OrganizationNode]:
    """Get all organization nodes"""
    try:
        organizations = await db.get_organizations()
        return organizations or []
    except Exception as e:
        logger.error(f"Get organizations failed: {e}")
        return []

@app.post("/api/geocode")
async def geocode_contacts():
    """Trigger geocoding for contacts missing coordinates"""
    try:
        result = await geocoding_service.geocode_contacts()
        return result
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Geocoding failed: {str(e)}")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_routes(full_path: str):
    if not FRONTEND_INDEX_FILE.is_file():
        raise HTTPException(status_code=404, detail="Not Found")

    if full_path in {"api", "auth"} or full_path.startswith(("api/", "auth/")):
        raise HTTPException(status_code=404, detail="Not Found")

    if full_path:
        resolved_path = (FRONTEND_DIST_DIR / full_path).resolve()
        frontend_root = FRONTEND_DIST_DIR.resolve()
        if resolved_path != frontend_root and frontend_root not in resolved_path.parents:
            raise HTTPException(status_code=404, detail="Not Found")

        if resolved_path.is_file():
            return FileResponse(resolved_path)

    return FileResponse(FRONTEND_INDEX_FILE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=True,
    )
