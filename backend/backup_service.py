import json
from datetime import datetime
from typing import List, Dict, Any
import logging

from graph_database import GraphDatabase
from models import Contact, ContactEdge

logger = logging.getLogger(__name__)

class BackupService:
    """Service for backing up and restoring ContactSphere data"""

    def __init__(self, database: GraphDatabase):
        self.db = database
        
    def create_backup_data(self) -> Dict[str, Any]:
        """
        Create backup data dictionary
        Returns the backup data as a dictionary ready for download
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Export all data
            contacts = self._export_contacts()
            edges = self._export_edges()
            sync_token = self.db.get_sync_token()
            
            backup_data = {
                "metadata": {
                    "timestamp": timestamp,
                    "version": "1.0",
                    "contact_count": len(contacts),
                    "edge_count": len(edges),
                    "created_at": datetime.now().isoformat(),
                    "app_name": "ContactSphere",
                },
                "contacts": contacts,
                "edges": edges,
                "sync_token": sync_token
            }
            
            logger.info(f"Backup data prepared with {len(contacts)} contacts and {len(edges)} edges")
            return backup_data
            
        except Exception as e:
            logger.error(f"Backup data creation failed: {e}")
            raise
    
    def restore_backup_from_data(self, backup_data: Dict[str, Any], clear_existing: bool = False) -> Dict[str, int]:
        """
        Restore data from backup data dictionary
        Returns statistics about the restore operation
        """
        try:
            # Clear existing data if requested
            if clear_existing:
                self._clear_database()
            
            # Restore contacts
            contacts_restored = 0
            for contact_data in backup_data.get('contacts', []):
                contact = Contact(**contact_data)
                self.db.upsert_contact(contact)
                contacts_restored += 1
            
            # Restore edges
            edges_restored = 0
            for edge_data in backup_data.get('edges', []):
                edge = ContactEdge(**edge_data)
                self.db.add_edge(edge)
                edges_restored += 1
            
            # Restore sync token
            sync_token = backup_data.get('sync_token')
            if sync_token:
                self.db.set_sync_token(sync_token)
            
            result = {
                "contacts_restored": contacts_restored,
                "edges_restored": edges_restored,
                "sync_token_restored": bool(sync_token)
            }
            
            logger.info(f"Restore completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
    
    def _export_contacts(self) -> List[Dict[str, Any]]:
        """Export all contacts to a list of dictionaries"""
        contacts = self.db.get_contacts()
        return [contact.model_dump() for contact in contacts]
    
    def _export_edges(self) -> List[Dict[str, Any]]:
        """Export all edges to a list of dictionaries"""
        edges = self.db.get_edges()
        return [edge.model_dump() for edge in edges]
    
    def _clear_database(self):
        """Clear all data from the database"""
        logger.warning("Clearing all database data")
        with self.db.driver.session() as session:
            # Delete all relationships first
            session.run("MATCH ()-[r]-() DELETE r")
            # Delete all nodes
            session.run("MATCH (n) DELETE n")
