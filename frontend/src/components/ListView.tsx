import { Contact } from '@/types/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Mail, Phone, Building, MapPin, FileText, Calendar } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';

interface ListViewProps {
  contacts: Contact[];
  uncategorizedContacts: Contact[];
  onContactSelect: (contact: Contact) => void;
  isLoading: boolean;
}

const ListView = ({ contacts, uncategorizedContacts, onContactSelect, isLoading }: ListViewProps) => {
  const isMobile = useIsMobile();
  // No local search needed - contacts are already filtered by parent component via backend search

  const MobileContactList = ({ contacts, showUncategorized = false }: { contacts: Contact[], showUncategorized?: boolean }) => (
    <div className="space-y-4">
      {contacts.map((contact) => (
        <div
          key={contact.id}
          className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-muted/50"
          onClick={() => onContactSelect(contact)}
        >
          <Avatar className="h-10 w-10">
            {contact.photo_url && (
              <AvatarImage src={contact.photo_url} alt={contact.name} />
            )}
            <AvatarFallback>
              {contact.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="font-medium truncate">{contact.name}</span>
              {showUncategorized && (
                <Badge variant="outline" className="text-[10px] px-1 py-0 h-5">
                  Uncategorized
                </Badge>
              )}
            </div>
            
            {(contact.organization || contact.title) && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground truncate">
                <Building className="h-3 w-3" />
                <span>{[contact.title, contact.organization].filter(Boolean).join(' at ')}</span>
              </div>
            )}
            
            <div className="flex flex-wrap gap-2 mt-1">
              {contact.email && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Mail className="h-3 w-3" />
                  <span className="truncate max-w-[150px]">{contact.email}</span>
                </div>
              )}
            </div>
            
            {contact.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {contact.tags.slice(0, 3).map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-[10px] px-1 py-0 h-5">
                    {tag}
                  </Badge>
                ))}
                {contact.tags.length > 3 && (
                  <span className="text-[10px] text-muted-foreground">+{contact.tags.length - 3}</span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const ContactTable = ({ contacts, showUncategorized = false }: { contacts: Contact[], showUncategorized?: boolean }) => {
    if (isMobile) {
      return <MobileContactList contacts={contacts} showUncategorized={showUncategorized} />;
    }

    return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12"></TableHead>
          <TableHead>Contact</TableHead>
          <TableHead>Organization</TableHead>
          <TableHead>Location</TableHead>
          <TableHead>Additional Info</TableHead>
          <TableHead>Tags</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {contacts.map((contact) => (
          <TableRow
            key={contact.id}
            className="cursor-pointer hover:bg-muted/50"
            onClick={() => onContactSelect(contact)}
          >
            <TableCell>
              <Avatar className="h-8 w-8">
                {contact.photo_url && (
                  <AvatarImage src={contact.photo_url} alt={contact.name} />
                )}
                <AvatarFallback className="text-xs">
                  {contact.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </TableCell>
            <TableCell className="font-medium">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{contact.name}</span>
                  {contact.notes && (
                    <FileText className="h-3 w-3 text-blue-500" />
                  )}
                  {showUncategorized && (
                    <Badge variant="outline" className="text-xs">
                      Uncategorized
                    </Badge>
                  )}
                </div>
                {contact.email && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Mail className="h-3 w-3" />
                    <span>{contact.email}</span>
                  </div>
                )}
                {contact.phone && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Phone className="h-3 w-3" />
                    <span>{contact.phone}</span>
                  </div>
                )}
              </div>
            </TableCell>
            <TableCell>
              {contact.organization ? (
                <div className="flex items-center gap-2">
                  <Building className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm">{contact.organization}</span>
                </div>
              ) : (
                <span className="text-muted-foreground text-sm">—</span>
              )}
            </TableCell>
            <TableCell>
              {contact.city || contact.country ? (
                <div className="flex items-center gap-2">
                  <MapPin className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm">
                    {[contact.city, contact.country].filter(Boolean).join(', ')}
                  </span>
                </div>
              ) : (
                <span className="text-muted-foreground text-sm">—</span>
              )}
            </TableCell>
            <TableCell>
              <div className="space-y-1">
                {contact.birthday && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span>{contact.birthday}</span>
                  </div>
                )}
                {contact.notes && (
                  <div className="text-xs text-muted-foreground max-w-32 truncate">
                    {contact.notes}
                  </div>
                )}
              </div>
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {contact.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {contact.tags.length === 0 && (
                  <span className="text-muted-foreground text-sm">—</span>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Contacts */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">
            All Contacts ({contacts.length})
          </TabsTrigger>
          <TabsTrigger value="uncategorized">
            Uncategorized ({uncategorizedContacts.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <Card>
            <CardHeader>
              <CardTitle>All Contacts</CardTitle>
            </CardHeader>
            <CardContent>
              {contacts.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">
                    No contacts found.
                  </p>
                </div>
              ) : (
                <ContactTable contacts={contacts} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="uncategorized">
          <Card>
            <CardHeader>
              <CardTitle>Uncategorized Contacts</CardTitle>
              <p className="text-sm text-muted-foreground">
                Contacts missing organization, location, or other relationship data. 
                Consider enriching these in Google Contacts.
              </p>
            </CardHeader>
            <CardContent>
              {uncategorizedContacts.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">
                    Great! All your contacts have relationship data.
                  </p>
                </div>
              ) : (
                <ContactTable contacts={uncategorizedContacts} showUncategorized />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ListView;
