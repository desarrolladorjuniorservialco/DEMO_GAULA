import { describe, it, expect } from 'vitest';
import Graph from 'graphology';
import {
  computeNodeSizes,
  assignCommunityColors,
  COMMUNITY_COLORS,
  TARGET_SIZE,
  MIN_SIZE,
  MAX_SIZE,
} from '../graph-layout.js';

describe('computeNodeSizes — degree metric', () => {
  it('returns TARGET_SIZE for is_target node regardless of degree', () => {
    const g = new Graph({ type: 'directed', allowSelfLoops: false });
    g.addNode('root', { is_target: true });
    g.addNode('leaf', { is_target: false });
    g.addEdge('root', 'leaf');

    const sizes = computeNodeSizes(g, 'degree');
    expect(sizes['root']).toBe(TARGET_SIZE);
  });

  it('sizes hub node larger than leaf node', () => {
    const g = new Graph({ type: 'directed', allowSelfLoops: false });
    ['hub', 'a', 'b', 'c', 'leaf', 'x'].forEach(n => g.addNode(n, { is_target: false }));
    g.addEdge('hub', 'a');
    g.addEdge('hub', 'b');
    g.addEdge('hub', 'c');
    g.addEdge('leaf', 'x');

    const sizes = computeNodeSizes(g, 'degree');
    expect(sizes['hub']).toBeGreaterThan(sizes['leaf']);
  });

  it('keeps non-target sizes in [MIN_SIZE, MAX_SIZE]', () => {
    const g = new Graph({ type: 'directed', allowSelfLoops: false });
    g.addNode('a', { is_target: false });
    g.addNode('b', { is_target: false });
    g.addEdge('a', 'b');

    const sizes = computeNodeSizes(g, 'degree');
    Object.values(sizes).forEach(s => {
      expect(s).toBeGreaterThanOrEqual(MIN_SIZE);
      expect(s).toBeLessThanOrEqual(MAX_SIZE);
    });
  });

  it('handles single isolated node without NaN', () => {
    const g = new Graph({ type: 'directed' });
    g.addNode('solo', { is_target: false });

    const sizes = computeNodeSizes(g, 'degree');
    expect(Number.isFinite(sizes['solo'])).toBe(true);
  });
});

describe('assignCommunityColors', () => {
  it('assigns COMMUNITY_COLORS[0] for community 0', () => {
    const g = new Graph();
    g.addNode('a', { community: 0 });
    assignCommunityColors(g);
    expect(g.getNodeAttribute('a', 'communityColor')).toBe(COMMUNITY_COLORS[0]);
  });

  it('assigns COMMUNITY_COLORS[1] for community 1', () => {
    const g = new Graph();
    g.addNode('b', { community: 1 });
    assignCommunityColors(g);
    expect(g.getNodeAttribute('b', 'communityColor')).toBe(COMMUNITY_COLORS[1]);
  });

  it('wraps palette for community index >= 8', () => {
    const g = new Graph();
    g.addNode('z', { community: 9 });
    assignCommunityColors(g);
    expect(g.getNodeAttribute('z', 'communityColor')).toBe(COMMUNITY_COLORS[9 % COMMUNITY_COLORS.length]);
  });

  it('defaults to community 0 for nodes without community attribute', () => {
    const g = new Graph();
    g.addNode('noComm', {});
    assignCommunityColors(g);
    expect(g.getNodeAttribute('noComm', 'communityColor')).toBe(COMMUNITY_COLORS[0]);
  });
});
