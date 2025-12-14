import { useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Contact } from '@/types/api';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Loader2, MapPin } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// Fix for default marker icon in React Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
});

L.Marker.prototype.options.icon = DefaultIcon;

interface MapViewProps {
  contacts: Contact[];
  onContactSelect: (contact: Contact) => void;
}

const MapView = ({ contacts, onContactSelect }: MapViewProps) => {
  const queryClient = useQueryClient();

  const geocodeMutation = useMutation({
    mutationFn: api.geocodeContacts,
    onSuccess: (data) => {
      toast.success(`Geocoding completed: ${data.updated} updated, ${data.failed} failed`);
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
    onError: (error) => {
      console.error('Geocoding error:', error);
      toast.error('Failed to start geocoding process');
    },
  });

  const markers = useMemo(() => {
    return contacts.map(contact => {
      if (!contact.latitude || !contact.longitude) return null;

      return (
        <Marker key={contact.id} position={[contact.latitude, contact.longitude]}>
          <Popup>
            <div className="flex flex-col items-center gap-2 min-w-[150px]">
              <Avatar className="h-10 w-10">
                {contact.photo_url && (
                  <AvatarImage src={contact.photo_url} alt={contact.name} />
                )}
                <AvatarFallback>
                  {contact.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="text-center">
                <div className="font-bold">{contact.name}</div>
                {contact.organization && <div className="text-xs text-muted-foreground">{contact.organization}</div>}
              </div>
              <Button size="sm" variant="outline" onClick={() => onContactSelect(contact)}>
                View Details
              </Button>
            </div>
          </Popup>
        </Marker>
      );
    }).filter(Boolean);
  }, [contacts, onContactSelect]);

  const contactsWithLocation = contacts.filter(c => c.latitude && c.longitude).length;
  const contactsWithoutLocation = contacts.length - contactsWithLocation;

  return (
    <div className="relative h-[calc(100vh-200px)] w-full min-h-[400px] rounded-lg overflow-hidden border">
      <div className="absolute top-2 right-2 z-[1000] flex flex-col gap-2 items-end">
        <div className="bg-background/90 backdrop-blur p-2 rounded-md shadow-md text-xs border">
          <div className="font-semibold mb-1">Map Stats</div>
          <div>Mapped: {contactsWithLocation}</div>
          <div>Missing: {contactsWithoutLocation}</div>
        </div>
        
        <Button 
          size="sm" 
          variant="secondary" 
          className="shadow-md"
          onClick={() => geocodeMutation.mutate()}
          disabled={geocodeMutation.isPending}
        >
          {geocodeMutation.isPending ? (
            <>
              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
              Geocoding...
            </>
          ) : (
            <>
              <MapPin className="h-3 w-3 mr-2" />
              Update Locations
            </>
          )}
        </Button>
      </div>

      <MapContainer center={[20, 0]} zoom={2} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {markers}
      </MapContainer>
    </div>
  );
};

export default MapView;
