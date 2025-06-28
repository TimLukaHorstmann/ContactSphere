from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class Contact(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    birthday: Optional[str] = None
    photo_url: Optional[str] = None
    address: Optional[str] = None  # Formatted full address
    street: Optional[str] = None
    postal_code: Optional[str] = None
    notes: Optional[str] = None  # User-added notes
    raw_data: Dict[str, Any]
    tags: List[str] = []
    uncategorized: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ContactEdge(BaseModel):
    id: Optional[str] = None  # Changed from int to str to support Neo4j elementId
    source_id: str
    target_id: str
    relationship_type: str
    strength: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

class SyncResponse(BaseModel):
    imported: int
    updated: int
    total_contacts: int
    sync_token: Optional[str] = None

class AuthResponse(BaseModel):
    auth_url: str

class TagRequest(BaseModel):
    tag: str

class NotesRequest(BaseModel):
    notes: str

class OrganizationNode(BaseModel):
    id: str  # Format: "org_{organization_name_slug}"
    name: str
    type: str = "organization"
    employee_count: int = 0
    created_at: Optional[datetime] = None
