import { Contact } from '@/types/api';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Mail, Building } from 'lucide-react';
import { List, type RowComponentProps } from 'react-window';
import { useIsMobile } from '@/hooks/use-mobile';
import { memo } from 'react';

interface ListViewProps {
  contacts: Contact[];
  uncategorizedContacts: Contact[];
  onContactSelect: (contact: Contact) => void;
  isLoading: boolean;
}

type RowExtraProps = {
  contacts: Contact[];
  onContactSelect: (contact: Contact) => void;
};

const RowComponent = ({ index, style, contacts, onContactSelect, ariaAttributes }: RowComponentProps<RowExtraProps>) => {
  const contact = contacts[index];
  
  return (
    <div style={style} className="px-2 py-1" {...ariaAttributes}>
      <div
        className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-muted/50 h-full"
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
            {contact.uncategorized && (
              <Badge variant="outline" className="text-[10px] px-1 py-0 h-5">
                Uncategorized
              </Badge>
            )}
          </div>
          
          {(contact.organization || contact.linkedin_position) && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground truncate">
              <Building className="h-3 w-3" />
              <span>{[contact.linkedin_position, contact.organization].filter(Boolean).join(' at ')}</span>
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
    </div>
  );
};

const Row = memo(RowComponent);

const ListView = ({ contacts, uncategorizedContacts, onContactSelect, isLoading }: ListViewProps) => {
  const isMobile = useIsMobile();

  if (isLoading) {
    return <div className="p-4 text-center">Loading contacts...</div>;
  }

  if (contacts.length === 0) {
    return <div className="p-4 text-center text-muted-foreground">No contacts found.</div>;
  }

  const rowProps = { contacts, onContactSelect };

  return (
    <div className="h-[calc(100vh-200px)] w-full min-h-[400px]">
      <List
        defaultHeight={400}
        rowCount={contacts.length}
        rowHeight={100}
        rowProps={rowProps}
        rowComponent={(props) => <Row {...props} />}
        style={{ height: '100%', width: '100%' }}
      />
    </div>
  );
};

export default ListView;
