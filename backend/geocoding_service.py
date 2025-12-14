import aiohttp
import asyncio
import logging
from typing import List, Dict, Any
from graph_database import GraphDatabase
from models import Contact

logger = logging.getLogger(__name__)

class GeocodingService:
    def __init__(self, database: GraphDatabase):
        self.db = database
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "ContactSphere/1.0 (contact@horstmann.tech)"
        }

    async def geocode_contacts(self) -> Dict[str, int]:
        """
        Geocode contacts that have address info but no coordinates.
        Respects Nominatim's rate limit of 1 request per second.
        """
        contacts = await self.db.get_contacts_needing_geocoding()
        logger.info(f"Found {len(contacts)} contacts needing geocoding")
        
        updated_count = 0
        failed_count = 0
        
        async with aiohttp.ClientSession() as session:
            for contact in contacts:
                # Construct query
                query = contact.address
                if not query:
                    parts = []
                    if contact.street: parts.append(contact.street)
                    if contact.postal_code: parts.append(contact.postal_code)
                    if contact.city: parts.append(contact.city)
                    if contact.country: parts.append(contact.country)
                    query = ", ".join(parts)
                
                if not query:
                    continue

                try:
                    params = {
                        "format": "json",
                        "q": query,
                        "limit": 1
                    }
                    
                    async with session.get(self.base_url, params=params, headers=self.headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and len(data) > 0:
                                lat = float(data[0]["lat"])
                                lon = float(data[0]["lon"])
                                
                                await self.db.update_contact_coordinates(contact.id, lat, lon)
                                updated_count += 1
                                logger.info(f"Geocoded {contact.name}: {lat}, {lon}")
                            else:
                                logger.warning(f"No results for {contact.name} ({query})")
                                failed_count += 1
                        else:
                            logger.error(f"Geocoding failed for {contact.name}: {response.status}")
                            failed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error geocoding {contact.name}: {e}")
                    failed_count += 1
                
                # Rate limiting: 1 request per second
                await asyncio.sleep(1.1)
                
        return {
            "total": len(contacts),
            "updated": updated_count,
            "failed": failed_count
        }
