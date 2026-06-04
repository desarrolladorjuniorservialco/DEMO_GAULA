import louvain from 'graphology-communities-louvain';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import circular from 'graphology-layout/circular';
import betweennessCentrality from 'graphology-metrics/centrality/betweenness';

export const COMMUNITY_COLORS = [
  '#4E91D9', '#E8734A', '#5DC896', '#B87FD4',
  '#E8C84A', '#4DC4C4', '#E06B8B', '#8FA8C8',
];

export const TARGET_BORDER_COLOR = '#C8A84B';
export const TARGET_SIZE        = 42;
export const MIN_SIZE           = 6;
export const MAX_SIZE           = 36;

const FA2_SETTINGS = {
  gravity:                        1,
  scalingRatio:                   10,
  strongGravityMode:              false,
  barnesHutOptimize:              true,
  linLogMode:                     true,
  outboundAttractionDistribution: true,
};

export function applyLouvain(graph) {
  try {
    louvain.assign(graph, { resolution: 1 });
  } catch (_) {
    graph.forEachNode(n => graph.setNodeAttribute(n, 'community', 0));
  }
}

export function assignCommunityColors(graph) {
  graph.forEachNode((node, attrs) => {
    const community = attrs.community ?? 0;
    graph.setNodeAttribute(node, 'communityColor', COMMUNITY_COLORS[community % COMMUNITY_COLORS.length]);
  });
}

export function computeNodeSizes(graph, metric = 'degree') {
  const sizes = {};

  if (metric === 'betweenness') {
    betweennessCentrality.assign(graph);
    let maxB = 0;
    graph.forEachNode((_, attrs) => { if ((attrs.betweennessCentrality || 0) > maxB) maxB = attrs.betweennessCentrality; });
    if (maxB === 0) maxB = 1;
    graph.forEachNode((node, attrs) => {
      if (attrs.is_target) { sizes[node] = TARGET_SIZE; return; }
      const b = attrs.betweennessCentrality || 0;
      sizes[node] = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * (b / maxB);
    });
  } else {
    let maxDeg = 1;
    graph.forEachNode(node => { const d = graph.degree(node); if (d > maxDeg) maxDeg = d; });
    graph.forEachNode((node, attrs) => {
      if (attrs.is_target) { sizes[node] = TARGET_SIZE; return; }
      const deg = graph.degree(node) || 1;
      sizes[node] = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * Math.log(deg + 1) / Math.log(maxDeg + 1);
    });
  }
  return sizes;
}

export function applyNodeSizes(graph, metric = 'degree') {
  const sizes = computeNodeSizes(graph, metric);
  graph.forEachNode(node => graph.setNodeAttribute(node, 'size', sizes[node]));
}

export function applyLayout(graph, onProgress, onDone) {
  circular.assign(graph, { scale: 200 });

  let remaining = 400;
  const BATCH   = 50;

  function step() {
    const iter = Math.min(BATCH, remaining);
    forceAtlas2.assign(graph, { iterations: iter, settings: FA2_SETTINGS });
    remaining -= iter;
    if (onProgress) onProgress(1 - remaining / 400);
    if (remaining > 0) requestAnimationFrame(step);
    else if (onDone) onDone();
  }
  requestAnimationFrame(step);
}
