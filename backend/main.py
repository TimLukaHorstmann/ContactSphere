from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from auth import GoogleAuth
from graph_database import GraphDatabase
from contacts_service import ContactsService
from linkedin_service import LinkedInService
from backup_service import BackupService
from models import SyncResponse, Contact, ContactEdge, TagRequest, NotesRequest, OrganizationNode, LinkedInSyncResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ContactSphere API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
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

@app.on_event("startup")
async def startup():
    db.init_db()
    logger.info("ContactSphere API started")

@app.get("/")
async def root():
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

@app.get("/auth/google/callback")
async def google_auth_callback(code: str, state: str = None):
    """Handle Google OAuth callback"""
    try:
        credentials = google_auth.exchange_code(code)
        # Store credentials in session/memory for this demo
        google_auth.store_credentials(credentials)
        return RedirectResponse(url="http://localhost:8080?auth=success")
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        return RedirectResponse(url="http://localhost:8080?auth=error")

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
        
        logger.info(f"LinkedIn sync completed: {result.imported} imported, {result.updated} updated, {result.matched} matched")
        return result
        
    except Exception as e:
        logger.error(f"LinkedIn sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"LinkedIn sync failed: {str(e)}")

@app.get("/api/contacts", response_model=List[Contact])
async def get_contacts(search: Optional[str] = None) -> List[Contact]:
    """Get all contacts with optional search"""
    try:
        contacts = db.get_contacts(search_query=search)
        return contacts
    except Exception as e:
        logger.error(f"Get contacts failed: {e}")
        return []

@app.get("/api/contacts/uncategorized", response_model=List[Contact])
async def get_uncategorized_contacts() -> List[Contact]:
    """Get contacts missing relationship data"""
    try:
        contacts = db.get_uncategorized_contacts()
        return contacts or []
    except Exception as e:
        logger.error(f"Get uncategorized contacts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get uncategorized contacts: {str(e)}")

@app.get("/api/contacts/{contact_id}", response_model=Contact)
async def get_contact(contact_id: str) -> Contact:
    """Get specific contact by ID"""
    try:
        contact = db.get_contact_by_id(contact_id)
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
        edges = db.get_edges()
        logger.info(f"Retrieved {len(edges)} edges from database")
        return edges or []
    except Exception as e:
        logger.error(f"Get edges failed: {e}")
        return []

@app.post("/api/contacts/{contact_id}/tags")
async def add_contact_tag(contact_id: str, tag_request: TagRequest):
    """Add manual tag to contact"""
    try:
        db.add_contact_tag(contact_id, tag_request.tag)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Add tag failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add tag")

@app.delete("/api/contacts/{contact_id}/tags/{tag}")
async def remove_contact_tag(contact_id: str, tag: str):
    """Remove tag from contact"""
    try:
        db.remove_contact_tag(contact_id, tag)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Remove tag failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove tag")

@app.put("/api/contacts/{contact_id}/notes")
async def update_contact_notes(contact_id: str, notes_request: NotesRequest):
    """Update notes for contact"""
    try:
        db.update_contact_notes(contact_id, notes_request.notes)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Update notes failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notes")

@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get graph statistics"""
    try:
        stats = db.get_graph_statistics()
        return stats
    except Exception as e:
        logger.error(f"Get graph stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get graph statistics")

@app.get("/api/graph/path/{source_id}/{target_id}")
async def get_shortest_path(source_id: str, target_id: str):
    """Find shortest path between two contacts"""
    try:
        path = db.find_shortest_path(source_id, target_id)
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
        communities = db.get_community_detection()
        return communities
    except Exception as e:
        logger.error(f"Get communities failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get communities")

@app.get("/api/backup/download")
async def download_backup():
    """Create and download a backup of all data"""
    try:
        backup_data = backup_service.create_backup_data()
        return backup_data
        
    except Exception as e:
        logger.error(f"Backup download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup download failed: {str(e)}")

@app.post("/api/backup/restore")
async def restore_backup(backup_data: dict, clear_existing: bool = False):
    """Restore data from uploaded backup data"""
    try:
        result = backup_service.restore_backup_from_data(backup_data, clear_existing)
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
        organizations = db.get_organizations()
        return organizations or []
    except Exception as e:
        logger.error(f"Get organizations failed: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
