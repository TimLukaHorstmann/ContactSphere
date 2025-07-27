export interface Contact {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  organization?: string;
  city?: string;
  country?: string;
  birthday?: string;
  photo_url?: string;
  address?: string;  // Formatted full address
  street?: string;
  postal_code?: string;
  notes?: string;  // User-added notes
  raw_data: Record<string, any>;
  tags: string[];
  uncategorized: boolean;
  created_at?: string;
  updated_at?: string;
  // LinkedIn fields
  linkedin_url?: string;
  linkedin_company?: string;
  linkedin_position?: string;
  linkedin_connected_date?: string;
  last_linkedin_sync?: string;
}

export interface ContactEdge {
  id?: string;  // Changed from number to string to support Neo4j elementId
  source_id: string;
  target_id: string;
  relationship_type: string;
  strength: number;
  metadata?: Record<string, any>;
}

export interface SyncResponse {
  imported: number;
  updated: number;
  total_contacts: number;
  sync_token?: string;
}

export interface AuthResponse {
  auth_url: string;
}

export interface OrganizationNode {
  id: string;
  name: string;
  type: 'organization';
  employee_count: number;
  created_at?: string;
}

export interface LinkedInSyncResponse {
  imported: number;
  updated: number;
  matched: number;
  total_linkedin_contacts: number;
}
