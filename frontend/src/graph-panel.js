import { COMMUNITY_COLORS } from './graph-layout.js';

const TYPE_LABELS = {
  person: 'Persona', alias: 'Alias', email: 'Correo',
  organization: 'Organización', domain: 'Dominio', ip: 'IP',
  repository: 'Repositorio', social_profile: 'Perfil Social',
  location: 'Ubicación', platform: 'Plataforma', url: 'URL',
};

const TYPE_COLORS = {
  person: '#e74c3c', alias: '#e67e22', email: '#4bc8a8',
  organization: '#9b59b6', domain: '#3498db', ip: '#1abc9c',
  repository: '#27ae60', social_profile: '#1DA1F2',
  location: '#f1c40f', platform: '#6b8aaa', url: '#8ab4cc',
};

const RISK_COLOR = { Crítico: '#ff5252', Alto: '#ff9800', Medio: '#f1c40f', Bajo: '#4bc87a', Info: '#6b8aaa' };
const RISK_BG    = { Crítico: '#4a0a0a', Alto: '#3a1a00', Medio: '#2a2a00', Bajo: '#0a1a0a', Info: '#0a1020' };

export function clearPanel() {
  const panel = document.getElementById('og-detail-panel');
  if (panel) panel.style.display = 'none';
  const body = document.getElementById('og-detail-body');
  if (body) body.innerHTML = '<p class="og-detail-placeholder">Selecciona un nodo en el grafo para ver su ficha de inteligencia.</p>';
}

export function renderNodeDetail(nodeId, graph, onNavigate) {
  const panel = document.getElementById('og-detail-panel');
  if (panel) panel.style.display = 'flex';
  const body = document.getElementById('og-detail-body');
  if (!body || !graph.hasNode(nodeId)) return;

  const attrs        = graph.getNodeAttributes(nodeId);
  const typeLabel    = TYPE_LABELS[attrs.type] || attrs.type;
  const typeColor    = TYPE_COLORS[attrs.type] || '#6b8aaa';
  const community    = attrs.community ?? 0;
  const commColor    = COMMUNITY_COLORS[community % COMMUNITY_COLORS.length];
  const risk         = attrs.risk_level || 'Bajo';
  const riskColor    = RISK_COLOR[risk] || '#6b8aaa';
  const riskBg       = RISK_BG[risk] || '#0a1020';
  const confPct      = Math.round((attrs.confidence || 0) * 100);

  let relsHtml = '';
  graph.forEachEdge((_, eAttrs, src, tgt) => {
    if (src !== nodeId && tgt !== nodeId) return;
    const isOut     = src === nodeId;
    const otherId   = isOut ? tgt : src;
    const otherLbl  = graph.getNodeAttribute(otherId, 'label') || otherId;
    const rel       = (eAttrs.relation_type || '').replace(/_/g, ' ');
    const dirColor  = isOut ? '#4bc8a8' : '#aac0dc';
    relsHtml += `<div class="og-d-rel" style="cursor:pointer" data-navigate="${otherId}">
      <span style="color:${dirColor};font-weight:700">${isOut ? '→' : '←'}</span>
      <span style="color:#4bc8a8;margin:0 4px">${rel}</span>
      <span style="color:#8ab4cc">${otherLbl}</span>
    </div>`;
  });

  const meta     = attrs.metadata || {};
  const META_MAP = { language: 'Lenguaje', stars: 'Stars', url: 'URL', karma_total: 'Karma', isp: 'ISP', languages: 'Lenguajes' };
  let metaHtml   = '';
  Object.entries(META_MAP).forEach(([key, lbl]) => {
    if (meta[key] === undefined || meta[key] === null || meta[key] === '') return;
    const raw     = meta[key];
    const display = key === 'url'
      ? `<a href="${raw}" target="_blank" rel="noopener" style="color:#4bc8a8">${String(raw).slice(0, 40)}${String(raw).length > 40 ? '…' : ''}</a>`
      : Array.isArray(raw) ? raw.join(', ') : String(raw);
    metaHtml += `<div class="og-d-row"><span class="og-d-key">${lbl}</span><span class="og-d-val">${display}</span></div>`;
  });

  body.innerHTML = `
    <div style="height:3px;background:${commColor};border-radius:2px 2px 0 0;margin:-12px -12px 10px -12px"></div>
    <div class="og-d-type" style="background:${typeColor}22;color:${typeColor};border:1px solid ${typeColor}44">${typeLabel}</div>
    <div style="font-size:.88rem;font-weight:700;color:#e0eaf8;margin-bottom:6px;word-break:break-all">${attrs.label || nodeId}</div>
    <div style="font-size:.68rem;color:${commColor};margin-bottom:10px">● Comunidad ${community + 1}</div>
    <div class="og-d-row">
      <span class="og-d-key">Riesgo</span>
      <span class="og-d-val"><span style="display:inline-block;padding:1px 7px;border-radius:3px;font-size:.67rem;font-weight:700;text-transform:uppercase;background:${riskBg};color:${riskColor};border:1px solid ${riskColor}44">${risk}</span></span>
    </div>
    <div class="og-d-row">
      <span class="og-d-key">Confianza</span>
      <span class="og-d-val"><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;height:4px;background:#1e2535;border-radius:2px;overflow:hidden"><div style="height:100%;border-radius:2px;background:linear-gradient(90deg,#1abc9c,#4bc8a8);width:${confPct}%"></div></div><span style="font-size:.7rem;color:#6b8aaa">${confPct}%</span></div></span>
    </div>
    <div class="og-d-row"><span class="og-d-key">Fuente</span><span class="og-d-val">${(attrs.source_evidence || '').replace(/_/g, ' ')}</span></div>
    <div class="og-d-row"><span class="og-d-key">Detectado</span><span class="og-d-val">${attrs.discovered_at || '—'}</span></div>
    ${metaHtml}
    ${relsHtml ? `<div class="og-d-section">Relaciones</div>${relsHtml}` : ''}
  `;

  body.querySelectorAll('[data-navigate]').forEach(el =>
    el.addEventListener('click', () => onNavigate(el.dataset.navigate))
  );
}

export function renderLegend(graph, onHighlightCommunity) {
  const el = document.getElementById('og-legend');
  if (!el) return;

  const counts = {};
  graph.forEachNode((_, attrs) => {
    const c = attrs.community ?? 0;
    counts[c] = (counts[c] || 0) + 1;
  });

  el.innerHTML = Object.entries(counts)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([c, count]) => {
      const color = COMMUNITY_COLORS[Number(c) % COMMUNITY_COLORS.length];
      return `<div class="og-legend-item" style="cursor:pointer" data-community="${c}">
        <div class="og-legend-dot" style="background:${color}"></div>
        <span>Comunidad ${Number(c) + 1} <span style="color:#3a4a5a">(${count})</span></span>
      </div>`;
    }).join('');

  el.querySelectorAll('[data-community]').forEach(item =>
    item.addEventListener('click', () => onHighlightCommunity(Number(item.dataset.community)))
  );
}

export function renderFindings(findings) {
  const wrap = document.getElementById('og-findings-wrap');
  const grid = document.getElementById('og-findings-grid');
  if (!wrap || !grid || !findings || !findings.length) return;

  grid.innerHTML = findings.map(f => `
    <div class="og-finding-card nivel-${f.nivel}">
      <div class="og-finding-head">
        <span class="og-finding-icon">${f.icon || '●'}</span>
        <span class="og-finding-tit">${f.titulo}</span>
      </div>
      <div class="og-finding-desc">${f.descripcion}</div>
    </div>`).join('');
  wrap.style.display = '';
}
