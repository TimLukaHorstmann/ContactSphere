import { useState, useEffect } from 'react';
import { Contact } from '@/types/api';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { Mail, Phone, Building, MapPin, Calendar, Tag, Plus, X, FileText, Home } from 'lucide-react';

interface DetailPanelProps {
  contact: Contact | null;
  open: boolean;
  onClose: () => void;
}

const DetailPanel = ({ contact, open, onClose }: DetailPanelProps) => {
  const [newTag, setNewTag] = useState('');
  const [notes, setNotes] = useState('');
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const queryClient = useQueryClient();

  // Update notes state when contact changes
  useEffect(() => {
    if (contact) {
      setNotes(contact.notes || '');
    }
  }, [contact]);

  const addTagMutation = useMutation({
    mutationFn: ({ contactId, tag }: { contactId: string; tag: string }) =>
      api.addContactTag(contactId, tag),
    onSuccess: () => {
      toast.success('Tag added successfully');
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      setNewTag('');
    },
    onError: () => {
      toast.error('Failed to add tag');
    },
  });

  const removeTagMutation = useMutation({
    mutationFn: ({ contactId, tag }: { contactId: string; tag: string }) =>
      api.removeContactTag(contactId, tag),
    onSuccess: () => {
      toast.success('Tag removed successfully');
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
    onError: () => {
      toast.error('Failed to remove tag');
    },
  });

  const updateNotesMutation = useMutation({
    mutationFn: ({ contactId, notes }: { contactId: string; notes: string }) =>
      api.updateContactNotes(contactId, notes),
    onSuccess: () => {
      toast.success('Notes updated successfully');
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      setIsEditingNotes(false);
    },
    onError: () => {
      toast.error('Failed to update notes');
    },
  });

  const handleAddTag = () => {
    if (!contact || !newTag.trim()) return;
    addTagMutation.mutate({ contactId: contact.id, tag: newTag.trim() });
  };

  const handleRemoveTag = (tag: string) => {
    if (!contact) return;
    removeTagMutation.mutate({ contactId: contact.id, tag });
  };

  const handleSaveNotes = () => {
    if (!contact) return;
    updateNotesMutation.mutate({ contactId: contact.id, notes });
  };

  const handleCancelNotes = () => {
    setNotes(contact?.notes || '');
    setIsEditingNotes(false);
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return null;
    // Handle MM-DD format from birthday
    if (dateStr.includes('-') && dateStr.length === 5) {
      const [month, day] = dateStr.split('-');
      return `${month}/${day}`;
    }
    return dateStr;
  };

  if (!contact) return null;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="!w-[800px] !max-w-[85vw] sm:!w-[1000px] sm:!max-w-[80vw] lg:!w-[1200px] lg:!max-w-[75vw] xl:!w-[1400px] xl:!max-w-[70vw] overflow-hidden">
        <SheetHeader>
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              {contact.photo_url && (
                <AvatarImage src={contact.photo_url} alt={contact.name} />
              )}
              <AvatarFallback className="text-lg">
                {contact.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div>
              <SheetTitle className="text-xl">{contact.name}</SheetTitle>
              {contact.organization && (
                <p className="text-sm text-muted-foreground">{contact.organization}</p>
              )}
            </div>
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-100px)] mt-6">
          <div className="space-y-6">
            {/* Contact Info */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Contact Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {contact.email && (
                  <div className="flex items-center gap-3">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-sm font-medium">Email</span>
                      <p className="text-sm text-muted-foreground">{contact.email}</p>
                    </div>
                  </div>
                )}

                {contact.phone && (
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-sm font-medium">Phone</span>
                      <p className="text-sm text-muted-foreground">{contact.phone}</p>
                    </div>
                  </div>
                )}

                {contact.organization && (
                  <div className="flex items-center gap-3">
                    <Building className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-sm font-medium">Organization</span>
                      <p className="text-sm text-muted-foreground">{contact.organization}</p>
                    </div>
                  </div>
                )}

                {contact.birthday && (
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-sm font-medium">Birthday</span>
                      <p className="text-sm text-muted-foreground">{formatDate(contact.birthday)}</p>
                    </div>
                  </div>
                )}

                {contact.address && (
                  <div className="flex items-start gap-3 md:col-span-2">
                    <Home className="h-4 w-4 text-muted-foreground mt-0.5" />
                    <div>
                      <span className="text-sm font-medium">Address</span>
                      <p className="text-sm text-muted-foreground">{contact.address}</p>
                    </div>
                  </div>
                )}

                {(contact.city || contact.country) && !contact.address && (
                  <div className="flex items-center gap-3">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <span className="text-sm font-medium">Location</span>
                      <p className="text-sm text-muted-foreground">
                        {[contact.city, contact.country].filter(Boolean).join(', ')}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <Separator />

            {/* Tags Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Tags
              </h3>

              {/* Existing Tags */}
              <div className="flex flex-wrap gap-2">
                {contact.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                    {tag}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                      onClick={() => handleRemoveTag(tag)}
                      disabled={removeTagMutation.isPending}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
                {contact.tags.length === 0 && (
                  <span className="text-sm text-muted-foreground">No tags yet</span>
                )}
              </div>

              {/* Add New Tag */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <Label htmlFor="new-tag" className="sr-only">
                    New tag
                  </Label>
                  <Input
                    id="new-tag"
                    placeholder="Add a tag (e.g., mentor, investor, family)"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                  />
                </div>
                <Button
                  onClick={handleAddTag}
                  disabled={!newTag.trim() || addTagMutation.isPending}
                  size="sm"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>

              {/* Preset Tags */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Quick tags:</Label>
                <div className="flex flex-wrap gap-2">
                  {['mentor', 'investor', 'family', 'friend', 'colleague', 'client'].map((presetTag) => (
                    <Button
                      key={presetTag}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (!contact.tags.includes(presetTag)) {
                          addTagMutation.mutate({ contactId: contact.id, tag: presetTag });
                        }
                      }}
                      disabled={contact.tags.includes(presetTag) || addTagMutation.isPending}
                      className="text-xs"
                    >
                      {presetTag}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            <Separator />

            {/* Notes Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Notes
                </h3>
                {!isEditingNotes && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsEditingNotes(true)}
                  >
                    {contact.notes ? 'Edit' : 'Add Notes'}
                  </Button>
                )}
              </div>

              {isEditingNotes ? (
                <div className="space-y-3">
                  <Textarea
                    placeholder="Add your notes about this contact..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="min-h-[100px]"
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleSaveNotes}
                      disabled={updateNotesMutation.isPending}
                    >
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancelNotes}
                      disabled={updateNotesMutation.isPending}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="min-h-[50px]">
                  {contact.notes ? (
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {contact.notes}
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">
                      No notes added yet. Click "Add Notes" to add your thoughts about this contact.
                    </p>
                  )}
                </div>
              )}
            </div>

            <Separator />

            {/* Status */}
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Status</h3>
              {contact.uncategorized ? (
                <Badge variant="outline" className="text-amber-600 border-amber-600">
                  Uncategorized
                </Badge>
              ) : (
                <Badge variant="outline" className="text-green-600 border-green-600">
                  Categorized
                </Badge>
              )}
            </div>

            <Separator />

            {/* Raw Data Preview */}
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Raw Data</h3>
              <div className="bg-muted p-3 rounded-md">
                <pre className="text-xs text-muted-foreground overflow-x-auto">
                  {JSON.stringify(contact.raw_data, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
};

export default DetailPanel;
