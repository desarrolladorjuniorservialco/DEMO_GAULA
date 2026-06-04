import Graph from 'graphology';
import { applyLouvain, assignCommunityColors, applyNodeSizes, applyLayout } from './graph-layout.js';
import { createInteractionState, createSigmaInstance, updateNeighbors, updateExpandedNeighbors } from './graph-renderer.js';
import { renderNodeDetail, clearPanel, renderLegend, renderFindings } from './graph-panel.js';

let _sigma   = null;
let _graph   = null;
let _state   = null;
let _metric  = 'degree';

// eslint-disable-next-line no-unused-vars
function init(_containerId) {
  // No-op: Sigma mounts lazily on first load() call.
  // The container must exist in the DOM before load() is called.
}

function load(apiData) {
  const container = document.getElementById('osint-graph-canvas');
  if (!container) return;

  if (_sigma) { _sigma.kill(); _sigma = null; _graph = null; _state = null; }

  const nodes = apiData.nodes || [];
  const links = apiData.links || [];

  _graph = new Graph({ type: 'directed', allowSelfLoops: false });

  nodes.forEach(n => {
    _graph.addNode(n.id, {
      label:           n.label,
      type:            n.type || 'person',
      is_target:       n.is_target || false,
      confidence:      n.confidence || 0.8,
      risk_level:      n.risk_level || 'Bajo',
      source_evidence: n.source_evidence || '',
      discovered_at:   n.discovered_at || '',
      metadata:        n.metadata || {},
      x:               (Math.random() - 0.5) * 100,
      y:               (Math.random() - 0.5) * 100,
      size:            10,
    });
  });

  links.forEach((l, i) => {
    if (!_graph.hasNode(l.source) || !_graph.hasNode(l.target)) return;
    try {
      _graph.addEdgeWithKey(`e${i}`, l.source, l.target, {
        relation_type: l.relation_type || '',
        label:         l.label || (l.relation_type || '').replace(/_/g, ' '),
        confidence:    l.confidence || 0.75,
        weight:        l.weight || 1,
      });
    } catch (_) { /* duplicate edge — skip */ }
  });

  if (_graph.order > 1) applyLouvain(_graph);
  assignCommunityColors(_graph);
  applyNodeSizes(_graph, _metric);

  _state  = createInteractionState();
  _sigma  = createSigmaInstance(_graph, container, _state);

  _sigma.on('enterNode', ({ node }) => {
    _state.hoveredNode = node;
    updateNeighbors(_graph, _state, node);
    _sigma.refresh();
  });

  _sigma.on('leaveNode', () => {
    _state.hoveredNode = null;
    _state.neighbors   = new Set();
    _sigma.refresh();
  });

  _sigma.on('clickNode', ({ node }) => {
    const wasSelected = _state.selectedNode === node;
    _state.selectedNode      = wasSelected ? null : node;
    _state.expandedNode      = null;
    _state.expandedNeighbors = new Set();
    updateNeighbors(_graph, _state, _state.selectedNode);
    _sigma.refresh();

    if (_state.selectedNode) renderNodeDetail(_state.selectedNode, _graph, _navigateTo);
    else clearPanel();

    _setBackBtn(false);
  });

  _sigma.on('clickStage', () => {
    _state.selectedNode      = null;
    _state.hoveredNode       = null;
    _state.expandedNode      = null;
    _state.neighbors         = new Set();
    _state.expandedNeighbors = new Set();
    _sigma.refresh();
    clearPanel();
    _setBackBtn(false);
  });

  _sigma.on('doubleClickNode', ({ node, event }) => {
    event.preventSigmaDefault();
    _state.expandedNode  = node;
    _state.selectedNode  = null;
    _state.neighbors     = new Set();
    updateExpandedNeighbors(_graph, _state, node);
    _sigma.refresh();
    _setBackBtn(true);
  });

  applyLayout(_graph, null, () => {
    if (_sigma) {
      _sigma.refresh();
      const fitBtn = document.getElementById('og-fit-btn');
      if (fitBtn) fitBtn.style.display = '';
    }
  });

  renderLegend(_graph, _highlightCommunity);
  renderFindings(apiData.findings || []);
}

function _navigateTo(nodeId) {
  if (!_sigma || !_graph || !_graph.hasNode(nodeId)) return;
  const attrs = _graph.getNodeAttributes(nodeId);
  _sigma.getCamera().animate({ x: attrs.x, y: attrs.y, ratio: 0.4 }, { duration: 400 });
  _state.selectedNode      = nodeId;
  _state.expandedNode      = null;
  _state.expandedNeighbors = new Set();
  updateNeighbors(_graph, _state, nodeId);
  _sigma.refresh();
  renderNodeDetail(nodeId, _graph, _navigateTo);
}

function _highlightCommunity(communityId) {
  if (!_sigma || !_graph) return;

  const alreadyActive = _state.selectedNode !== null &&
    _graph.hasNode(_state.selectedNode) &&
    (_graph.getNodeAttribute(_state.selectedNode, 'community') ?? 0) === communityId &&
    _state.neighbors.size > 0;

  if (alreadyActive) {
    _state.selectedNode = null;
    _state.neighbors    = new Set();
  } else {
    const communityNodes = [];
    _graph.forEachNode((n, attrs) => {
      if ((attrs.community ?? 0) === communityId) communityNodes.push(n);
    });
    _state.selectedNode = communityNodes[0] || null;
    _state.neighbors    = new Set(communityNodes.slice(1));
  }
  _sigma.refresh();
}

function _setBackBtn(visible) {
  const btn = document.getElementById('og-expand-back-btn');
  if (btn) btn.style.display = visible ? '' : 'none';
}

function reset() {
  if (_sigma) { _sigma.kill(); _sigma = null; }
  _graph = null;
  _state = null;
  clearPanel();
  const legend = document.getElementById('og-legend');
  if (legend) legend.innerHTML = '';
  const findingsWrap = document.getElementById('og-findings-wrap');
  if (findingsWrap) findingsWrap.style.display = 'none';
  const fitBtn = document.getElementById('og-fit-btn');
  if (fitBtn) fitBtn.style.display = 'none';
  _setBackBtn(false);
}

function setMetric(metric) {
  if (!_graph || !_sigma) return;
  _metric = metric;
  applyNodeSizes(_graph, metric);
  _sigma.refresh();
}

function fit() {
  if (!_sigma) return;
  _sigma.getCamera().animate({ x: 0, y: 0, ratio: 1 }, { duration: 300 });
}

function clearExpansion() {
  if (!_state || !_sigma) return;
  _state.expandedNode      = null;
  _state.expandedNeighbors = new Set();
  _sigma.refresh();
  _setBackBtn(false);
}

export { init, load, reset, setMetric, fit, clearExpansion };
