import pytest
import tempfile
import os
from database import Database
from models import Contact, ContactEdge

class TestDatabase:
    def setup_method(self):
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
        self.db.init_db()
    
    def teardown_method(self):
        # Clean up temporary database
        os.unlink(self.temp_db.name)
    
    def test_init_db(self):
        """Test database initialization"""
        # Database should be created without errors
        assert os.path.exists(self.temp_db.name)
    
    def test_upsert_contact_new(self):
        """Test inserting new contact"""
        contact = Contact(
            id="test_1",
            name="Test User",
            email="test@example.com",
            organization="Test Corp",
            raw_data={"test": "data"}
        )
        
        is_new = self.db.upsert_contact(contact)
        assert is_new is True
        
        # Verify contact was inserted
        retrieved = self.db.get_contact_by_id("test_1")
        assert retrieved is not None
        assert retrieved.name == "Test User"
        assert retrieved.email == "test@example.com"
    
    def test_upsert_contact_update(self):
        """Test updating existing contact"""
        contact = Contact(
            id="test_1",
            name="Test User",
            email="test@example.com",
            raw_data={}
        )
        
        # Insert first time
        is_new = self.db.upsert_contact(contact)
        assert is_new is True
        
        # Update same contact
        contact.name = "Updated User"
        is_new = self.db.upsert_contact(contact)
        assert is_new is False
        
        # Verify update
        retrieved = self.db.get_contact_by_id("test_1")
        assert retrieved.name == "Updated User"
    
    def test_get_contacts_search(self):
        """Test contact search functionality"""
        contacts = [
            Contact(id="1", name="John Doe", email="john@example.com", raw_data={}),
            Contact(id="2", name="Jane Smith", organization="Acme Corp", raw_data={}),
            Contact(id="3", name="Bob Johnson", email="bob@other.com", raw_data={})
        ]
        
        for contact in contacts:
            self.db.upsert_contact(contact)
        
        # Search by name
        results = self.db.get_contacts(search_query="John")
        assert len(results) == 1
        assert results[0].name == "John Doe"
        
        # Search by organization
        results = self.db.get_contacts(search_query="Acme")
        assert len(results) == 1
        assert results[0].name == "Jane Smith"
        
        # Search by email
        results = self.db.get_contacts(search_query="other.com")
        assert len(results) == 1
        assert results[0].name == "Bob Johnson"
    
    def test_add_and_get_edges(self):
        """Test adding and retrieving relationship edges"""
        edge = ContactEdge(
            source_id="1",
            target_id="2",
            relationship_type="CLOSE_COLLEAGUES",
            strength=0.9,
            metadata={"organization": "Test Corp", "company_size": 5}
        )
        
        self.db.add_edge(edge)
        
        edges = self.db.get_edges()
        assert len(edges) == 1
        assert edges[0].source_id == "1"
        assert edges[0].target_id == "2"
        assert edges[0].relationship_type == "CLOSE_COLLEAGUES"
    
    def test_contact_tags(self):
        """Test adding and removing contact tags"""
        contact = Contact(id="test_1", name="Test User", raw_data={})
        self.db.upsert_contact(contact)
        
        # Add tag
        self.db.add_contact_tag("test_1", "friend")
        retrieved = self.db.get_contact_by_id("test_1")
        assert "friend" in retrieved.tags
        
        # Add another tag
        self.db.add_contact_tag("test_1", "colleague")
        retrieved = self.db.get_contact_by_id("test_1")
        assert "friend" in retrieved.tags
        assert "colleague" in retrieved.tags
        
        # Remove tag
        self.db.remove_contact_tag("test_1", "friend")
        retrieved = self.db.get_contact_by_id("test_1")
        assert "friend" not in retrieved.tags
        assert "colleague" in retrieved.tags
    
    def test_sync_token(self):
        """Test sync token storage and retrieval"""
        token = "test_sync_token_12345"
        
        # Initially no token
        assert self.db.get_sync_token() is None
        
        # Set token
        self.db.set_sync_token(token)
        assert self.db.get_sync_token() == token
        
        # Update token
        new_token = "updated_token_67890"
        self.db.set_sync_token(new_token)
        assert self.db.get_sync_token() == new_token
    
    def test_uncategorized_contacts(self):
        """Test retrieving uncategorized contacts"""
        contacts = [
            Contact(id="1", name="Complete User", organization="Test Corp", 
                   city="SF", email="test@example.com", raw_data={}),
            Contact(id="2", name="Incomplete User", uncategorized=True, raw_data={})
        ]
        
        for contact in contacts:
            self.db.upsert_contact(contact)
        
        uncategorized = self.db.get_uncategorized_contacts()
        assert len(uncategorized) == 1
        assert uncategorized[0].name == "Incomplete User"
