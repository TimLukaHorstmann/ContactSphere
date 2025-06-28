from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List, Dict, Any, Optional, Set
import logging
from datetime import datetime

from graph_database import GraphDatabase
from models import Contact, ContactEdge, SyncResponse
from relationship_inference import RelationshipInference

logger = logging.getLogger(__name__)

class ContactsService:
    def __init__(self, database: GraphDatabase):
        self.db = database
        self.relationship_inference = RelationshipInference()

    async def sync_contacts(self, credentials: Credentials) -> SyncResponse:
        """Sync contacts from Google and infer relationships"""
        service = build('people', 'v1', credentials=credentials)
        
        imported = 0
        updated = 0
        sync_token = self.db.get_sync_token()
        
        # Fetch contacts with pagination
        contacts = []
        next_page_token = None
        
        while True:
            request_params = {
                'resourceName': 'people/me',
                'pageSize': 200,
                'personFields': 'names,emailAddresses,organizations,addresses,birthdays,phoneNumbers,photos,biographies'
            }
            
            if next_page_token:
                request_params['pageToken'] = next_page_token
            elif sync_token:
                request_params['requestSyncToken'] = True
                request_params['syncToken'] = sync_token
                
            try:
                results = service.people().connections().list(**request_params).execute()
                connections = results.get('connections', [])
                
                for person in connections:
                    contact = self._parse_contact(person)
                    if contact:
                        is_new = self.db.upsert_contact(contact)
                        if is_new:
                            imported += 1
                        else:
                            updated += 1
                        contacts.append(contact)
                
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    # Store new sync token
                    new_sync_token = results.get('nextSyncToken')
                    if new_sync_token:
                        self.db.set_sync_token(new_sync_token)
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching contacts: {e}")
                break
        
        # Infer relationships
        self._infer_relationships(contacts)
        
        total_contacts = len(self.db.get_contacts())
        
        return SyncResponse(
            imported=imported,
            updated=updated,
            total_contacts=total_contacts,
            sync_token=self.db.get_sync_token()
        )

    def _parse_contact(self, person: Dict[str, Any]) -> Optional[Contact]:
        """Parse Google People API person to Contact model"""
        resource_name = person.get('resourceName', '')
        contact_id = resource_name.split('/')[-1] if resource_name else ''
        
        if not contact_id:
            return None
            
        # Extract name
        names = person.get('names', [])
        display_name = names[0].get('displayName', '') if names else ''
        if not display_name:
            return None
            
        # Extract email
        emails = person.get('emailAddresses', [])
        email = emails[0].get('value', '') if emails else None
        
        # Extract phone
        phones = person.get('phoneNumbers', [])
        phone = phones[0].get('value', '') if phones else None
        
        # Extract organization
        organizations = person.get('organizations', [])
        organization = organizations[0].get('name', '') if organizations else None
        
        # Extract address details
        addresses = person.get('addresses', [])
        city = None
        country = None
        street = None
        postal_code = None
        formatted_address = None
        if addresses:
            addr = addresses[0]
            city = addr.get('city', '') or None
            country = addr.get('countryCode', '') or None
            street = addr.get('streetAddress', '') or None
            postal_code = addr.get('postalCode', '') or None
            # Create formatted address
            address_parts = [
                addr.get('streetAddress', ''),
                addr.get('city', ''),
                addr.get('region', ''),
                addr.get('postalCode', ''),
                addr.get('country', '')
            ]
            formatted_address = ', '.join(filter(None, address_parts)) or None

        # Extract birthday
        birthdays = person.get('birthdays', [])
        birthday = None
        if birthdays:
            bday = birthdays[0].get('date', {})
            if bday.get('month') and bday.get('day'):
                birthday = f"{bday.get('month', 1):02d}-{bday.get('day', 1):02d}"

        # Extract photo
        photos = person.get('photos', [])
        photo_url = None
        if photos:
            photo_url = photos[0].get('url', '') or None

        # Extract notes/biography
        biographies = person.get('biographies', [])
        notes = None
        if biographies:
            notes = biographies[0].get('value', '') or None
        
        # Check if contact should be marked as uncategorized
        uncategorized = self._is_uncategorized(organization, city, country, email)
        
        return Contact(
            id=contact_id,
            name=display_name,
            email=email,
            phone=phone,
            organization=organization,
            city=city,
            country=country,
            birthday=birthday,
            photo_url=photo_url,
            address=formatted_address,
            street=street,
            postal_code=postal_code,
            notes=notes,  # Now synced from Google Contacts
            raw_data=person,
            tags=[],
            uncategorized=uncategorized
        )

    def _is_uncategorized(self, organization: Optional[str], city: Optional[str], 
                         country: Optional[str], email: Optional[str]) -> bool:
        """Check if contact lacks relationship-inferrable data"""
        return not any([organization, city, country, email])

    def _infer_relationships(self, contacts: List[Contact]):
        """Infer relationships between contacts and store edges"""
        logger.info(f"Starting relationship inference for {len(contacts)} contacts")
        
        # Clear existing edges to avoid duplicates
        self.db.clear_all_edges()
        
        edges = self.relationship_inference.infer_all_relationships(contacts)
        logger.info(f"Inferred {len(edges)} relationships")
        
        for edge in edges:
            self.db.add_edge(edge)
            
        logger.info(f"Stored {len(edges)} edges in database")
