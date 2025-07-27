import requests
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from models import Contact, LinkedInSyncResponse
from graph_database import GraphDatabase
from relationship_inference import RelationshipInference

logger = logging.getLogger(__name__)

class LinkedInService:
    def __init__(self, database: GraphDatabase):
        self.db = database
        self.relationship_inference = RelationshipInference()
        load_dotenv()
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not self.access_token:
            raise RuntimeError("⚠️ LINKEDIN_ACCESS_TOKEN not found in .env")
        
        self.api_version = "202312"
        self.base_url = "https://api.linkedin.com/rest"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.api_version,
            "Content-Type": "application/json",
        }

    def fetch_all_connections(self) -> List[Dict[str, Any]]:
        """Fetch all LinkedIn connections with pagination"""
        all_connections = []
        start = 0
        count = 50
        
        while True:
            try:
                logger.info(f"Fetching LinkedIn connections: start={start}, count={count}")
                data = self._fetch_connections_page(start, count)
                
                # Extract snapshot data
                snapshot_data = data.get("elements", [])
                if not snapshot_data:
                    logger.info("No more LinkedIn connections to fetch")
                    break
                    
                connections = snapshot_data[0].get("snapshotData", [])
                if not connections:
                    logger.info("No more LinkedIn connections in snapshot data")
                    break
                    
                all_connections.extend(connections)
                
                # Check if we got fewer results than requested (last page)
                if len(connections) < count:
                    logger.info(f"Received {len(connections)} connections, which is less than requested {count}. End of data.")
                    break
                    
                start += count
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # 404 typically means we've reached the end of available data
                    logger.info(f"Reached end of LinkedIn connections (404 response at start={start})")
                    break
                else:
                    logger.error(f"HTTP error fetching LinkedIn connections: {e}")
                    break
            except Exception as e:
                logger.error(f"Error fetching LinkedIn connections: {e}")
                break
        
        logger.info(f"Total LinkedIn connections fetched: {len(all_connections)}")
        return all_connections

    def _fetch_connections_page(self, start: int = 0, count: int = 50) -> Dict[str, Any]:
        """Fetch a single page of LinkedIn connections"""
        resp = requests.get(
            f"{self.base_url}/memberSnapshotData",
            headers=self.headers,
            params={
                "q": "criteria",
                "domain": "CONNECTIONS",
                "start": start,
                "count": count,
            }
        )
        resp.raise_for_status()
        return resp.json()

    async def sync_linkedin_contacts(self) -> LinkedInSyncResponse:
        """Sync LinkedIn connections and match with existing contacts"""
        logger.info("Starting LinkedIn contact sync")
        
        linkedin_connections = self.fetch_all_connections()
        
        # Fetch all contacts once and create lookup structures for fast matching
        logger.info("Building contact lookup structures for fast matching...")
        all_contacts = self.db.get_contacts()
        
        # Create efficient lookup dictionaries
        email_lookup = {}
        name_lookup = {}
        fuzzy_name_lookup = {}
        
        for contact in all_contacts:
            # Email lookup (exact match)
            if contact.email:
                email_lookup[contact.email.lower()] = contact
            
            # Full name lookup (exact match)
            name_key = contact.name.lower().strip()
            name_lookup[name_key] = contact
            
            # Fuzzy name lookup (for partial matching)
            name_parts = name_key.split()
            if len(name_parts) >= 2:
                # Store by first+last name combination
                fuzzy_key = f"{name_parts[0]}_{name_parts[-1]}"
                if fuzzy_key not in fuzzy_name_lookup:
                    fuzzy_name_lookup[fuzzy_key] = []
                fuzzy_name_lookup[fuzzy_key].append(contact)
        
        logger.info(f"Built lookups: {len(email_lookup)} emails, {len(name_lookup)} names, {len(fuzzy_name_lookup)} fuzzy names")
        
        imported = 0
        updated = 0
        matched = 0
        
        for linkedin_contact in linkedin_connections:
            try:
                # Try to match with existing contact using fast lookups
                existing_contact = self._find_matching_contact_fast(
                    linkedin_contact, email_lookup, name_lookup, fuzzy_name_lookup
                )
                
                if existing_contact:
                    # Update existing contact with LinkedIn data
                    self._update_contact_with_linkedin_data(existing_contact, linkedin_contact)
                    updated += 1
                    matched += 1
                else:
                    # Create new contact from LinkedIn data
                    new_contact = self._create_contact_from_linkedin(linkedin_contact)
                    self.db.upsert_contact(new_contact)
                    imported += 1
                    
            except Exception as e:
                logger.error(f"Error processing LinkedIn contact {linkedin_contact.get('First Name', '')} {linkedin_contact.get('Last Name', '')}: {e}")
                continue
        
        logger.info(f"LinkedIn sync completed: {imported} imported, {updated} updated, {matched} matched")
        
        # Re-infer relationships since we may have new contacts or updated organization info
        logger.info("Re-inferring relationships after LinkedIn sync...")
        self._infer_relationships()
        
        return LinkedInSyncResponse(
            imported=imported,
            updated=updated,
            matched=matched,
            total_linkedin_contacts=len(linkedin_connections)
        )

    def _find_matching_contact_fast(self, linkedin_contact: Dict[str, Any], 
                                   email_lookup: Dict[str, Contact], 
                                   name_lookup: Dict[str, Contact], 
                                   fuzzy_name_lookup: Dict[str, List[Contact]]) -> Optional[Contact]:
        """Fast contact matching using pre-built lookup dictionaries"""
        first_name = linkedin_contact.get("First Name", "").strip()
        last_name = linkedin_contact.get("Last Name", "").strip()
        company = linkedin_contact.get("Company", "").strip()
        email = linkedin_contact.get("Email Address", "").strip()
        
        if not first_name or not last_name:
            return None
        
        # Strategy 1: Match by email (fastest - O(1) lookup)
        if email:
            contact = email_lookup.get(email.lower())
            if contact:
                return contact
        
        # Strategy 2: Match by full name (fast - O(1) lookup)
        full_name = f"{first_name} {last_name}".lower()
        contact = name_lookup.get(full_name)
        if contact:
            # If company also matches, it's very likely the same person
            if company and contact.organization and company.lower() in contact.organization.lower():
                return contact
            # If no company info, still match by name
            if not company or not contact.organization:
                return contact
        
        # Strategy 3: Fuzzy name matching (still fast - O(1) lookup + small list iteration)
        fuzzy_key = f"{first_name.lower()}_{last_name.lower()}"
        fuzzy_matches = fuzzy_name_lookup.get(fuzzy_key, [])
        
        for contact in fuzzy_matches:
            # Additional validation for fuzzy matches
            contact_name = contact.name.lower()
            if first_name.lower() in contact_name and last_name.lower() in contact_name:
                return contact
        
        return None

    def _update_contact_with_linkedin_data(self, contact: Contact, linkedin_contact: Dict[str, Any]):
        """Update existing contact with LinkedIn data"""
        contact.linkedin_url = linkedin_contact.get("URL", "")
        contact.linkedin_company = linkedin_contact.get("Company", "")
        contact.linkedin_position = linkedin_contact.get("Position", "")
        contact.linkedin_connected_date = linkedin_contact.get("Connected On", "")
        contact.last_linkedin_sync = datetime.now()
        
        # Smart organization handling: preserve original as previous_organization if different
        linkedin_org = linkedin_contact.get("Company", "").strip()
        if linkedin_org:
            if contact.organization and contact.organization.strip():
                # If we have an existing org and it's different from LinkedIn org
                if contact.organization.strip().lower() != linkedin_org.lower():
                    # Move current org to previous_organization (if not already set)
                    if not contact.previous_organization:
                        contact.previous_organization = contact.organization
                    # Update current org to LinkedIn (more current)
                    contact.organization = linkedin_org
            else:
                # No existing org, just use LinkedIn org
                contact.organization = linkedin_org
        
        # Update email if not already set
        linkedin_email = linkedin_contact.get("Email Address", "").strip()
        if not contact.email and linkedin_email:
            contact.email = linkedin_email
        
        self.db.upsert_contact(contact)

    def _create_contact_from_linkedin(self, linkedin_contact: Dict[str, Any]) -> Contact:
        """Create a new contact from LinkedIn data"""
        first_name = linkedin_contact.get("First Name", "").strip()
        last_name = linkedin_contact.get("Last Name", "").strip()
        full_name = f"{first_name} {last_name}".strip()
        
        return Contact(
            id=f"linkedin_{hash(linkedin_contact.get('URL', full_name))}",
            name=full_name,
            email=linkedin_contact.get("Email Address", "").strip() or None,
            organization=linkedin_contact.get("Company", "").strip() or None,
            linkedin_url=linkedin_contact.get("URL", ""),
            linkedin_company=linkedin_contact.get("Company", ""),
            linkedin_position=linkedin_contact.get("Position", ""),
            linkedin_connected_date=linkedin_contact.get("Connected On", ""),
            last_linkedin_sync=datetime.now(),
            raw_data=linkedin_contact,
            tags=["linkedin"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def _infer_relationships(self):
        """Infer relationships between contacts and store edges"""
        # Get all contacts for relationship inference
        all_contacts = self.db.get_contacts()
        logger.info(f"Starting relationship inference for {len(all_contacts)} contacts")
        
        # Clear existing edges to avoid duplicates
        self.db.clear_all_edges()
        
        edges = self.relationship_inference.infer_all_relationships(all_contacts)
        logger.info(f"Inferred {len(edges)} relationships")
        
        for edge in edges:
            self.db.add_edge(edge)
            
        logger.info(f"Stored {len(edges)} edges in database")
