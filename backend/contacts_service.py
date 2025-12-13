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
        
        # 1. Fetch Contact Groups (Labels) first
        groups_map = {}
        try:
            groups_result = service.contactGroups().list().execute()
            for group in groups_result.get('contactGroups', []):
                # Map resourceName (contactGroups/123) to formattedName (Label Name)
                # Ignore system groups like 'contactGroups/all' if needed, but formattedName usually handles it
                if group.get('groupType') == 'USER_CONTACT_GROUP':
                    groups_map[group.get('resourceName')] = group.get('formattedName')
        except Exception as e:
            logger.error(f"Error fetching contact groups: {e}")

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
                'personFields': 'names,emailAddresses,organizations,addresses,birthdays,phoneNumbers,photos,biographies,memberships'
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
                    contact = self._parse_contact(person, groups_map)
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

    def batch_update_contacts_google(self, credentials: Credentials, contacts: List[Contact]) -> int:
        """Batch update contacts in Google Contacts"""
        if not contacts:
            return 0
            
        service = build('people', 'v1', credentials=credentials)
        total_updated = 0
        
        # 1. Pre-fetch contact groups mapping once
        existing_groups_map = self._get_all_contact_groups(service)
        
        # Process in chunks of 50
        chunk_size = 50
        for i in range(0, len(contacts), chunk_size):
            chunk = contacts[i:i + chunk_size]
            try:
                updated_count = self._process_batch_update(service, chunk, existing_groups_map)
                total_updated += updated_count
            except Exception as e:
                logger.error(f"Batch update failed for chunk {i}: {e}")
                
        return total_updated

    def _get_all_contact_groups(self, service) -> Dict[str, str]:
        """Get map of 'Group Name' -> 'Resource Name'"""
        groups_map = {}
        try:
            groups_result = service.contactGroups().list(pageSize=1000).execute()
            for group in groups_result.get('contactGroups', []):
                if group.get('groupType') == 'USER_CONTACT_GROUP':
                    # Use formattedName (display name) as key
                    name = group.get('formattedName')
                    if name:
                        groups_map[name] = group.get('resourceName')
        except Exception as e:
            logger.error(f"Error fetching contact groups: {e}")
        return groups_map

    def _process_batch_update(self, service, contacts_chunk: List[Contact], existing_groups_map: Dict[str, str]) -> int:
        # 1. Get current states
        resource_names = [f'people/{c.id}' for c in contacts_chunk]
        
        response = service.people().getBatchGet(
            resourceNames=resource_names,
            personFields='biographies,organizations,memberships,metadata'
        ).execute()
        
        responses = response.get('responses', [])
        contacts_data = {}
        for resp in responses:
            person = resp.get('person')
            if person:
                contacts_data[person.get('resourceName')] = person
        
        # 2. Prepare updates
        batch_contacts = {}
        groups_to_add = {} # group_id -> list of resource_names
        groups_to_remove = {} # group_id -> list of resource_names
        
        # Ensure all needed groups exist
        all_tags = set()
        for c in contacts_chunk:
            if c.tags:
                all_tags.update(c.tags)
        
        # Create missing groups
        for tag in all_tags:
            if tag not in existing_groups_map:
                try:
                    new_group = service.contactGroups().create(
                        body={'contactGroup': {'name': tag}}
                    ).execute()
                    existing_groups_map[tag] = new_group.get('resourceName')
                except Exception as e:
                    logger.error(f"Failed to create group {tag}: {e}")

        for contact in contacts_chunk:
            resource_name = f'people/{contact.id}'
            person = contacts_data.get(resource_name)
            
            if not person:
                continue
                
            etag = person.get('etag')
            biographies = person.get('biographies', [])
            organizations = person.get('organizations', [])
            
            # Update Notes
            if contact.notes:
                if biographies:
                    biographies[0]['value'] = contact.notes
                else:
                    biographies.append({'value': contact.notes, 'contentType': 'TEXT_PLAIN'})
            
            # Update Organizations
            if contact.organization:
                existing_org = next((org for org in organizations if org.get('name') == contact.organization), None)
                if existing_org:
                    existing_org['current'] = True
                    if contact.linkedin_position:
                        existing_org['title'] = contact.linkedin_position
                else:
                    new_org = {'name': contact.organization, 'current': True}
                    if contact.linkedin_position:
                        new_org['title'] = contact.linkedin_position
                    organizations.append(new_org)
                
                for org in organizations:
                    if org.get('name') != contact.organization:
                        org['current'] = False

            batch_contacts[resource_name] = {
                'etag': etag,
                'biographies': biographies,
                'organizations': organizations
            }
            
            # Calculate Group Changes
            if contact.tags is not None:
                current_memberships = person.get('memberships', [])
                current_group_ids = set()
                for m in current_memberships:
                    gid = m.get('contactGroupMembership', {}).get('contactGroupResourceName')
                    if gid:
                        current_group_ids.add(gid)
                
                target_group_ids = set()
                for tag in contact.tags:
                    if tag in existing_groups_map:
                        target_group_ids.add(existing_groups_map[tag])
                
                # Add
                for gid in target_group_ids - current_group_ids:
                    if gid not in groups_to_add:
                        groups_to_add[gid] = []
                    groups_to_add[gid].append(resource_name)
                    
                # Remove (only from user groups we know about)
                known_user_groups = set(existing_groups_map.values())
                for gid in current_group_ids - target_group_ids:
                    if gid in known_user_groups:
                        if gid not in groups_to_remove:
                            groups_to_remove[gid] = []
                        groups_to_remove[gid].append(resource_name)

        # 3. Execute Batch Update
        if batch_contacts:
            service.people().batchUpdateContacts(
                body={
                    'contacts': batch_contacts,
                    'updateMask': 'biographies,organizations',
                    'readMask': 'metadata'
                }
            ).execute()
            
        # 4. Execute Group Updates
        for gid, resource_names in groups_to_add.items():
            try:
                service.contactGroups().members().modify(
                    resourceName=gid,
                    body={'resourceNamesToAdd': resource_names}
                ).execute()
            except Exception as e:
                logger.error(f"Failed to add members to group {gid}: {e}")
                
        for gid, resource_names in groups_to_remove.items():
            try:
                service.contactGroups().members().modify(
                    resourceName=gid,
                    body={'resourceNamesToRemove': resource_names}
                ).execute()
            except Exception as e:
                logger.error(f"Failed to remove members from group {gid}: {e}")

        # Update DB timestamps
        updated_ids = [c.id for c in contacts_chunk if f'people/{c.id}' in batch_contacts]
        self.db.update_last_google_sync_batch(updated_ids)
                
        logger.info(f"Batch updated {len(batch_contacts)} contacts")
        return len(batch_contacts)

    def update_contact_google(self, credentials: Credentials, contact: Contact):
        """Update contact fields in Google Contacts"""
        service = build('people', 'v1', credentials=credentials)
        resource_name = f'people/{contact.id}'
        
        try:
            # 1. Get current contact to get etag and current fields
            person = service.people().get(
                resourceName=resource_name,
                personFields='biographies,organizations,memberships,metadata'
            ).execute()
            
            etag = person.get('etag')
            biographies = person.get('biographies', [])
            organizations = person.get('organizations', [])
            
            # 2. Update Notes (Biographies)
            if contact.notes:
                if biographies:
                    biographies[0]['value'] = contact.notes
                else:
                    biographies.append({'value': contact.notes, 'contentType': 'TEXT_PLAIN'})
            
            # 3. Update Organizations
            # Strategy: If we have a new current organization (from LinkedIn/App),
            # make sure it's in the list and marked as current.
            # Mark other organizations as not current.
            if contact.organization:
                # Check if organization already exists
                existing_org = next((org for org in organizations if org.get('name') == contact.organization), None)
                
                if existing_org:
                    # Update existing to be current
                    existing_org['current'] = True
                    if contact.linkedin_position:
                        existing_org['title'] = contact.linkedin_position
                else:
                    # Add new organization
                    new_org = {
                        'name': contact.organization,
                        'current': True
                    }
                    if contact.linkedin_position:
                        new_org['title'] = contact.linkedin_position
                    organizations.append(new_org)
                
                # Mark others as not current
                for org in organizations:
                    if org.get('name') != contact.organization:
                        org['current'] = False

            # 4. Update Tags (Contact Groups)
            # This is more complex as we need to manage ContactGroups first
            if contact.tags is not None:
                self._sync_contact_groups(service, resource_name, contact.tags)

            body = {
                'etag': etag,
                'biographies': biographies,
                'organizations': organizations
            }
            
            # 5. Execute update
            service.people().updateContact(
                resourceName=resource_name,
                updatePersonFields='biographies,organizations',
                body=body
            ).execute()
            
            # Update last_google_sync timestamp
            self.db.update_last_google_sync(contact.id)
            
            logger.info(f"Successfully updated contact {contact.id} in Google Contacts")
            
        except Exception as e:
            logger.error(f"Error updating contact in Google: {e}")
            raise e

    def _sync_contact_groups(self, service, resource_name: str, tags: List[str]):
        """Sync tags to Google Contact Groups (Labels)"""
        try:
            # 1. Get all existing contact groups
            groups_result = service.contactGroups().list().execute()
            existing_groups = {g.get('name'): g.get('resourceName') for g in groups_result.get('contactGroups', [])}
            # Also map by formattedName for easier lookup
            existing_groups_by_name = {g.get('formattedName'): g.get('resourceName') for g in groups_result.get('contactGroups', [])}
            
            # 2. Create missing groups
            target_group_resource_names = []
            for tag in tags:
                # Check if group exists by name (formattedName)
                if tag in existing_groups_by_name:
                    target_group_resource_names.append(existing_groups_by_name[tag])
                else:
                    # Create new group
                    try:
                        new_group = service.contactGroups().create(
                            body={'contactGroup': {'name': tag}}
                        ).execute()
                        resource_id = new_group.get('resourceName')
                        existing_groups_by_name[tag] = resource_id
                        target_group_resource_names.append(resource_id)
                    except Exception as e:
                        logger.error(f"Failed to create group {tag}: {e}")
            
            # 3. Update memberships
            # First, get current memberships for this contact to know what to remove
            contact = service.people().get(
                resourceName=resource_name,
                personFields='memberships'
            ).execute()
            
            current_memberships = contact.get('memberships', [])
            current_group_ids = set()
            
            for membership in current_memberships:
                group_id = membership.get('contactGroupMembership', {}).get('contactGroupResourceName')
                if group_id:
                    current_group_ids.add(group_id)
            
            target_group_ids = set(target_group_resource_names)
            
            # Groups to add
            to_add = target_group_ids - current_group_ids
            for group_id in to_add:
                try:
                    service.contactGroups().members().modify(
                        resourceName=group_id,
                        body={'resourceNamesToAdd': [resource_name]}
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to add to group {group_id}: {e}")

            # Groups to remove
            # We only remove from USER_CONTACT_GROUPs, not system groups like 'myContacts'
            to_remove = current_group_ids - target_group_ids
            for group_id in to_remove:
                # Check if it's a user group (heuristic: usually starts with contactGroups/)
                # System groups are like 'contactGroups/all' or 'contactGroups/myContacts'
                # But the API returns resource names for all.
                # We should verify if it's a group we manage (i.e., it's in our existing_groups list)
                # If we don't know the group, maybe we shouldn't touch it?
                # But if we want full sync, we should remove.
                # Let's be safe and only remove if it was in the list of user groups we fetched.
                
                # Check if this group_id corresponds to a user group
                is_user_group = False
                for g in groups_result.get('contactGroups', []):
                    if g.get('resourceName') == group_id and g.get('groupType') == 'USER_CONTACT_GROUP':
                        is_user_group = True
                        break
                
                if is_user_group:
                    try:
                        service.contactGroups().members().modify(
                            resourceName=group_id,
                            body={'resourceNamesToRemove': [resource_name]}
                        ).execute()
                    except Exception as e:
                        logger.error(f"Failed to remove from group {group_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error syncing contact groups: {e}")

    def update_contact_notes(self, credentials: Credentials, contact_id: str, notes: str):
        """Legacy method kept for compatibility, redirects to new update method"""
        # We need to fetch the full contact from DB to do a full update
        contact = self.db.get_contact_by_id(contact_id)
        if contact:
            contact.notes = notes
            self.update_contact_google(credentials, contact)

    def _parse_contact(self, person: Dict[str, Any], groups_map: Dict[str, str] = None) -> Optional[Contact]:
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
            
        # Extract tags from memberships
        tags = []
        if groups_map:
            memberships = person.get('memberships', [])
            for membership in memberships:
                group_resource = membership.get('contactGroupMembership', {}).get('contactGroupResourceName')
                if group_resource and group_resource in groups_map:
                    tags.append(groups_map[group_resource])
        
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
            tags=tags,
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
