import { useRef, useEffect, useState, useMemo } from 'react';
import { Network, type Network as NetworkType } from 'vis-network';
import { DataSet } from 'vis-data';
import { Contact, ContactEdge } from '@/types/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useIsMobile } from '@/hooks/use-mobile';

interface GraphViewProps {
  contacts: Contact[];
  edges: ContactEdge[];
  onContactSelect: (contact: Contact) => void;
  isLoading: boolean;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

const GraphView = ({ contacts, edges, onContactSelect, isLoading, searchQuery = '', onSearchChange }: GraphViewProps) => {
  const isMobile = useIsMobile();
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  const nodesDataSet = useRef<DataSet<any> | null>(null);
  const edgesDataSet = useRef<DataSet<any> | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [displayedNodeCount, setDisplayedNodeCount] = useState<number>(0);
  const [maxNodes, setMaxNodes] = useState<number>(300);

  // Function to limit nodes for very large networks
  const limitNodesForPerformance = (contacts: Contact[], maxNodesLimit: number = maxNodes): Contact[] => {
    if (contacts.length <= maxNodesLimit) return contacts;
    
    // Prioritize contacts with more connections and those that aren't uncategorized
    const contactsWithEdgeCount = contacts.map(contact => {
      const edgeCount = edges.filter(
        edge => edge.source_id === contact.id || edge.target_id === contact.id
      ).length;
      return { contact, edgeCount };
    });
    
    // Sort by edge count (descending) and filter out uncategorized contacts if necessary
    const sortedContacts = contactsWithEdgeCount
      .sort((a, b) => {
        // First prioritize non-uncategorized contacts
        if (a.contact.uncategorized && !b.contact.uncategorized) return 1;
        if (!a.contact.uncategorized && b.contact.uncategorized) return -1;
        // Then by edge count
        return b.edgeCount - a.edgeCount;
      })
      .map(item => item.contact)
      .slice(0, maxNodesLimit);
      
    return sortedContacts;
  };

  // Function to limit edges for large networks
  const limitEdgesForPerformance = (edges: ContactEdge[], maxEdges: number = 500): ContactEdge[] => {
    if (edges.length <= maxEdges) return edges;
    
    // Sort edges by strength to prioritize stronger relationships
    const sortedEdges = [...edges].sort((a, b) => b.strength - a.strength);
    return sortedEdges.slice(0, maxEdges);
  };

  // Memoized performance-limited contacts to prevent endless loops
  const limitedContacts = useMemo(() => {
    return limitNodesForPerformance(contacts, maxNodes);
  }, [contacts, maxNodes]);

  // Initialize network
  useEffect(() => {
    if (!networkRef.current || limitedContacts.length === 0) return;

    // Clean up previous network
    if (networkInstance.current) {
      networkInstance.current.destroy();
      networkInstance.current = null;
    }

    // Create nodes dataset with performance limits
    setDisplayedNodeCount(limitedContacts.length);
    const nodes = new DataSet(
      limitedContacts.map(contact => ({
        id: contact.id,
        label: contact.name,
        title: `${contact.name}\n${contact.organization || ''}\n${contact.email || ''}`,
        group: getNodeGroup(contact),
        color: getNodeColor(contact),
        font: { size: 12, color: '#2d3748' },
        borderWidth: 1,
        scaling: {
          label: {
            enabled: false
          }
        }
      }))
    );
    nodesDataSet.current = nodes;

    // Create edges dataset with unique IDs
    // First, deduplicate edges to prevent conflicts
    const uniqueEdges = Array.from(
      new Map(limitEdgesForPerformance(edges).map(edge => 
        [`${edge.source_id}-${edge.target_id}-${edge.relationship_type}`, edge]
      )).values()
    );

    const edgesData = new DataSet(
      uniqueEdges.map(edge => ({
        id: `${edge.source_id}-${edge.target_id}-${edge.relationship_type}`,
        from: edge.source_id,
        to: edge.target_id,
        label: formatRelationshipLabel(edge.relationship_type),
        title: `${edge.relationship_type} (strength: ${edge.strength})`,
        color: getEdgeColor(edge.relationship_type),
        width: Math.max(0.5, edge.strength),
        smooth: { 
          enabled: true, 
          type: 'dynamic' as const,
          roundness: 0.5
        },
        font: {
          size: 8,
          color: '#4a5568',
          strokeWidth: 2,
          strokeColor: '#ffffff',
          align: 'horizontal'
        }
      }))
    );
    edgesDataSet.current = edgesData;

    // Network options
    const options = {
      nodes: {
        shape: 'circle',
        size: 15,
        borderWidth: 1,
        shadow: false,
        font: {
          size: 12,
          color: '#2d3748'
        },
        scaling: {
          min: 10,
          max: 20
        },
        chosen: true
      },
      edges: {
        width: 1,
        shadow: false,
        smooth: {
          enabled: true,
          type: 'dynamic',
          roundness: 0.5
        },
        font: {
          size: 10,
          color: '#4a5568',
          strokeWidth: 0,
          align: 'horizontal'
        },
        arrows: {
          to: {
            enabled: false
          }
        },
        color: {
          inherit: false
        },
        selectionWidth: 2
      },
      physics: {
        enabled: true,
        stabilization: { 
          iterations: 150,
          updateInterval: 25,
          fit: true
        },
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 95,
          springConstant: 0.04,
          damping: 0.2,
          avoidOverlap: 0.1
        },
        maxVelocity: 40,
        minVelocity: 0.5,
        solver: 'barnesHut',
        timestep: 0.4,
        adaptiveTimestep: true
      },
      interaction: {
        dragNodes: true,
        dragView: true,
        zoomView: true,
        hover: true,
        selectConnectedEdges: false,
        tooltipDelay: 200
      },
      layout: {
        improvedLayout: false,
        randomSeed: 2
      }
    };

    // Create network
    const network = new Network(networkRef.current, { nodes, edges: edgesData }, options);
    networkInstance.current = network;

    // Add stabilization progress handler
    let isStabilizing = true;
    network.on('stabilizationProgress', function(params) {
      const progress = Math.round(params.iterations / params.total * 100);
      if (networkRef.current) {
        if (!networkRef.current.querySelector('.stabilization-progress')) {
          const progressBar = document.createElement('div');
          progressBar.className = 'stabilization-progress';
          progressBar.style.position = 'absolute';
          progressBar.style.top = '50%';
          progressBar.style.left = '50%';
          progressBar.style.transform = 'translate(-50%, -50%)';
          progressBar.style.background = 'rgba(255, 255, 255, 0.8)';
          progressBar.style.padding = '10px 15px';
          progressBar.style.borderRadius = '4px';
          progressBar.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
          progressBar.style.zIndex = '10';
          progressBar.innerHTML = `<span>Optimizing network layout: ${progress}%</span>`;
          networkRef.current.appendChild(progressBar);
        } else {
          const progressBar = networkRef.current.querySelector('.stabilization-progress');
          if (progressBar) {
            progressBar.innerHTML = `<span>Optimizing network layout: ${progress}%</span>`;
          }
        }
      }
    });

    network.on('stabilizationIterationsDone', function() {
      isStabilizing = false;
      const progressBar = networkRef.current?.querySelector('.stabilization-progress');
      if (progressBar) {
        progressBar.remove();
      }
      
      // Calculate community overlays after stabilization
      updateCommunityOverlays(network, limitedContacts);
    });

    // Event handlers
    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const contact = limitedContacts.find(c => c.id === nodeId);
        if (contact) {
          setSelectedNode(nodeId);
          onContactSelect(contact);
        }
      }
    });

    network.on('doubleClick', (params) => {
      if (params.nodes.length > 0) {
        network.focus(params.nodes[0], { scale: 1.5, animation: true });
      }
    });

    network.on('hoverNode', (params) => {
      networkRef.current!.style.cursor = 'pointer';
    });

    network.on('blurNode', () => {
      networkRef.current!.style.cursor = 'default';
    });

    // Draw community labels directly on canvas for performance
    network.on('afterDrawing', (ctx) => {
      const communities: { [key: string]: { contacts: Contact[] } } = {};
      
      // Group by organization (for companies with 5+ employees)
      limitedContacts.forEach(contact => {
        if (contact.organization && !contact.uncategorized) {
          if (!communities[contact.organization]) {
            communities[contact.organization] = { contacts: [] };
          }
          communities[contact.organization].contacts.push(contact);
        }
      });

      Object.entries(communities).forEach(([communityName, community]) => {
        if (community.contacts.length < 5) return;

        const nodeIds = community.contacts.map(c => c.id);
        const positions = network.getPositions(nodeIds);
        
        if (Object.keys(positions).length > 0) {
          let totalX = 0, totalY = 0, count = 0;
          Object.values(positions).forEach(pos => {
            if (pos) {
              totalX += pos.x;
              totalY += pos.y;
              count++;
            }
          });
          
          if (count > 0) {
            const centerX = totalX / count;
            const centerY = totalY / count;
            
            // Draw text
            const fontSize = Math.min(Math.max(community.contacts.length * 2, 12), 20);
            ctx.font = `bold ${fontSize}px Arial`;
            ctx.fillStyle = '#4a5568';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Add shadow/outline for readability
            ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
            ctx.shadowBlur = 4;
            ctx.lineWidth = 3;
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.strokeText(communityName, centerX, centerY - 20);
            
            ctx.shadowBlur = 0;
            ctx.fillText(communityName, centerX, centerY - 20);
          }
        }
      });
    });

    // Initial fit
    setTimeout(() => {
      if (networkInstance.current) {
        networkInstance.current.fit({ animation: true });
      }
    }, 500);

    return () => {
      if (networkInstance.current) {
        networkInstance.current.destroy();
        networkInstance.current = null;
      }
      nodesDataSet.current = null;
      edgesDataSet.current = null;
    };
  }, [limitedContacts, edges, onContactSelect]);

  // Get unique relationship types from edges (memoized to prevent endless loops)
  const availableRelationshipTypes = useMemo(() => {
    const types = new Set<string>();
    edges.forEach(edge => {
      if (edge.relationship_type) {
        types.add(edge.relationship_type);
      }
    });
    return Array.from(types).sort();
  }, [edges]);

  // Filter contacts based on relationship type (search is handled by backend)
  useEffect(() => {
    if (!networkInstance.current) return;

    const network = networkInstance.current;
    let filteredContacts = limitedContacts;
    let filteredEdges = edges;

    if (filterType !== 'all') {
      if (filterType === 'uncategorized') {
        filteredContacts = limitedContacts.filter(contact => contact.uncategorized);
      } else {
        // Filter by relationship type
        const relevantEdges = edges.filter(edge => edge.relationship_type === filterType);
        const relevantContactIds = new Set<string>();
        relevantEdges.forEach(edge => {
          relevantContactIds.add(edge.source_id);
          relevantContactIds.add(edge.target_id);
        });
        filteredContacts = limitedContacts.filter(contact => relevantContactIds.has(contact.id));
        filteredEdges = relevantEdges;
      }
    }

    // Update network data with performance limits
    const limitedFilteredContacts = limitNodesForPerformance(filteredContacts);
    setDisplayedNodeCount(limitedFilteredContacts.length);
    const nodes = new DataSet(
      limitedFilteredContacts.map(contact => ({
        id: contact.id,
        label: contact.name,
        title: `${contact.name}\n${contact.organization || ''}\n${contact.email || ''}`,
        group: getNodeGroup(contact),
        color: getNodeColor(contact),
        font: { size: 12, color: '#2d3748' },
        borderWidth: selectedNode === contact.id ? 4 : 2,
        borderColor: selectedNode === contact.id ? '#3182ce' : undefined
      }))
    );

    // Update filtered edges to only include edges between our limited nodes
    const filteredEdgesForLimitedNodes = filteredEdges.filter(edge =>
      limitedFilteredContacts.some(c => c.id === edge.source_id) &&
      limitedFilteredContacts.some(c => c.id === edge.target_id)
    );

    // First, deduplicate edges to prevent conflicts
    const uniqueFilteredEdges = Array.from(
      new Map(limitEdgesForPerformance(filteredEdgesForLimitedNodes).map(edge => 
        [`${edge.source_id}-${edge.target_id}-${edge.relationship_type}`, edge]
      )).values()
    );

    const edgesData = new DataSet(
      uniqueFilteredEdges.map(edge => ({
        id: `${edge.source_id}-${edge.target_id}-${edge.relationship_type}`,
        from: edge.source_id,
        to: edge.target_id,
        label: formatRelationshipLabel(edge.relationship_type),
        title: `${edge.relationship_type} (strength: ${edge.strength})`,
        color: getEdgeColor(edge.relationship_type),
        width: Math.max(0.5, edge.strength),
        smooth: { 
          enabled: true, 
          type: 'dynamic' as const,
          roundness: 0.5
        },
        font: {
          size: 8,
          color: '#4a5568',
          strokeWidth: 2,
          strokeColor: '#ffffff',
          align: 'horizontal'
        }
      }))
    );

    network.setData({ nodes, edges: edgesData });
  }, [filterType, limitedContacts, edges, selectedNode]);

  const getNodeGroup = (contact: Contact) => {
    if (contact.uncategorized) return 'uncategorized';
    return contact.organization || contact.city || 'default';
  };

  const formatRelationshipLabel = (relationshipType: string): string => {
    const labelMap = {
      'CLOSE_COLLEAGUES': 'Close Colleagues',
      'COWORKERS': 'Coworkers',
      'WORKS_AT': 'Same Company',
      'WORKS_WITH': 'Same Domain',
      'LIVES_IN': 'Same Location',
      'ALUMNI_OF': 'Alumni',
      'SHARES_BIRTHDAY': 'Birthday',
      'SHARED_TAG': 'Shared Tag',
      // Legacy support
      'colleague': 'Colleague',
      'local': 'Local',
      'country-mate': 'Country',
      'domain-mate': 'Domain',
      'birthday-buddy': 'Birthday',
      'alumni': 'Alumni',
    };
    return labelMap[relationshipType as keyof typeof labelMap] || relationshipType;
  };

  const getNodeColor = (contact: Contact) => {
    if (contact.uncategorized) return { background: '#94a3b8', border: '#64748b' };
    
    const colors = {
      colleague: { background: '#3b82f6', border: '#1d4ed8' },
      local: { background: '#10b981', border: '#047857' },
      'country-mate': { background: '#8b5cf6', border: '#6d28d9' },
      'domain-mate': { background: '#f59e0b', border: '#d97706' },
      'birthday-buddy': { background: '#ec4899', border: '#be185d' },
      alumni: { background: '#06b6d4', border: '#0891b2' },
    };

    // Default color based on organization or location
    const orgHash = (contact.organization || contact.city || 'default')
      .split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    const hue = orgHash % 360;
    
    return {
      background: `hsl(${hue}, 70%, 60%)`,
      border: `hsl(${hue}, 70%, 40%)`
    };
  };

  const getEdgeColor = (relationshipType: string) => {
    const colors = {
      'CLOSE_COLLEAGUES': '#3b82f6',     // Blue - close work relationships
      'COWORKERS': '#60a5fa',            // Light blue - work relationships
      'WORKS_AT': '#93c5fd',             // Lighter blue - same company
      'WORKS_WITH': '#8b5cf6',           // Purple - same domain
      'LIVES_IN': '#10b981',             // Green - same location
      'ALUMNI_OF': '#06b6d4',            // Cyan - same school
      'SHARES_BIRTHDAY': '#ec4899',      // Pink - same birthday
      'SHARED_TAG': '#f43f5e',           // Rose - shared tag
      // Legacy support
      'colleague': '#3b82f6',
      'local': '#10b981',
      'country-mate': '#8b5cf6',
      'domain-mate': '#f59e0b',
      'birthday-buddy': '#ec4899',
      'alumni': '#06b6d4',
    };
    return colors[relationshipType as keyof typeof colors] || '#6b7280';
  };

  const zoomIn = () => {
    if (networkInstance.current) {
      const scale = networkInstance.current.getScale();
      networkInstance.current.moveTo({ scale: scale * 1.3 });
    }
  };

  const zoomOut = () => {
    if (networkInstance.current) {
      const scale = networkInstance.current.getScale();
      networkInstance.current.moveTo({ scale: scale * 0.7 });
    }
  };

  const resetView = () => {
    if (networkInstance.current) {
      networkInstance.current.fit({ animation: true });
    }
  };

  const focusOnNode = () => {
    if (networkInstance.current && selectedNode) {
      networkInstance.current.focus(selectedNode, { scale: 1.5, animation: true });
    }
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
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <span>Contact Network</span>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Max nodes:</label>
              <Input
                type="number"
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="w-20"
                min="10"
                max="1000"
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-full md:w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Contacts</SelectItem>
                <SelectItem value="uncategorized">Uncategorized</SelectItem>
                {availableRelationshipTypes.map(type => (
                  <SelectItem key={type} value={type}>
                    {formatRelationshipLabel(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className={`relative p-0 ${isMobile ? 'h-[500px]' : 'h-[700px]'}`}>
        {/* Controls */}
        <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
          <Button variant="outline" size="sm" onClick={zoomIn} className="bg-white shadow-md">
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={zoomOut} className="bg-white shadow-md">
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={resetView} className="bg-white shadow-md">
            <RotateCcw className="h-4 w-4" />
          </Button>
          {selectedNode && (
            <Button variant="outline" size="sm" onClick={focusOnNode} className="bg-white shadow-md">
              <Maximize2 className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Network container */}
        <div ref={networkRef} className="w-full h-full" />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg">
          <h4 className="text-sm font-semibold mb-2">Relationships</h4>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-blue-500"></div>
              <span className="text-xs">Close Colleagues</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-blue-400"></div>
              <span className="text-xs">Coworkers</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-emerald-500"></div>
              <span className="text-xs">Same Location</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-cyan-500"></div>
              <span className="text-xs">Alumni</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-pink-500"></div>
              <span className="text-xs">Birthday</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-rose-500"></div>
              <span className="text-xs">Shared Tag</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {contacts.length > 150 ? (
              <span>Showing {displayedNodeCount} of {contacts.length} contacts for better performance</span>
            ) : (
              <span>Showing all {contacts.length} contacts</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GraphView;
