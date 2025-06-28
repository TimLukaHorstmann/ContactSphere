import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { Contact, ContactEdge } from '@/types/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ZoomIn, ZoomOut, RotateCcw, Search, Filter } from 'lucide-react';

interface GraphViewProps {
  contacts: Contact[];
  edges: ContactEdge[];
  onContactSelect: (contact: Contact) => void;
  isLoading: boolean;
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  group: string;
  contact: Contact;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
}

const GraphView = ({ contacts, edges, onContactSelect, isLoading }: GraphViewProps) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown>>();

  // Get unique relationship types for filtering
  const relationshipTypes = Array.from(new Set(edges.map(edge => edge.relationship_type)));

  // Filter contacts and edges based on search and filters
  const filteredData = {
    contacts: contacts.filter(contact => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        contact.name.toLowerCase().includes(query) ||
        contact.email?.toLowerCase().includes(query) ||
        contact.organization?.toLowerCase().includes(query) ||
        contact.city?.toLowerCase().includes(query) ||
        contact.country?.toLowerCase().includes(query) ||
        contact.notes?.toLowerCase().includes(query) ||
        contact.phone?.toLowerCase().includes(query) ||
        contact.address?.toLowerCase().includes(query) ||
        contact.birthday?.toLowerCase().includes(query) ||
        contact.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }),
    edges: edges.filter(edge => 
      activeFilters.length === 0 || activeFilters.includes(edge.relationship_type)
    )
  };

  useEffect(() => {
    const updateDimensions = () => {
      const container = svgRef.current?.parentElement;
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: Math.max(600, container.clientHeight),
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (!svgRef.current || contacts.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous render

    // Create main container group for zoom/pan
    const container = svg.append("g");

    // Setup zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        container.attr("transform", event.transform);
      });

    svg.call(zoom);
    zoomRef.current = zoom;

    const nodes: GraphNode[] = filteredData.contacts.map(contact => ({
      id: contact.id,
      name: contact.name,
      group: contact.organization || contact.city || 'uncategorized',
      contact,
    }));

    // Only include edges where both source and target nodes are in filtered contacts
    const filteredContactIds = new Set(filteredData.contacts.map(c => c.id));
    const links: GraphLink[] = filteredData.edges
      .filter(edge => 
        filteredContactIds.has(edge.source_id) && 
        (filteredContactIds.has(edge.target_id) || edge.target_id.startsWith('org_'))
      )
      .map(edge => ({
        source: edge.source_id,
        target: edge.target_id,
        type: edge.relationship_type,
      }));

    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force("link", d3.forceLink<GraphNode, GraphLink>(links).id(d => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(dimensions.width / 2, dimensions.height / 2))
      .force("collision", d3.forceCollide().radius(20));

    const link = container.append("g")
      .selectAll("line")
      .data(links)
      .enter().append("line")
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.7);

    const nodeGroup = container.append("g")
      .selectAll("g")
      .data(nodes)
      .enter().append("g")
      .style("cursor", "pointer")
      .call(d3.drag<SVGGElement, GraphNode>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended))
      .on("click", (event, d) => onContactSelect(d.contact));

    const node = nodeGroup.append("circle")
      .attr("r", 10)
      .attr("fill", d => getNodeColor(d.contact))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2);

    const label = nodeGroup.append("text")
      .text(d => d.name)
      .attr("font-size", "12px")
      .attr("dx", 15)
      .attr("dy", 4)
      .attr("fill", "#374151")
      .style("pointer-events", "none")
      .style("user-select", "none");

    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as GraphNode).x!)
        .attr("y1", d => (d.source as GraphNode).y!)
        .attr("x2", d => (d.target as GraphNode).x!)
        .attr("y2", d => (d.target as GraphNode).y!);

      nodeGroup
        .attr("transform", d => `translate(${d.x!},${d.y!})`);
    });

    function dragstarted(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    // Auto-fit the graph after initial positioning
    setTimeout(() => {
      fitToView();
    }, 1000);

  }, [contacts, edges, dimensions, onContactSelect, searchQuery, activeFilters]);

  const fitToView = () => {
    if (!svgRef.current || !zoomRef.current) return;

    const svg = d3.select(svgRef.current);
    const container = svg.select("g").node() as SVGGElement;
    
    if (container) {
      const bounds = container.getBBox();
      const fullWidth = dimensions.width;
      const fullHeight = dimensions.height;
      const width = bounds.width;
      const height = bounds.height;
      const midX = bounds.x + width / 2;
      const midY = bounds.y + height / 2;
      
      const scale = Math.min(fullWidth / width, fullHeight / height) * 0.8;
      const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

      svg.transition()
        .duration(750)
        .call(zoomRef.current.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
    }
  };

  const zoomIn = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.5);
  };

  const zoomOut = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1 / 1.5);
  };

  const resetView = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(750).call(zoomRef.current.transform, d3.zoomIdentity);
  };

  const toggleFilter = (filterType: string) => {
    setActiveFilters(prev => 
      prev.includes(filterType) 
        ? prev.filter(f => f !== filterType)
        : [...prev, filterType]
    );
  };

  const clearFilters = () => {
    setActiveFilters([]);
    setSearchQuery('');
  };

  const getNodeColor = (contact: Contact) => {
    if (contact.uncategorized) return '#94a3b8'; // gray
    
    const colors = {
      colleague: '#3b82f6', // blue
      local: '#10b981', // emerald
      'country-mate': '#8b5cf6', // violet
      'domain-mate': '#f59e0b', // amber
      'birthday-buddy': '#ec4899', // pink
      alumni: '#06b6d4', // cyan
    };

    // Use relationship type from edges or fallback to organization-based color
    const relatedEdge = edges.find(e => e.source_id === contact.id || e.target_id === contact.id);
    if (relatedEdge) {
      return colors[relatedEdge.relationship_type as keyof typeof colors] || '#6b7280';
    }

    return '#6b7280'; // default gray
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-96 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (contacts.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center py-12">
            <p className="text-muted-foreground">No contacts found. Click "Refresh" to sync from Google Contacts.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="relative w-full h-[600px] bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Search and Filter Controls */}
      <div className="absolute top-4 left-4 z-10 bg-white rounded-lg shadow-md p-3 max-w-sm">
        <div className="space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name, email, company, location, notes, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 text-sm"
            />
            {(searchQuery || activeFilters.length > 0) && (
              <div className="text-xs text-muted-foreground mt-1">
                Showing {filteredData.contacts.length} of {contacts.length} contacts
              </div>
            )}
          </div>
          
          {/* Relationship Filters */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Relationships</span>
              {activeFilters.length > 0 && (
                <Button variant="ghost" size="sm" onClick={clearFilters} className="h-6 px-2 text-xs">
                  Clear
                </Button>
              )}
            </div>
            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {relationshipTypes.map(type => (
                <Badge
                  key={type}
                  variant={activeFilters.includes(type) ? "default" : "outline"}
                  className="cursor-pointer text-xs hover:bg-gray-100"
                  onClick={() => toggleFilter(type)}
                >
                  {type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={zoomIn}
          className="bg-white shadow-md"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={zoomOut}
          className="bg-white shadow-md"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={resetView}
          className="bg-white shadow-md"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
      
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="w-full h-full"
      />
    </div>
  );
};

export default GraphView;
