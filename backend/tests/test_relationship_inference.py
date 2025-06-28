import pytest
from models import Contact, ContactEdge
from relationship_inference import RelationshipInference

class TestRelationshipInference:
    def setup_method(self):
        self.inference = RelationshipInference()
    
    def test_colleague_inference(self):
        """Test that contacts with same organization are marked as colleagues"""
        contacts = [
            Contact(id="1", name="John Doe", organization="Small Startup", raw_data={}),
            Contact(id="2", name="Jane Smith", organization="Small Startup", raw_data={}),
            Contact(id="3", name="Bob Johnson", organization="Other Corp", raw_data={})
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        colleague_edges = [e for e in edges if 'COLLEAGUE' in e.relationship_type or 'COWORKER' in e.relationship_type or 'WORKS' in e.relationship_type]
        
        assert len(colleague_edges) == 1
        assert colleague_edges[0].source_id in ["1", "2"]
        assert colleague_edges[0].target_id in ["1", "2"]
    
    def test_local_inference(self):
        """Test that contacts in same city are marked as locals"""
        contacts = [
            Contact(id="1", name="John Doe", city="San Francisco", raw_data={}),
            Contact(id="2", name="Jane Smith", city="San Francisco", raw_data={}),
            Contact(id="3", name="Bob Johnson", city="New York", raw_data={})
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        local_edges = [e for e in edges if e.relationship_type == "LIVES_IN"]
        
        assert len(local_edges) == 1
        assert local_edges[0].metadata["city"] == "san francisco"
    
    def test_domain_mate_inference(self):
        """Test that contacts with same meaningful email domain are connected"""
        contacts = [
            Contact(id="1", name="John Doe", email="john@acme.com", raw_data={}),
            Contact(id="2", name="Jane Smith", email="jane@acme.com", raw_data={}),
            Contact(id="3", name="Bob Johnson", email="bob@gmail.com", raw_data={})
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        domain_edges = [e for e in edges if e.relationship_type == "WORKS_WITH"]
        
        assert len(domain_edges) == 1
        assert domain_edges[0].metadata["shared_attribute"] == "acme.com"
    
    def test_birthday_buddy_inference(self):
        """Test that contacts with same birthday are connected"""
        contacts = [
            Contact(id="1", name="John Doe", birthday="03-15", raw_data={}),
            Contact(id="2", name="Jane Smith", birthday="03-15", raw_data={}),
            Contact(id="3", name="Bob Johnson", birthday="07-20", raw_data={})
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        birthday_edges = [e for e in edges if e.relationship_type == "SHARES_BIRTHDAY"]
        
        assert len(birthday_edges) == 1
        assert birthday_edges[0].metadata["shared_attribute"] == "03-15"
    
    def test_alumni_inference(self):
        """Test that contacts from same school are marked as alumni"""
        contacts = [
            Contact(id="1", name="John Doe", organization="MIT", raw_data={}),
            Contact(id="2", name="Jane Smith", organization="MIT", raw_data={}),
            Contact(id="3", name="Bob Johnson", 
                   raw_data={"organizations": [{"type": "school", "name": "Stanford University"}]})
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        alumni_edges = [e for e in edges if e.relationship_type == "ALUMNI_OF"]
        
        # Should find MIT connection
        mit_edges = [e for e in alumni_edges if "mit" in e.metadata.get("shared_attribute", "")]
        assert len(mit_edges) == 1
    
    def test_no_consumer_email_domains(self):
        """Test that common consumer email domains are ignored"""
        contacts = [
            Contact(id="1", name="John Doe", email="john@gmail.com", raw_data={}),
            Contact(id="2", name="Jane Smith", email="jane@gmail.com", raw_data={}),
        ]
        
        edges = self.inference.infer_all_relationships(contacts)
        domain_edges = [e for e in edges if e.relationship_type == "WORKS_WITH"]
        
        assert len(domain_edges) == 0
    
    def test_extract_domain(self):
        """Test domain extraction from email"""
        assert self.inference._extract_domain("test@example.com") == "example.com"
        assert self.inference._extract_domain("user@DOMAIN.ORG") == "domain.org"
        assert self.inference._extract_domain("invalid_email") is None
    
    def test_is_meaningful_domain(self):
        """Test meaningful domain detection"""
        assert self.inference._is_meaningful_domain("company.com") is True
        assert self.inference._is_meaningful_domain("gmail.com") is False
        assert self.inference._is_meaningful_domain("outlook.com") is False
    
    def test_company_size_relationships(self):
        """Test that company size affects relationship types"""
        # Small company - should create CLOSE_COLLEAGUES
        small_company_contacts = [
            Contact(id=f"small_{i}", name=f"Person {i}", organization="Tiny Startup", raw_data={})
            for i in range(5)
        ]
        
        # Medium company - should create COWORKERS  
        medium_company_contacts = [
            Contact(id=f"med_{i}", name=f"Person {i}", organization="Medium Corp", raw_data={})
            for i in range(50)
        ]
        
        # Large company - should create WORKS_AT
        large_company_contacts = [
            Contact(id=f"large_{i}", name=f"Person {i}", organization="Big Corp", raw_data={})
            for i in range(150)
        ]
        
        # Very large company - should be skipped
        huge_company_contacts = [
            Contact(id=f"huge_{i}", name=f"Person {i}", organization="Massive Corp", raw_data={})
            for i in range(300)
        ]
        
        all_contacts = small_company_contacts + medium_company_contacts + large_company_contacts + huge_company_contacts
        edges = self.inference.infer_all_relationships(all_contacts)
        
        # Check small company relationships
        small_edges = [e for e in edges if e.relationship_type == "CLOSE_COLLEAGUES"]
        assert len(small_edges) > 0
        assert all(e.strength == 0.9 for e in small_edges)
        
        # Check medium company relationships  
        medium_edges = [e for e in edges if e.relationship_type == "COWORKERS"]
        assert len(medium_edges) > 0
        assert all(e.strength == 0.7 for e in medium_edges)
        
        # Check large company relationships
        large_edges = [e for e in edges if e.relationship_type == "WORKS_AT"]
        assert len(large_edges) > 0
        assert all(e.strength == 0.4 for e in large_edges)
        
        # Check that huge company is skipped
        huge_edges = [e for e in edges if 'Massive Corp' in str(e.metadata)]
        assert len(huge_edges) == 0
