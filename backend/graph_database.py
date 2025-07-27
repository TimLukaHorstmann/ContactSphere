from neo4j import GraphDatabase as Neo4jDriver
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from models import Contact, ContactEdge, OrganizationNode, OrganizationNode

class GraphDatabase:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        # Default to local Neo4j instance
        default_uri = 'bolt://localhost:7687'
        default_user = 'neo4j'
        default_password = 'neo4j'  # Default Neo4j password
        
        self.driver = Neo4jDriver.driver(
            uri or os.getenv('NEO4J_URI', default_uri),
            auth=(
                user or os.getenv('NEO4J_USER', default_user),
                password or os.getenv('NEO4J_PASSWORD', default_password)
            )
        )
        
    def close(self):
        """Close the database connection"""
        self.driver.close()
        
    def init_db(self):
        """Initialize database constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints
            session.run("CREATE CONSTRAINT contact_id IF NOT EXISTS FOR (c:Contact) REQUIRE c.id IS UNIQUE")
            
            # Create indexes for performance
            session.run("CREATE INDEX contact_name IF NOT EXISTS FOR (c:Contact) ON (c.name)")
            session.run("CREATE INDEX contact_email IF NOT EXISTS FOR (c:Contact) ON (c.email)")
            session.run("CREATE INDEX contact_organization IF NOT EXISTS FOR (c:Contact) ON (c.organization)")
            
    def upsert_contact(self, contact: Contact) -> bool:
        """Insert or update contact, returns True if new contact"""
        with self.driver.session() as session:
            # Check if contact exists
            result = session.run(
                "MATCH (c:Contact {id: $id}) RETURN c",
                id=contact.id
            )
            is_new = not result.single()
            
            # Upsert contact
            session.run("""
                MERGE (c:Contact {id: $id})
                ON CREATE SET c.created_at = datetime()
                SET c.name = $name,
                    c.email = $email,
                    c.phone = $phone,
                    c.organization = $organization,
                    c.previous_organization = $previous_organization,
                    c.city = $city,
                    c.country = $country,
                    c.birthday = $birthday,
                    c.photo_url = $photo_url,
                    c.address = $address,
                    c.street = $street,
                    c.postal_code = $postal_code,
                    c.notes = COALESCE(c.notes, $notes),
                    c.raw_data = $raw_data,
                    c.tags = $tags,
                    c.uncategorized = $uncategorized,
                    c.linkedin_url = $linkedin_url,
                    c.linkedin_company = $linkedin_company,
                    c.linkedin_position = $linkedin_position,
                    c.linkedin_connected_date = $linkedin_connected_date,
                    c.last_linkedin_sync = $last_linkedin_sync,
                    c.updated_at = datetime()
            """, **self._contact_to_dict(contact))
            
            return is_new
            
    def get_contacts(self, search_query: Optional[str] = None) -> List[Contact]:
        """Get all contacts with optional search"""
        with self.driver.session() as session:
            if search_query:
                result = session.run("""
                    MATCH (c:Contact)
                    WHERE toLower(c.name) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.email, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.organization, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.previous_organization, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.city, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.country, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.phone, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.address, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.notes, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.birthday, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.linkedin_company, '')) CONTAINS toLower($search_term)
                       OR toLower(coalesce(c.linkedin_position, '')) CONTAINS toLower($search_term)
                       OR ANY(tag IN coalesce(c.tags, []) WHERE toLower(tag) CONTAINS toLower($search_term))
                    RETURN c
                    ORDER BY c.name
                """, search_term=search_query)
            else:
                result = session.run("""
                    MATCH (c:Contact)
                    RETURN c
                    ORDER BY c.name
                """)
            
            return [self._node_to_contact(record["c"]) for record in result]
            
    def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Contact {id: $id}) RETURN c",
                id=contact_id
            )
            record = result.single()
            return self._node_to_contact(record["c"]) if record else None
            
    def get_uncategorized_contacts(self) -> List[Contact]:
        """Get contacts missing relationship data"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Contact)
                WHERE coalesce(c.uncategorized, false) = true
                RETURN c
                ORDER BY c.name
            """)
            return [self._node_to_contact(record["c"]) for record in result]
            
    def add_edge(self, edge: ContactEdge):
        """Add relationship edge, creating organization nodes for hub connections"""
        with self.driver.session() as session:
            # Check if target is an organization hub
            if edge.target_id.startswith("org_") and edge.metadata and edge.metadata.get("is_hub_connection"):
                # Create organization node if it doesn't exist
                org_name = edge.metadata.get("organization", "Unknown")
                company_size = edge.metadata.get("company_size", 0)
                
                session.run("""
                    MERGE (org:Organization {id: $org_id})
                    ON CREATE SET org.name = $org_name,
                                  org.employee_count = $company_size,
                                  org.created_at = datetime()
                    ON MATCH SET org.employee_count = $company_size
                """, org_id=edge.target_id, org_name=org_name, company_size=company_size)
                
                # Connect contact to organization
                session.run("""
                    MATCH (source:Contact {id: $source_id})
                    MATCH (target:Organization {id: $target_id})
                    MERGE (source)-[r:WORKS_AT]->(target)
                    SET r.strength = $strength,
                        r.metadata = $metadata,
                        r.relationship_type = $relationship_type
                """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relationship_type=edge.relationship_type,
                    strength=edge.strength,
                    metadata=json.dumps(edge.metadata) if edge.metadata else None
                )
            else:
                # Regular contact-to-contact relationship
                rel_type = edge.relationship_type
                session.run(f"""
                    MATCH (source:Contact {{id: $source_id}})
                    MATCH (target:Contact {{id: $target_id}})
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r.strength = $strength,
                        r.metadata = $metadata,
                        r.source_id = $source_id,
                        r.target_id = $target_id,
                        r.relationship_type = $relationship_type
                """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relationship_type=edge.relationship_type,
                    strength=edge.strength,
                    metadata=json.dumps(edge.metadata) if edge.metadata else None
                )
            
    def get_edges(self) -> List[ContactEdge]:
        """Get all relationship edges including organization connections"""
        with self.driver.session() as session:
            # Get contact-to-contact relationships
            result = session.run("""
                MATCH (source:Contact)-[r]->(target:Contact)
                WHERE r.relationship_type IS NOT NULL
                RETURN elementId(r) as edge_id, r, source.id as source_id, target.id as target_id
            """)
            
            edges = []
            for record in result:
                rel = record["r"]
                edge = ContactEdge(
                    id=record["edge_id"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    relationship_type=rel["relationship_type"],
                    strength=rel.get("strength", 1.0),
                    metadata=json.loads(rel["metadata"]) if rel.get("metadata") else None
                )
                edges.append(edge)
            
            # Get contact-to-organization relationships
            result = session.run("""
                MATCH (source:Contact)-[r]->(target:Organization)
                RETURN elementId(r) as edge_id, r, source.id as source_id, target.id as target_id
            """)
            
            for record in result:
                rel = record["r"]
                edge = ContactEdge(
                    id=record["edge_id"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    relationship_type=rel.get("relationship_type", "WORKS_AT"),
                    strength=rel.get("strength", 1.0),
                    metadata=json.loads(rel["metadata"]) if rel.get("metadata") else None
                )
                edges.append(edge)
            
            return edges
            
    def add_contact_tag(self, contact_id: str, tag: str):
        """Add tag to contact"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Contact {id: $contact_id})
                SET c.tags = coalesce(c.tags, []) + CASE WHEN $tag IN coalesce(c.tags, []) THEN [] ELSE [$tag] END
            """, contact_id=contact_id, tag=tag)
            
    def remove_contact_tag(self, contact_id: str, tag: str):
        """Remove tag from contact"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Contact {id: $contact_id})
                SET c.tags = [t IN coalesce(c.tags, []) WHERE t <> $tag]
            """, contact_id=contact_id, tag=tag)
            
    def set_sync_token(self, token: str):
        """Store sync token"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:SyncMeta {key: 'sync_token'})
                SET s.value = $token, s.updated_at = datetime()
            """, token=token)
            
    def get_sync_token(self) -> Optional[str]:
        """Get sync token"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:SyncMeta)
                WHERE coalesce(s.key, '') = 'sync_token'
                RETURN coalesce(s.value, null) as token
            """)
            record = result.single()
            return record["token"] if record else None
            
    def clear_all_edges(self):
        """Clear all relationship edges"""
        with self.driver.session() as session:
            session.run("""
                MATCH ()-[r]-()
                WHERE r.relationship_type IS NOT NULL
                DELETE r
            """)
            
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics for dashboard"""
        with self.driver.session() as session:
            # Count nodes and relationships
            stats_result = session.run("""
                MATCH (c:Contact)
                OPTIONAL MATCH ()-[r]-()
                WHERE r.relationship_type IS NOT NULL
                RETURN count(DISTINCT c) as contact_count, count(DISTINCT r) as relationship_count
            """)
            stats = stats_result.single()
            
            # Get relationship type distribution
            rel_types_result = session.run("""
                MATCH ()-[r]-()
                WHERE r.relationship_type IS NOT NULL
                RETURN r.relationship_type as type, count(*) as count
                ORDER BY count DESC
            """)
            relationship_types = {record["type"]: record["count"] for record in rel_types_result}
            
            # Get top connected nodes
            top_connected_result = session.run("""
                MATCH (c:Contact)-[r:CONNECTED]-()
                RETURN c.name as name, count(r) as connections
                ORDER BY connections DESC
                LIMIT 10
            """)
            top_connected = [{"name": record["name"], "connections": record["connections"]} 
                           for record in top_connected_result]
            
            return {
                "contact_count": stats["contact_count"],
                "relationship_count": stats["relationship_count"],
                "relationship_types": relationship_types,
                "top_connected": top_connected
            }
            
    def find_shortest_path(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Find shortest path between two contacts"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (source:Contact {id: $source_id}), (target:Contact {id: $target_id})
                MATCH path = shortestPath((source)-[:CONNECTED*]-(target))
                RETURN [node in nodes(path) | {id: node.id, name: node.name}] as nodes,
                       [rel in relationships(path) | rel.relationship_type] as relationships
            """, source_id=source_id, target_id=target_id)
            
            record = result.single()
            if record:
                return {
                    "nodes": record["nodes"],
                    "relationships": record["relationships"]
                }
            return None
            
    def get_community_detection(self) -> List[Dict[str, Any]]:
        """Get communities using basic clustering"""
        with self.driver.session() as session:
            # Simple community detection based on shared organizations
            result = session.run("""
                MATCH (c:Contact)
                WHERE c.organization IS NOT NULL
                RETURN c.organization as community, collect({id: c.id, name: c.name}) as members
                ORDER BY size(members) DESC
            """)
            
            communities = []
            for record in result:
                if len(record["members"]) > 1:  # Only communities with more than 1 member
                    communities.append({
                        "name": record["community"],
                        "members": record["members"],
                        "size": len(record["members"])
                    })
            
            return communities
            
    def update_contact_notes(self, contact_id: str, notes: str):
        """Update notes for contact"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Contact {id: $contact_id})
                SET c.notes = $notes, c.updated_at = datetime()
            """, contact_id=contact_id, notes=notes)
            
    def get_organizations(self) -> List[OrganizationNode]:
        """Get all organization nodes"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (org:Organization)
                RETURN org
                ORDER BY org.name
            """)
            
            organizations = []
            for record in result:
                node = record["org"]
                org = OrganizationNode(
                    id=node["id"],
                    name=node["name"],
                    employee_count=node.get("employee_count", 0),
                    created_at=node.get("created_at")
                )
                organizations.append(org)
            
            return organizations

    def _contact_to_dict(self, contact: Contact) -> Dict[str, Any]:
        """Convert Contact model to dictionary for Neo4j"""
        return {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "organization": contact.organization,
            "previous_organization": contact.previous_organization,
            "city": contact.city,
            "country": contact.country,
            "birthday": contact.birthday,
            "photo_url": contact.photo_url,
            "address": contact.address,
            "street": contact.street,
            "postal_code": contact.postal_code,
            "notes": contact.notes,
            "raw_data": json.dumps(contact.raw_data),
            "tags": contact.tags,
            "uncategorized": contact.uncategorized,
            "linkedin_url": contact.linkedin_url,
            "linkedin_company": contact.linkedin_company,
            "linkedin_position": contact.linkedin_position,
            "linkedin_connected_date": contact.linkedin_connected_date,
            "last_linkedin_sync": contact.last_linkedin_sync.isoformat() if contact.last_linkedin_sync else None
        }
        
    def _node_to_contact(self, node) -> Contact:
        """Convert Neo4j node to Contact model"""
        # Convert Neo4j DateTime objects to Python datetime objects
        created_at = node.get("created_at")
        updated_at = node.get("updated_at")
        last_linkedin_sync = node.get("last_linkedin_sync")
        
        if created_at and hasattr(created_at, 'to_native'):
            created_at = created_at.to_native()
        if updated_at and hasattr(updated_at, 'to_native'):
            updated_at = updated_at.to_native()
        if last_linkedin_sync and isinstance(last_linkedin_sync, str):
            try:
                last_linkedin_sync = datetime.fromisoformat(last_linkedin_sync)
            except ValueError:
                last_linkedin_sync = None
            
        return Contact(
            id=node["id"],
            name=node["name"],
            email=node.get("email"),
            phone=node.get("phone"),
            organization=node.get("organization"),
            previous_organization=node.get("previous_organization"),
            city=node.get("city"),
            country=node.get("country"),
            birthday=node.get("birthday"),
            photo_url=node.get("photo_url"),
            address=node.get("address"),
            street=node.get("street"),
            postal_code=node.get("postal_code"),
            notes=node.get("notes"),
            raw_data=json.loads(node.get("raw_data", "{}")),
            tags=node.get("tags", []),
            uncategorized=node.get("uncategorized", False),
            created_at=created_at,
            updated_at=updated_at,
            linkedin_url=node.get("linkedin_url"),
            linkedin_company=node.get("linkedin_company"),
            linkedin_position=node.get("linkedin_position"),
            linkedin_connected_date=node.get("linkedin_connected_date"),
            last_linkedin_sync=last_linkedin_sync
        )
