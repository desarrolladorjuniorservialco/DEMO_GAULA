import Sigma from 'sigma';
import { NodeBorderProgram } from '@sigma/node-border';
import { TARGET_BORDER_COLOR } from './graph-layout.js';

const TYPE_COLORS = {
  person: '#e74c3c', alias: '#e67e22', email: '#4bc8a8',
  organization: '#9b59b6', domain: '#3498db', ip: '#1abc9c',
  repository: '#27ae60', social_profile: '#1DA1F2',
  location: '#f1c40f', platform: '#6b8aaa', url: '#8ab4cc',
};

const DIM_COLOR        = '#111824';
const DIM_BORDER_COLOR = '#1a2535';

export function createInteractionState() {
  return {
    hoveredNode:       null,
    selectedNode:      null,
    expandedNode:      null,
    neighbors:         new Set(),
    expandedNeighbors: new Set(),
  };
}

export function updateNeighbors(graph, state, nodeId) {
  state.neighbors = new Set();
  if (!nodeId) return;
  graph.forEachNeighbor(nodeId, n => state.neighbors.add(n));
}

export function updateExpandedNeighbors(graph, state, nodeId) {
  state.expandedNeighbors = new Set();
  if (!nodeId) return;
  graph.forEachNeighbor(nodeId, n => state.expandedNeighbors.add(n));
}

export function createSigmaInstance(graph, container, state) {
  return new Sigma(graph, container, {
    nodeProgramClasses: { circle: NodeBorderProgram },
    defaultNodeType:    'circle',
    renderEdgeLabels:   true,
    defaultEdgeColor:   '#2a3a4a',
    defaultEdgeType:    'line',
    labelFont:          '"Inter", "Open Sans", sans-serif',
    labelColor:         { color: '#c0ccdc' },
    labelSize:          12,
    labelWeight:        '400',
    labelDensity:       0.07,
    labelGridCellSize:  60,
    edgeLabelSize:      9,
    zIndex:             true,

    nodeReducer: (node, data) => {
      const attrs      = graph.getNodeAttributes(node);
      const commColor  = attrs.communityColor || '#4E91D9';
      const typeColor  = TYPE_COLORS[attrs.type] || '#6b8aaa';
      const isTarget   = attrs.is_target || false;

      const base = {
        ...data,
        color:       commColor,
        borderColor: isTarget ? TARGET_BORDER_COLOR : typeColor,
        borderSize:  isTarget ? 3 : 1,
        size:        attrs.size || data.size || 10,
        label:       attrs.label,
        zIndex:      isTarget ? 10 : 1,
      };

      if (state.expandedNode) {
        if (node === state.expandedNode || state.expandedNeighbors.has(node))
          return { ...base, zIndex: 5 };
        return { ...base, color: DIM_COLOR, borderColor: DIM_BORDER_COLOR, label: '', zIndex: 0 };
      }

      if (state.hoveredNode || state.selectedNode) {
        const active = state.hoveredNode || state.selectedNode;
        if (node === active || state.neighbors.has(node))
          return { ...base, zIndex: 5 };
        return { ...base, color: DIM_COLOR, borderColor: DIM_BORDER_COLOR, label: '', zIndex: 0 };
      }

      return base;
    },

    edgeReducer: (edge, data) => {
      const [src, tgt] = graph.extremities(edge);
      const eAttrs     = graph.getEdgeAttributes(edge);
      const conf       = eAttrs.confidence || 0.75;

      const base = {
        ...data,
        color:  '#2a3a4a',
        size:   0.5 + conf * 1.5,
        label:  '',
        zIndex: 0,
      };

      if (state.expandedNode) {
        if (src === state.expandedNode || tgt === state.expandedNode)
          return { ...base, color: '#4bc8a8', size: 2, label: eAttrs.label || '', zIndex: 2 };
        return { ...base, hidden: true };
      }

      if (state.hoveredNode || state.selectedNode) {
        const active = state.hoveredNode || state.selectedNode;
        if (src === active || tgt === active)
          return { ...base, color: '#4bc8a8', size: 1.5, label: eAttrs.label || '', zIndex: 2 };
        return { ...base, hidden: true };
      }

      return base;
    },
  });
}
