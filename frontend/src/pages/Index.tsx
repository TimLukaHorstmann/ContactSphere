import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { RefreshCw, Users, Network, Search, Download, Upload } from 'lucide-react';
import GraphViewNew from '@/components/GraphViewNew';
import ListView from '@/components/ListView';
import DetailPanel from '@/components/DetailPanel';
import { Contact, ContactEdge, LinkedInSyncResponse } from '@/types/api';
import { api } from '@/lib/api';

const Index = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const queryClient = useQueryClient();

  // Check auth status on load
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const auth = urlParams.get('auth');
    if (auth === 'success') {
      toast.success('Successfully authenticated with Google!');
      window.history.replaceState({}, '', '/');
    } else if (auth === 'error') {
      toast.error('Authentication failed. Please try again.');
      window.history.replaceState({}, '', '/');
    }
  }, []);

  // Queries
  const { data: contacts = [], isLoading: contactsLoading } = useQuery({
    queryKey: ['contacts', searchQuery],
    queryFn: () => api.getContacts(searchQuery || undefined),
  });

  const { data: edges = [] } = useQuery({
    queryKey: ['edges'],
    queryFn: api.getEdges,
  });

  const { data: uncategorizedContacts = [] } = useQuery({
    queryKey: ['uncategorized'],
    queryFn: api.getUncategorizedContacts,
  });

  // Mutations
  const authMutation = useMutation({
    mutationFn: api.startAuth,
    onSuccess: (data) => {
      window.location.href = data.auth_url;
    },
    onError: (error) => {
      console.error('Auth error:', error);
      toast.error(`Failed to start authentication: ${error.message}`);
    },
  });

  const syncMutation = useMutation({
    mutationFn: api.syncContacts,
    onSuccess: (data) => {
      toast.success(`Sync completed! ${data.imported} imported, ${data.updated} updated`);
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['uncategorized'] });
    },
    onError: (error: any) => {
      if (error?.response?.status === 401) {
        toast.error('Please authenticate first');
      } else {
        toast.error('Sync failed. Please try again.');
      }
    },
  });

  const linkedinSyncMutation = useMutation({
    mutationFn: api.syncLinkedInContacts,
    onSuccess: (data) => {
      toast.success(`LinkedIn sync completed! ${data.imported} imported, ${data.updated} updated, ${data.matched} matched`);
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['uncategorized'] });
    },
    onError: (error: any) => {
      console.error('LinkedIn sync error:', error);
      toast.error('LinkedIn sync failed. Please check your access token and try again.');
    },
  });

  const backupMutation = useMutation({
    mutationFn: api.downloadBackup,
    onSuccess: () => {
      toast.success('Backup downloaded successfully!');
    },
    onError: (error) => {
      console.error('Backup error:', error);
      toast.error('Failed to create backup. Please try again.');
    },
  });

  const handleContactSelect = (contact: Contact) => {
    setSelectedContact(contact);
    setShowDetail(true);
  };

  const totalContacts = contacts.length;
  const totalEdges = edges.length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">ContactGraph</h1>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search contacts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64"
                />
              </div>
              
              <Button
                onClick={() => authMutation.mutate()}
                disabled={authMutation.isPending}
                variant="outline"
              >
                <Users className="h-4 w-4 mr-2" />
                Connect Google
              </Button>
              
              <Button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                Refresh Google
              </Button>
              
              <Button
                onClick={() => linkedinSyncMutation.mutate()}
                disabled={linkedinSyncMutation.isPending}
                variant="outline"
              >
                <svg className={`h-4 w-4 mr-2 ${linkedinSyncMutation.isPending ? 'animate-spin' : ''}`} viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                Sync LinkedIn
              </Button>
              
              <Button
                onClick={() => backupMutation.mutate()}
                disabled={backupMutation.isPending}
                variant="secondary"
              >
                <Download className="h-4 w-4 mr-2" />
                Backup
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="container mx-auto px-4 py-6 max-w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Contacts</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalContacts}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Relationships</CardTitle>
              <Network className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalEdges}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Uncategorized</CardTitle>
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{uncategorizedContacts.length}</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="graph" className="space-y-4">
          <TabsList>
            <TabsTrigger value="graph">Graph View</TabsTrigger>
            <TabsTrigger value="list">List View</TabsTrigger>
          </TabsList>
          
          <TabsContent value="graph">
            <GraphViewNew
              contacts={contacts}
              edges={edges}
              onContactSelect={handleContactSelect}
              isLoading={contactsLoading}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          </TabsContent>
          
          <TabsContent value="list">
            <ListView
              contacts={contacts}
              uncategorizedContacts={uncategorizedContacts}
              onContactSelect={handleContactSelect}
              isLoading={contactsLoading}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Detail Panel */}
      <DetailPanel
        contact={selectedContact}
        open={showDetail}
        onClose={() => setShowDetail(false)}
      />
    </div>
  );
};

export default Index;
