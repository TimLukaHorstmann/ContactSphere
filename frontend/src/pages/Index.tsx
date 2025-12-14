import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from 'sonner';
import { RefreshCw, Users, Network, Search, Download, Upload, Menu } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import GraphView from '@/components/GraphView';
import ListView from '@/components/ListView';
import MapView from '@/components/MapView';
import DetailPanel from '@/components/DetailPanel';
import { Contact, ContactEdge, LinkedInSyncResponse } from '@/types/api';
import { api } from '@/lib/api';

const Index = () => {
  const isMobile = useIsMobile();
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

  const { data: authStatus } = useQuery({
    queryKey: ['authStatus'],
    queryFn: api.getAuthStatus,
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
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Network className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">ContactSphere</h1>
              </div>
              
              {isMobile && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <Menu className="h-5 w-5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => authMutation.mutate()} disabled={authStatus?.authenticated}>
                      <Users className="h-4 w-4 mr-2" />
                      {authStatus?.authenticated ? "Connected" : "Connect Google"}
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => syncMutation.mutate()}>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh Google
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => linkedinSyncMutation.mutate()}>
                      <span className="mr-2 font-bold">in</span>
                      Sync LinkedIn
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => backupMutation.mutate()}>
                      <Download className="h-4 w-4 mr-2" />
                      Backup
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
            
            <div className="flex flex-col gap-4 md:flex-row md:items-center">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search contacts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 w-full md:w-64"
                />
              </div>
              
              {!isMobile && (
                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => authMutation.mutate()}
                    disabled={authMutation.isPending || authStatus?.authenticated}
                    variant={authStatus?.authenticated ? "secondary" : "outline"}
                    size="sm"
                  >
                    <Users className="h-4 w-4 mr-2" />
                    {authStatus?.authenticated ? "Connected" : "Connect"}
                  </Button>
                  
                  <Button
                    onClick={() => syncMutation.mutate()}
                    disabled={syncMutation.isPending}
                    size="sm"
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                  
                  <Button
                    onClick={() => linkedinSyncMutation.mutate()}
                    disabled={linkedinSyncMutation.isPending}
                    variant="outline"
                    size="sm"
                  >
                    <span className="font-bold mr-2">in</span>
                    {linkedinSyncMutation.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      "Sync"
                    )}
                  </Button>
                  
                  <Button
                    onClick={() => backupMutation.mutate()}
                    disabled={backupMutation.isPending}
                    variant="secondary"
                    size="sm"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Backup
                  </Button>
                </div>
              )}
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
        <Tabs defaultValue={isMobile ? "list" : "graph"} className="space-y-4">
          <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
            <TabsTrigger value="graph">Graph</TabsTrigger>
            <TabsTrigger value="list">List</TabsTrigger>
            <TabsTrigger value="map">Map</TabsTrigger>
          </TabsList>
          
          <TabsContent value="graph" className="mt-4 border rounded-lg overflow-hidden bg-card text-card-foreground shadow-sm">
            <GraphView
              contacts={contacts}
              edges={edges}
              onContactSelect={handleContactSelect}
              isLoading={contactsLoading}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          </TabsContent>
          
          <TabsContent value="list" className="mt-4 border rounded-lg overflow-hidden bg-card text-card-foreground shadow-sm">
            <ListView
              contacts={contacts}
              uncategorizedContacts={uncategorizedContacts}
              onContactSelect={handleContactSelect}
              isLoading={contactsLoading}
            />
          </TabsContent>

          <TabsContent value="map" className="mt-4 border rounded-lg overflow-hidden bg-card text-card-foreground shadow-sm">
            <MapView
              contacts={contacts}
              onContactSelect={handleContactSelect}
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
