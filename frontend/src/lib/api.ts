import { Contact, ContactEdge, SyncResponse, AuthResponse, OrganizationNode, LinkedInSyncResponse } from '@/types/api';

const API_BASE = '';

class ApiClient {
  constructor() {
    // Bind methods to preserve 'this' context
    this.startAuth = this.startAuth.bind(this);
    this.getAuthStatus = this.getAuthStatus.bind(this);
    this.syncContacts = this.syncContacts.bind(this);
    this.syncLinkedInContacts = this.syncLinkedInContacts.bind(this);
    this.getContacts = this.getContacts.bind(this);
    this.getEdges = this.getEdges.bind(this);
    this.getUncategorizedContacts = this.getUncategorizedContacts.bind(this);
    this.addContactTag = this.addContactTag.bind(this);
    this.removeContactTag = this.removeContactTag.bind(this);
    this.updateContactNotes = this.updateContactNotes.bind(this);
    this.getOrganizations = this.getOrganizations.bind(this);
    this.downloadBackup = this.downloadBackup.bind(this);
    this.restoreBackup = this.restoreBackup.bind(this);
    this.geocodeContacts = this.geocodeContacts.bind(this);
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    try {
      const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const error = await response.text();
        console.error(`API Error: ${response.status} ${response.statusText}`, error);
        throw new Error(error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      console.error(`Network Error:`, error);
      throw error;
    }
  }

  async startAuth(): Promise<AuthResponse> {
    const response = await this.fetchWithAuth('/auth/google');
    return response.json();
  }

  async getAuthStatus(): Promise<{ authenticated: boolean }> {
    const response = await this.fetchWithAuth('/api/auth/status');
    return response.json();
  }

  async syncContacts(): Promise<SyncResponse> {
    const response = await this.fetchWithAuth('/api/sync', {
      method: 'POST',
    });
    return response.json();
  }

  async syncLinkedInContacts(): Promise<LinkedInSyncResponse> {
    const response = await this.fetchWithAuth('/api/sync/linkedin', {
      method: 'POST',
    });
    return response.json();
  }

  async getContacts(search?: string): Promise<Contact[]> {
    const url = search ? `/api/contacts?search=${encodeURIComponent(search)}` : '/api/contacts';
    const response = await this.fetchWithAuth(url);
    return response.json();
  }

  async getContact(id: string): Promise<Contact> {
    const response = await this.fetchWithAuth(`/api/contacts/${id}`);
    return response.json();
  }

  async getEdges(): Promise<ContactEdge[]> {
    const response = await this.fetchWithAuth('/api/edges');
    return response.json();
  }

  async getUncategorizedContacts(): Promise<Contact[]> {
    const response = await this.fetchWithAuth('/api/contacts/uncategorized');
    return response.json();
  }

  async addContactTag(contactId: string, tag: string): Promise<void> {
    await this.fetchWithAuth(`/api/contacts/${contactId}/tags`, {
      method: 'POST',
      body: JSON.stringify({ tag }),
    });
  }

  async removeContactTag(contactId: string, tag: string): Promise<Contact> {
    const response = await this.fetchWithAuth(`/api/contacts/${contactId}/tags`, {
      method: 'DELETE',
      body: JSON.stringify({ tag }),
    });
    return response.json();
  }

  async updateContactNotes(contactId: string, notes: string): Promise<void> {
    await this.fetchWithAuth(`/api/contacts/${contactId}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    });
  }

  async getGraphStats(): Promise<any> {
    const response = await this.fetchWithAuth('/api/graph/stats');
    return response.json();
  }

  async getShortestPath(sourceId: string, targetId: string): Promise<any> {
    const response = await this.fetchWithAuth(`/api/graph/path/${sourceId}/${targetId}`);
    return response.json();
  }

  async getCommunities(): Promise<any[]> {
    const response = await this.fetchWithAuth('/api/graph/communities');
    return response.json();
  }

  async downloadBackup(): Promise<void> {
    try {
      console.log('Starting backup download...');
      const response = await this.fetchWithAuth('/api/backup/download');
      const data = await response.json();
      console.log('Backup data received:', data.metadata);
      
      // Create filename with timestamp
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
      const filename = `contactsphere_backup_${timestamp}.json`;
      
      // Create and download file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      console.log('Backup download completed:', filename);
    } catch (error) {
      console.error('Backup download failed:', error);
      throw error;
    }
  }

  async restoreBackup(backupData: any, clearExisting: boolean = false): Promise<any> {
    const response = await this.fetchWithAuth(`/api/backup/restore?clear_existing=${clearExisting}`, {
      method: 'POST',
      body: JSON.stringify(backupData),
    });
    return response.json();
  }

  async getOrganizations(): Promise<OrganizationNode[]> {
    const response = await this.fetchWithAuth('/api/organizations');
    return response.json();
  }

  async geocodeContacts(): Promise<{ total: number; updated: number; failed: number }> {
    const response = await this.fetchWithAuth('/api/geocode', {
      method: 'POST',
    });
    return response.json();
  }
}

export const api = new ApiClient();
