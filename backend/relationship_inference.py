from typing import List, Dict, Set, Optional
from models import Contact, ContactEdge, OrganizationNode
import re
import uuid
import os

class RelationshipInference:
    """Infer relationships between contacts based on shared attributes"""
    
    def __init__(self):
        # Company size thresholds for relationship quality
        self.small_company_threshold = int(os.getenv('SMALL_COMPANY_THRESHOLD', 15))  # Close colleagues
        self.medium_company_threshold = int(os.getenv('MEDIUM_COMPANY_THRESHOLD', 100))  # Coworkers
        # Above 100: acquaintances (low priority)
        
    def infer_all_relationships(self, contacts: List[Contact]) -> List[ContactEdge]:
        """Infer all relationships between contacts"""
        edges = []
        
        # Create lookup dictionaries for efficient matching
        org_groups = self._group_by_attribute(contacts, 'organization')
        city_groups = self._group_by_attribute(contacts, 'city')
        domain_groups = self._group_by_email_domain(contacts)
        birthday_groups = self._group_by_birthday(contacts)
        school_groups = self._group_by_schools(contacts)
        tag_groups = self._group_by_tags(contacts)
        
        # Generate edges with smart company relationship handling
        edges.extend(self._create_company_relationships(org_groups))
        edges.extend(self._create_location_relationships(city_groups))
        edges.extend(self._create_edges_from_groups(domain_groups, 'WORKS_WITH', 0.7))
        edges.extend(self._create_edges_from_groups(birthday_groups, 'SHARES_BIRTHDAY', 0.3))
        edges.extend(self._create_edges_from_groups(school_groups, 'ALUMNI_OF', 0.6))
        edges.extend(self._create_edges_from_groups(tag_groups, 'SHARED_TAG', 0.6))
        
        return edges
    
    def _group_by_tags(self, contacts: List[Contact]) -> Dict[str, List[Contact]]:
        """Group contacts by tags"""
        groups = {}
        for contact in contacts:
            for tag in contact.tags:
                if tag not in groups:
                    groups[tag] = []
                groups[tag].append(contact)
        return {k: v for k, v in groups.items() if len(v) > 1}

    def _group_by_attribute(self, contacts: List[Contact], attr: str) -> Dict[str, List[Contact]]:
        """Group contacts by a specific attribute, including previous_organization"""
        groups = {}
        for contact in contacts:
            # Handle current organization
            value = getattr(contact, attr, None)
            if value and value.strip():
                key = value.strip().lower()
                if key not in groups:
                    groups[key] = []
                groups[key].append(contact)
            
            # Also handle previous_organization if we're grouping by organization
            if attr == 'organization' and contact.previous_organization and contact.previous_organization.strip():
                prev_key = contact.previous_organization.strip().lower()
                if prev_key not in groups:
                    groups[prev_key] = []
                groups[prev_key].append(contact)
                
        return {k: v for k, v in groups.items() if len(v) > 1}  # Only groups with multiple contacts
    
    def _group_by_email_domain(self, contacts: List[Contact]) -> Dict[str, List[Contact]]:
        """Group contacts by email domain"""
        groups = {}
        for contact in contacts:
            if contact.email:
                domain = self._extract_domain(contact.email)
                if domain and self._is_meaningful_domain(domain):
                    if domain not in groups:
                        groups[domain] = []
                    groups[domain].append(contact)
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def _group_by_birthday(self, contacts: List[Contact]) -> Dict[str, List[Contact]]:
        """Group contacts by birthday (month-day)"""
        groups = {}
        for contact in contacts:
            if contact.birthday:
                if contact.birthday not in groups:
                    groups[contact.birthday] = []
                groups[contact.birthday].append(contact)
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def _group_by_schools(self, contacts: List[Contact]) -> Dict[str, List[Contact]]:
        """Group contacts by educational institutions"""
        groups = {}
        for contact in contacts:
            # Look for school indicators in organization or raw data
            schools = self._extract_schools(contact)
            for school in schools:
                if school not in groups:
                    groups[school] = []
                groups[school].append(contact)
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def _create_company_relationships(self, org_groups: Dict[str, List[Contact]]) -> List[ContactEdge]:
        """Create smart company relationships - use hub nodes for large companies"""
        edges = []
        
        for company, contacts in org_groups.items():
            company_size = len(contacts)
            
            # Skip very large companies to avoid noise
            if company_size > 200:
                continue
            
            # For smaller companies (<=10 people), create direct connections
            if company_size <= 10:
                # Direct connections for small teams
                for i, contact1 in enumerate(contacts):
                    for contact2 in contacts[i+1:]:
                        edges.append(ContactEdge(
                            source_id=contact1.id,
                            target_id=contact2.id,
                            relationship_type='CLOSE_COLLEAGUES',
                            strength=0.9,
                            metadata={
                                "organization": company,
                                "company_size": company_size
                            }
                        ))
            else:
                # For larger companies (>10 people), use hub-based approach
                # Create organization node ID (will be handled by the graph database)
                org_id = f"org_{company.lower().replace(' ', '_').replace('.', '').replace(',', '')}"
                
                # Create edges from each contact to the organization hub
                for contact in contacts:
                    edges.append(ContactEdge(
                        source_id=contact.id,
                        target_id=org_id,
                        relationship_type='WORKS_AT',
                        strength=0.7,
                        metadata={
                            "organization": company,
                            "company_size": company_size,
                            "is_hub_connection": True
                        }
                    ))
        
        return edges
    
    def _create_location_relationships(self, city_groups: Dict[str, List[Contact]]) -> List[ContactEdge]:
        """Create location-based relationships with better naming"""
        edges = []
        
        for city, contacts in city_groups.items():
            # Only create relationships for smaller groups to avoid noise
            if len(contacts) > 50:
                continue
                
            for i, contact1 in enumerate(contacts):
                for contact2 in contacts[i+1:]:
                    edges.append(ContactEdge(
                        source_id=contact1.id,
                        target_id=contact2.id,
                        relationship_type='LIVES_IN',
                        strength=0.3,
                        metadata={"city": city}
                    ))
        
        return edges
    
    def _create_edges_from_groups(self, groups: Dict[str, List[Contact]], 
                                   relationship_type: str, strength: float = 1.0) -> List[ContactEdge]:
        """Create edges between all contacts in each group with size limits"""
        edges = []
        for group_key, contacts in groups.items():
            # Skip very large groups to avoid noise
            if len(contacts) > 30:
                continue
                
            # Create edges between all pairs in the group
            for i, contact1 in enumerate(contacts):
                for contact2 in contacts[i+1:]:
                    edges.append(ContactEdge(
                        source_id=contact1.id,
                        target_id=contact2.id,
                        relationship_type=relationship_type,
                        strength=strength,
                        metadata={"shared_attribute": group_key}
                    ))
        return edges

    def _extract_domain(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower().strip()
        return None
    
    def _is_meaningful_domain(self, domain: str) -> bool:
        """Check if domain is meaningful for relationship inference"""
        # Skip common consumer email providers
        consumer_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
            'aol.com', 'icloud.com', 'me.com', 'live.com', 'msn.com',
            'web.de', 'gmx.com', 'gmx.de', 'yandex.com', 'mail.ru',
            't-online.de'
        }
        return domain not in consumer_domains
    
    def _extract_schools(self, contact: Contact) -> Set[str]:
        """Extract school/university names from contact data"""
        schools = set()
        
        # Check organization field for school indicators
        if contact.organization:
            org_lower = contact.organization.lower()
            school_keywords = ['university', 'college', 'school', 'institute', 'academy']
            known_schools = ['mit', 'stanford', 'harvard', 'caltech', 'ucla', 'usc', 'berkeley'
                             'oxford', 'cambridge', 'yale', 'princeton', 'columbia', 'cornell']
            
            if (any(keyword in org_lower for keyword in school_keywords) or 
                any(school in org_lower for school in known_schools)):
                schools.add(contact.organization.strip().lower())
        
        # Check raw data for organizations with school type
        organizations = contact.raw_data.get('organizations', [])
        for org in organizations:
            if org.get('type') == 'school' and org.get('name'):
                schools.add(org['name'].strip().lower())
        
        return schools
