// AgentWorld GUI — pure Canvas 2D, zero dependencies
// Views: 2D spatial map + drive timeline + interaction heatmap

// ── State ──
let zones = [];
let entities = {};          // id -> {name, zone, pos, type, sprite, displayX, displayY, targetX, targetY, color}
let entityList = [];
let interactionArrows = []; // [{fx,fy,tx,ty,alpha,created}]
let driveHistory = {};      // agentId -> [{ts, hunger, thirst, social, energy, fun, mood}]
let interactionPairs = [];  // [{agent, target, count}]
let currentView = 'map';
let selectedAgent = null;
let maxTime = 0;
let _ws = null;
let _clockTs = 0;
let _overlapData = null; // {offsets: {eid: {dx,dy}}, stacks: [{x,y,members:[eid]}]}

// Agent color palette (12 distinct hues)
const AGENT_HUES = [0, 30, 60, 120, 180, 210, 270, 300, 15, 45, 90, 330];
const DRIVE_COLORS = {
  hunger: '#22c55e', thirst: '#39d2c0', social: '#d29922',
  energy: '#f97316', fun: '#a371f7', mood: '#f472b6'
};
const DRIVE_NAMES = { hunger:'hunger', thirst:'thirst', social:'social', energy:'energy', fun:'fun', mood:'mood' };

// ── WebSocket ──

function connect() {
  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  _ws = new WebSocket(proto + '://' + location.host + '/ws');
  _ws.onopen = function() { setStatus('Connected', true); console.log('[GUI] WebSocket connected'); };
  _ws.onmessage = function(msg) {
    var evt = JSON.parse(msg.data);
    _clockTs = evt.ts || _clockTs;
    // throttle console logging to every 20th event
    if (!_ws._msgCount) _ws._msgCount = 0;
    _ws._msgCount++;
    if (_ws._msgCount % 20 === 1) console.log('[GUI] event #' + _ws._msgCount + ': ' + evt.type + ' ts=' + evt.ts);
    switch (evt.type) {
      case 'world_init': handleWorldInit(evt); break;
      case 'pos_snapshot': handlePosSnapshot(evt); break;
      case 'pos_update': handlePosUpdate(evt); break;
      case 'interaction': handleInteraction(evt); break;
      case 'drive_snapshot': handleDriveSnapshot(evt); break;
      case 'interaction_heatmap': handleHeatmap(evt); break;
    }
    updateClock();
  };
  _ws.onclose = function() { setStatus('Disconnected — retrying...', false); setTimeout(connect, 2000); };
  _ws.onerror = function() { setStatus('Connection error', false); };
}

function setStatus(text, ok) {
  var bar = document.getElementById('status-bar');
  var dot = bar.querySelector('.dot');
  bar.textContent = '';
  bar.appendChild(dot);
  bar.appendChild(document.createTextNode(' ' + text));
  dot.className = 'dot ' + (ok ? 'on' : 'off');
  bar.style.background = ok ? '#0a1a0a' : '#1a1000';
  bar.style.color = ok ? 'var(--green)' : 'var(--yellow)';
}

function updateClock() {
  var m = Math.floor(_clockTs / 60);
  var s = Math.floor(_clockTs % 60);
  document.getElementById('clock').textContent =
    (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
}

// ── Event Handlers ──

function handleWorldInit(evt) {
  zones = evt.zones || [];
  entities = {};
  entityList = [];
  (evt.entities || []).forEach(function(e) {
    entities[e.id] = {
      name: e.name, zone: e.zone, type: e.type, sprite: e.sprite,
      displayX: e.pos[0], displayY: e.pos[1],
      targetX: e.pos[0], targetY: e.pos[1],
      color: agentColor(e.id)
    };
    entityList.push(e.id);
  });
  recalcLayout();
}

function handlePosSnapshot(evt) {
  (evt.entities || []).forEach(function(e) {
    var ent = entities[e.id];
    if (!ent) {
      // new entity appeared mid-simulation
      entities[e.id] = {
        name: e.id, zone: e.zone, type: 'agent',
        displayX: e.pos[0], displayY: e.pos[1],
        targetX: e.pos[0], targetY: e.pos[1],
        color: agentColor(e.id)
      };
      entityList.push(e.id);
    } else {
      if (e.zone) ent.zone = e.zone;
      ent.targetX = e.pos[0];
      ent.targetY = e.pos[1];
    }
  });
}

function handlePosUpdate(evt) {
  var ent = entities[evt.entity_id];
  if (!ent) return;
  if (evt.zone) ent.zone = evt.zone;
  ent.targetX = evt.pos[0];
  ent.targetY = evt.pos[1];
}

function handleInteraction(evt) {
  interactionArrows.push({
    fx: evt.agent_pos[0], fy: evt.agent_pos[1],
    tx: evt.target_pos[0], ty: evt.target_pos[1],
    agent_id: evt.agent_id || '', target_id: evt.target_id || '',
    alpha: 1.0, created: performance.now(),
    zone: evt.zone
  });
}

function handleDriveSnapshot(evt) {
  var ts = evt.ts;
  maxTime = Math.max(maxTime, ts);
  var snaps = evt.snapshots || {};
  Object.keys(snaps).forEach(function(aid) {
    if (!driveHistory[aid]) driveHistory[aid] = [];
    var pt = { ts: ts };
    var s = snaps[aid];
    for (var k in DRIVE_NAMES) { pt[k] = s[k] != null ? s[k] : 0; }
    driveHistory[aid].push(pt);
    // keep last 300 points
    if (driveHistory[aid].length > 300) driveHistory[aid].shift();
  });
  if (!selectedAgent && entityList.length > 0) {
    // auto-select first agent that has data
    for (var i = 0; i < entityList.length; i++) {
      if (driveHistory[entityList[i]] && driveHistory[entityList[i]].length > 0) {
        selectedAgent = entityList[i]; break;
      }
    }
  }
}

function handleHeatmap(evt) {
  interactionPairs = evt.pairs || [];
}

// ── Agent Color ──

function agentColor(id) {
  var hash = 5381;
  for (var i = 0; i < id.length; i++) hash = ((hash << 5) + hash) + id.charCodeAt(i);
  return 'hsl(' + AGENT_HUES[Math.abs(hash) % AGENT_HUES.length] + ', 70%, 60%)';
}

// ── Zone Layout ──

var _layout = null; // {zones: {id: {x, y, w, h}}, scale, totalW, totalH}

function recalcLayout() {
  if (zones.length === 0) return;
  var canvas = getMapCanvas();
  // ensure canvas backing store matches CSS size before computing layout
  resizeCanvas(canvas);
  var W = canvas.clientWidth, H = canvas.clientHeight;
  if (W < 10 || H < 10) return; // canvas not ready yet
  var pad = 16, gap = 10;
  var totalZW = 0;
  zones.forEach(function(z) { totalZW += z.width; });
  var scaleX = (W - pad * 2 - gap * (zones.length - 1)) / totalZW;
  // compute per-zone draw rects
  var layout = { zones: {}, scale: 1, totalW: 0, totalH: 0 };
  var curX = pad;
  zones.forEach(function(z) {
    var zw = z.width * scaleX;
    var zh = z.height * scaleX;
    // fit vertically: scale down if too tall
    var maxH = H - pad * 2;
    if (zh > maxH) { var s = maxH / zh; zw *= s; zh *= s; }
    layout.zones[z.id] = { x: curX, y: pad, w: zw, h: zh };
    curX += zw + gap;
    layout.totalW = Math.max(layout.totalW, curX - gap + pad);
    layout.totalH = Math.max(layout.totalH, zh + pad * 2);
  });
  layout.scale = scaleX;
  // center entire layout in canvas
  var offsetX = Math.max(0, (W - (layout.totalW - pad)) / 2);
  var offsetY = Math.max(0, (H - layout.totalH) / 2);
  Object.keys(layout.zones).forEach(function(zid) {
    layout.zones[zid].x += offsetX;
    layout.zones[zid].y += offsetY;
  });
  _layout = layout;
}

function zoneLayout(zid) {
  if (!_layout || !_layout.zones[zid]) return null;
  var lz = _layout.zones[zid];
  var zone = null;
  for (var i = 0; i < zones.length; i++) { if (zones[i].id === zid) { zone = zones[i]; break; } }
  if (!zone) return lz;
  return { x: lz.x, y: lz.y, w: lz.w, h: lz.h, zone: zone };
}

// world -> canvas coordinate conversion
function worldToCanvas(eid) {
  var ent = entities[eid];
  if (!ent) return null;
  var zid = ent.zone;
  var lz = zoneLayout(zid);
  if (!lz) return null;
  var z = lz.zone;
  var rx = ent.displayX / z.width;
  var ry = ent.displayY / z.height;
  return {
    x: lz.x + rx * lz.w,
    y: lz.y + ry * lz.h
  };
}

// ── Overlap Resolution ──

function computeOverlapOffsets() {
  _overlapData = { offsets: {}, stacks: [] };
  // gather canvas positions for all entities
  var positions = [];
  entityList.forEach(function(eid) {
    var pt = worldToCanvas(eid);
    if (pt) {
      positions.push({ eid: eid, x: pt.x, y: pt.y });
    }
  });
  if (positions.length < 2) return;

  // union-find for connected components (distance < 12px)
  var parent = {}, rank = {};
  positions.forEach(function(p) { parent[p.eid] = p.eid; rank[p.eid] = 0; });

  function find(eid) {
    while (parent[eid] !== eid) { parent[eid] = parent[parent[eid]]; eid = parent[eid]; }
    return eid;
  }
  function union(a, b) {
    a = find(a); b = find(b);
    if (a === b) return;
    if (rank[a] < rank[b]) { parent[a] = b; }
    else if (rank[a] > rank[b]) { parent[b] = a; }
    else { parent[b] = a; rank[a]++; }
  }

  var OVERLAP_THRESH = 12;
  for (var i = 0; i < positions.length; i++) {
    for (var j = i + 1; j < positions.length; j++) {
      var dx = positions[i].x - positions[j].x;
      var dy = positions[i].y - positions[j].y;
      if (dx * dx + dy * dy < OVERLAP_THRESH * OVERLAP_THRESH) {
        union(positions[i].eid, positions[j].eid);
      }
    }
  }

  // group by root
  var groups = {};
  positions.forEach(function(p) {
    var root = find(p.eid);
    if (!groups[root]) groups[root] = [];
    groups[root].push(p);
  });

  // compute offsets for each group
  Object.keys(groups).forEach(function(root) {
    var group = groups[root];
    if (group.length < 2) return; // no overlap

    // sort by eid for stable positions across frames
    group.sort(function(a, b) { return a.eid < b.eid ? -1 : a.eid > b.eid ? 1 : 0; });

    // centroid
    var cx = 0, cy = 0;
    group.forEach(function(p) { cx += p.x; cy += p.y; });
    cx /= group.length; cy /= group.length;

    if (group.length <= 6) {
      // circular spread
      var radius = 10 + group.length * 2;
      group.forEach(function(p, i) {
        var angle = (2 * Math.PI * i / group.length) - Math.PI / 2;
        _overlapData.offsets[p.eid] = {
          dx: Math.cos(angle) * radius,
          dy: Math.sin(angle) * radius
        };
      });
    } else {
      // stack marker
      _overlapData.stacks.push({
        x: cx, y: cy,
        members: group.map(function(p) { return p.eid; })
      });
    }
  });
}

function worldToCanvasWithOffset(eid) {
  var pt = worldToCanvas(eid);
  if (!pt) return null;
  if (_overlapData && _overlapData.offsets[eid]) {
    var off = _overlapData.offsets[eid];
    pt.x += off.dx;
    pt.y += off.dy;
  }
  return pt;
}

function drawStackMarker(ctx, x, y, count) {
  // outer ring
  ctx.strokeStyle = 'rgba(255,255,255,0.5)';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 2]);
  ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.stroke();
  ctx.setLineDash([]);
  // filled center
  ctx.fillStyle = 'rgba(22,27,34,0.9)';
  ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.3)';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.stroke();
  // count badge
  var bx = x + 8, by = y + 8, br = 8;
  ctx.fillStyle = '#58a6ff';
  ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 9px "Segoe UI", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(count, bx, by + 3);
  ctx.textAlign = 'start';
}

// ── Canvas Helpers ──

function getMapCanvas() { return document.getElementById('main-canvas'); }
function getStatsCanvas() { return document.getElementById('stats-canvas'); }

function resizeCanvas(canvas) {
  var dpr = window.devicePixelRatio || 1;
  var rect = canvas.getBoundingClientRect();
  var w = rect.width * dpr, h = rect.height * dpr;
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
    return true;
  }
  return false;
}

// ── Map Rendering ──

function drawMap(ctx, now) {
  var W = ctx.canvas.clientWidth, H = ctx.canvas.clientHeight;
  ctx.clearRect(0, 0, W, H);

  // zone backgrounds
  var zoneHues = [220, 160, 40, 280, 120, 10, 200, 340];
  zones.forEach(function(z, i) {
    var lz = zoneLayout(z.id);
    if (!lz) return;
    var hue = zoneHues[i % zoneHues.length];
    ctx.fillStyle = 'hsla(' + hue + ', 30%, 25%, 0.15)';
    ctx.strokeStyle = 'hsla(' + hue + ', 40%, 55%, 0.35)';
    ctx.lineWidth = 1;
    roundRect(ctx, lz.x, lz.y, lz.w, lz.h, 8);
    ctx.fill(); ctx.stroke();
    // zone name
    ctx.fillStyle = 'hsla(' + hue + ', 30%, 70%, 0.5)';
    ctx.font = 'bold 12px "Segoe UI", sans-serif';
    ctx.fillText(z.name, lz.x + 10, lz.y + 18);
    // zone dimensions
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    ctx.font = '9px "Segoe UI", sans-serif';
    ctx.fillText(z.width + 'x' + z.height, lz.x + lz.w - 40, lz.y + lz.h - 6);
  });

  // interaction arrows (draw before entities so they're behind)
  interactionArrows.forEach(function(arr) {
    if (arr.zone) {
      var lz = zoneLayout(arr.zone);
      if (lz) { arr.fx_ = lz.x + (arr.fx / lz.zone.width) * lz.w; arr.fy_ = lz.y + (arr.fy / lz.zone.height) * lz.h; arr.tx_ = lz.x + (arr.tx / lz.zone.width) * lz.w; arr.ty_ = lz.y + (arr.ty / lz.zone.height) * lz.h; }
    }
    // apply overlap offsets so arrows follow displayed entity positions
    if (_overlapData) {
      if (arr.agent_id && _overlapData.offsets[arr.agent_id]) {
        arr.fx_ = (arr.fx_ || arr.fx) + _overlapData.offsets[arr.agent_id].dx;
        arr.fy_ = (arr.fy_ || arr.fy) + _overlapData.offsets[arr.agent_id].dy;
      }
      if (arr.target_id && _overlapData.offsets[arr.target_id]) {
        arr.tx_ = (arr.tx_ || arr.tx) + _overlapData.offsets[arr.target_id].dx;
        arr.ty_ = (arr.ty_ || arr.ty) + _overlapData.offsets[arr.target_id].dy;
      }
      for (var si = 0; si < _overlapData.stacks.length; si++) {
        var st = _overlapData.stacks[si];
        if (st.members.indexOf(arr.target_id) >= 0) {
          arr.tx_ = st.x; arr.ty_ = st.y;
        }
        if (st.members.indexOf(arr.agent_id) >= 0) {
          arr.fx_ = st.x; arr.fy_ = st.y;
        }
      }
    }
  });
  interactionArrows.forEach(function(arr) {
    var fx = arr.fx_ || arr.fx, fy = arr.fy_ || arr.fy;
    var tx = arr.tx_ || arr.tx, ty = arr.ty_ || arr.ty;
    // trim both ends so arrowhead isn't hidden behind entity circles
    var dx = tx - fx, dy = ty - fy;
    var dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 4) return;
    var ndx = dx / dist, ndy = dy / dist;
    var trim = 8; // entity radius + margin
    var sx = fx + ndx * trim;
    var sy = fy + ndy * trim;
    var ex = tx - ndx * trim;
    var ey = ty - ndy * trim;
    ctx.strokeStyle = 'rgba(255,220,100,' + arr.alpha.toFixed(2) + ')';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
    // arrowhead at trimmed endpoint
    var ang = Math.atan2(ty - fy, tx - fx);
    var hsz = 5;
    ctx.fillStyle = 'rgba(255,220,100,' + arr.alpha.toFixed(2) + ')';
    ctx.beginPath();
    ctx.moveTo(ex, ey);
    ctx.lineTo(ex - hsz * Math.cos(ang - 0.5), ey - hsz * Math.sin(ang - 0.5));
    ctx.lineTo(ex - hsz * Math.cos(ang + 0.5), ey - hsz * Math.sin(ang + 0.5));
    ctx.closePath(); ctx.fill();
  });

  // entities
  computeOverlapOffsets();
  entityList.forEach(function(eid) {
    var ent = entities[eid];
    if (!ent) return;
    // skip entities that are part of a stack (7+ overlap)
    if (_overlapData && _overlapData.stacks.some(function(s) { return s.members.indexOf(eid) >= 0; })) return;
    var pt = worldToCanvasWithOffset(eid);
    if (!pt) return;
    // draw gate as diamond
    if (ent.sprite && ent.sprite.toLowerCase().indexOf('gate') >= 0) {
      var gsz = 7;
      ctx.fillStyle = ent.color;
      ctx.beginPath();
      ctx.moveTo(pt.x, pt.y - gsz);
      ctx.lineTo(pt.x + gsz, pt.y);
      ctx.lineTo(pt.x, pt.y + gsz);
      ctx.lineTo(pt.x - gsz, pt.y);
      ctx.closePath(); ctx.fill();
    } else if (ent.type === 'agent') {
      var r = 6;
      ctx.fillStyle = ent.color;
      ctx.beginPath(); ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.5)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2); ctx.stroke();
    } else {
      var s = 5;
      ctx.fillStyle = '#8b949e';
      ctx.fillRect(pt.x - s/2, pt.y - s/2, s, s);
      ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.lineWidth = 0.5;
      ctx.strokeRect(pt.x - s/2, pt.y - s/2, s, s);
    }
    // name label
    ctx.fillStyle = ent.type === 'agent' ? '#e6edf3' : 'rgba(230,237,243,0.5)';
    ctx.font = (ent.type === 'agent' ? 'bold ' : '') + '10px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(ent.name, pt.x, pt.y + (ent.type === 'agent' ? 15 : 12));
    ctx.textAlign = 'start';
  });

  // stack markers (7+ agents at same position)
  if (_overlapData && _overlapData.stacks.length > 0) {
    _overlapData.stacks.forEach(function(s) {
      drawStackMarker(ctx, s.x, s.y, s.members.length);
    });
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

// ── Stats Rendering ──

function drawStats(ctx, now) {
  var W = ctx.canvas.clientWidth, H = ctx.canvas.clientHeight;
  ctx.clearRect(0, 0, W, H);

  // agent selector buttons (wrap to next row on overflow)
  var agents = entityList.filter(function(eid) { return entities[eid] && entities[eid].type === 'agent'; });
  if (!selectedAgent && agents.length > 0) selectedAgent = agents[0];

  ctx._btns = [];
  var btnY = 10, btnH = 24, btnGap = 4;
  var maxRowW = W - 20;
  var curX = 10, curRowY = btnY;
  ctx.font = '11px "Segoe UI", sans-serif';
  agents.forEach(function(aid, i) {
    var name = entities[aid] ? entities[aid].name : aid;
    var tw = ctx.measureText(name).width + 14;
    if (curX + tw > maxRowW) { curX = 10; curRowY += btnH + btnGap; }
    ctx.fillStyle = selectedAgent === aid ? 'rgba(88,166,255,0.25)' : 'rgba(22,27,34,0.8)';
    ctx.strokeStyle = selectedAgent === aid ? '#58a6ff' : '#30363d';
    ctx.lineWidth = 1;
    roundRect(ctx, curX, curRowY, tw, btnH, 4);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = selectedAgent === aid ? '#58a6ff' : '#8b949e';
    ctx.fillText(name, curX + 7, curRowY + 16);
    ctx._btns.push({ x: curX, y: curRowY, w: tw, h: btnH, aid: aid });
    curX += tw + 6;
  });

  var chartY = curRowY + btnH + 12;
  var remainingH = H - chartY - 8;
  var chartH = remainingH * 0.55;

  drawDriveChart(ctx, 40, chartY, W - 60, chartH);
  var hmY = chartY + chartH + 20;
  var hmH = H - hmY - 10;
  drawHeatmap(ctx, agents, 10, hmY, W - 20, hmH);
}

function drawDriveChart(ctx, x, y, w, h) {
  // title
  var title = selectedAgent ? (entities[selectedAgent] ? entities[selectedAgent].name : selectedAgent) + ' Status' : '';
  ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px "Segoe UI", sans-serif';
  ctx.fillText(title, x, y);
  var titleH = 18;

  if (!selectedAgent) return;
  var hist = driveHistory[selectedAgent];
  if (!hist || hist.length < 1) {
    ctx.fillStyle = '#8b949e'; ctx.font = '12px "Segoe UI", sans-serif';
    ctx.fillText('Waiting for drive data...', x + w/2 - 70, y + titleH + h/2);
    return;
  }
  // axes
  var padL = 32, padR = 10, padT = 4, padB = 20;
  var chartY = y + titleH;
  var pw = w - padL - padR, ph = h - titleH - padT - padB;
  if (ph < 20) return;
  ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(x + padL, chartY + padT); ctx.lineTo(x + padL, chartY + padT + ph); ctx.lineTo(x + padL + pw, chartY + padT + ph); ctx.stroke();
  // Y ticks
  for (var v = 0; v <= 100; v += 20) {
    var py = chartY + padT + ph - (v / 100) * ph;
    ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.font = '9px "Segoe UI", sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(v, x + padL - 5, py + 3);
    ctx.textAlign = 'start';
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.beginPath(); ctx.moveTo(x + padL, py); ctx.lineTo(x + padL + pw, py); ctx.stroke();
  }
  // X ticks
  var maxT = Math.max(maxTime, 10);
  ctx.textAlign = 'center';
  for (var t = 0; t <= maxT; t += Math.max(1, Math.floor(maxT / 8))) {
    var px = x + padL + (t / maxT) * pw;
    ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.fillText(t + 's', px, chartY + padT + ph + 14);
  }
  ctx.textAlign = 'start';
  // lines
  Object.keys(DRIVE_COLORS).forEach(function(drive) {
    ctx.strokeStyle = DRIVE_COLORS[drive];
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    var first = true;
    hist.forEach(function(pt) {
      var px = x + padL + (pt.ts / maxT) * pw;
      var py = chartY + padT + ph - (pt[drive] / 100) * ph;
      if (first) { ctx.moveTo(px, py); first = false; }
      else { ctx.lineTo(px, py); }
    });
    ctx.stroke();
  });
  // legend
  var legX = x + padL + pw - 160, legY = chartY + padT;
  Object.keys(DRIVE_COLORS).forEach(function(drive, i) {
    var lx = legX + (i % 3) * 55;
    var ly = legY + Math.floor(i / 3) * 16;
    ctx.fillStyle = DRIVE_COLORS[drive];
    ctx.fillRect(lx, ly, 10, 3);
    ctx.fillStyle = '#e6edf3'; ctx.font = '9px "Segoe UI", sans-serif';
    ctx.fillText(drive, lx + 14, ly + 4);
  });
}

function drawHeatmap(ctx, agents, x, y, w, h) {
  if (agents.length === 0) return;

  // title
  var titleH = 16;
  ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px "Segoe UI", sans-serif';
  ctx.fillText('Interaction Heatmap', x, y + 11);

  // build lookup
  var pairMap = {};
  interactionPairs.forEach(function(p) { pairMap[p.agent + '|' + p.target] = p.count; });
  var maxCount = 1;
  interactionPairs.forEach(function(p) { maxCount = Math.max(maxCount, p.count); });

  // measure longest agent name for label column width
  ctx.font = '9px "Segoe UI", sans-serif';
  var labelW = 0;
  agents.forEach(function(aid) {
    var name = entities[aid] ? entities[aid].name : aid;
    labelW = Math.max(labelW, ctx.measureText(name).width);
  });
  labelW = Math.min(labelW + 10, 120);

  var colLabelH = 28; // room for rotated column headers
  var labelAreaH = titleH + colLabelH;
  var availableW = w - labelW - 10;
  var availableH = h - labelAreaH - 4;
  var cellSz = Math.min(28, Math.floor(Math.min(availableW / agents.length, availableH / agents.length)));
  if (cellSz < 8) cellSz = 8;
  var ox = x + labelW + 6;
  var oy = y + labelAreaH;

  // column labels (rotated, anchored below title area)
  ctx.fillStyle = '#8b949e'; ctx.font = '9px "Segoe UI", sans-serif';
  agents.forEach(function(aid, i) {
    var name = entities[aid] ? entities[aid].name : aid;
    var cx = ox + i * cellSz + cellSz / 2;
    ctx.save();
    ctx.translate(cx, y + labelAreaH - 4);
    ctx.rotate(-Math.PI / 6);
    ctx.textAlign = 'right';
    ctx.fillText(name, 0, 0);
    ctx.restore();
  });

  // row labels
  ctx.textAlign = 'right';
  agents.forEach(function(aid, i) {
    var name = entities[aid] ? entities[aid].name : aid;
    ctx.fillText(name, ox - 6, oy + i * cellSz + cellSz / 2 + 3);
  });
  ctx.textAlign = 'start';

  // cells
  agents.forEach(function(ra, ri) {
    agents.forEach(function(ca, ci) {
      var count = pairMap[ra + '|' + ca] || 0;
      var intensity = maxCount > 0 ? count / maxCount : 0;
      var cx = ox + ci * cellSz;
      var cy = oy + ri * cellSz;
      var r, g, b;
      if (intensity < 0.01) {
        r = 30; g = 30; b = 35;
      } else {
        r = Math.round(30 + 225 * intensity);
        g = Math.round(30 + 180 * (1 - intensity));
        b = Math.round(35);
      }
      ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
      ctx.fillRect(cx + 1, cy + 1, cellSz - 2, cellSz - 2);
      if (count > 0) {
        ctx.fillStyle = intensity > 0.5 ? '#fff' : '#8b949e';
        ctx.font = '9px "Segoe UI", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(count, cx + cellSz / 2, cy + cellSz / 2 + 3);
        ctx.textAlign = 'start';
      }
    });
  });
}

// ── Animation Loop ──

function animate(timestamp) {
  requestAnimationFrame(animate);
  try {
    // lerp entity positions
    entityList.forEach(function(eid) {
      var ent = entities[eid];
      if (!ent) return;
      ent.displayX += (ent.targetX - ent.displayX) * 0.15;
      ent.displayY += (ent.targetY - ent.displayY) * 0.15;
    });

    // decay interaction arrows
    interactionArrows = interactionArrows.filter(function(a) {
      a.alpha = Math.max(0, 1.0 - (timestamp - a.created) / 2000);
      return a.alpha > 0.01;
    });

    if (currentView === 'map') {
      var canvas = getMapCanvas();
      var resized = resizeCanvas(canvas);
      if (resized) recalcLayout();
      var ctx = canvas.getContext('2d');
      ctx._btns = null;
      drawMap(ctx, timestamp);
    } else {
      var scanvas = getStatsCanvas();
      resizeCanvas(scanvas);
      var sctx = scanvas.getContext('2d');
      sctx._btns = [];
      drawStats(sctx, timestamp);
    }
  } catch (e) {
    // prevent a render error from stopping the animation loop
  }
}

// ── View Switching ──

function switchView(view) {
  currentView = view;
  document.getElementById('btn-map').classList.toggle('active', view === 'map');
  document.getElementById('btn-stats').classList.toggle('active', view === 'status');
  document.getElementById('map-wrap').style.display = view === 'map' ? '' : 'none';
  document.getElementById('stats-wrap').style.display = view === 'status' ? '' : 'none';
}

// ── Mouse: tooltip on map ──

document.addEventListener('mousemove', function(e) {
  var tooltip = document.getElementById('tooltip');
  if (currentView === 'map') {
    var canvas = getMapCanvas();
    var rect = canvas.getBoundingClientRect();
    var mx = e.clientX - rect.left, my = e.clientY - rect.top;

    // check stack markers first (7+ agent groups)
    var stackHit = null;
    if (_overlapData && _overlapData.stacks.length > 0) {
      _overlapData.stacks.forEach(function(s) {
        var dx = mx - s.x, dy = my - s.y;
        if (dx * dx + dy * dy < 225) { // within 15px
          stackHit = s;
        }
      });
    }
    if (stackHit) {
      var names = stackHit.members.map(function(eid) { return entities[eid] ? entities[eid].name : eid; });
      var shown = names.slice(0, 8).join(', ');
      if (names.length > 8) shown += ' +' + (names.length - 8) + ' more';
      tooltip.querySelector('.tt-name').textContent = stackHit.members.length + ' agents';
      tooltip.querySelector('.tt-zone').textContent = shown;
      tooltip.querySelector('.tt-pos').textContent = '';
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY - 30) + 'px';
    } else {
      var found = null;
      entityList.forEach(function(eid) {
        var pt = worldToCanvasWithOffset(eid);
        if (!pt) return;
        var dx = mx - pt.x, dy = my - pt.y;
        if (dx * dx + dy * dy < 100) { // within 10px
          found = eid;
        }
      });
      if (found) {
        var ent = entities[found];
        tooltip.querySelector('.tt-name').textContent = ent.name;
        tooltip.querySelector('.tt-zone').textContent = ent.zone;
        tooltip.querySelector('.tt-pos').textContent = '(' + ent.targetX.toFixed(0) + ', ' + ent.targetY.toFixed(0) + ')';
        tooltip.style.display = 'block';
        tooltip.style.left = (e.clientX + 14) + 'px';
        tooltip.style.top = (e.clientY - 30) + 'px';
      } else {
        tooltip.style.display = 'none';
      }
    }
  } else {
    tooltip.style.display = 'none';
  }
});

// ── Mouse: click agent selector in stats view ──

document.addEventListener('click', function(e) {
  if (currentView !== 'status') return;
  var canvas = getStatsCanvas();
  var rect = canvas.getBoundingClientRect();
  var mx = e.clientX - rect.left, my = e.clientY - rect.top;
  var ctx = canvas.getContext('2d');
  var btns = ctx._btns || [];
  for (var i = 0; i < btns.length; i++) {
    var b = btns[i];
    if (mx >= b.x && mx <= b.x + b.w && my >= b.y && my <= b.y + b.h) {
      selectedAgent = b.aid; break;
    }
  }
});

// ── Window resize ──

window.addEventListener('resize', function() { recalcLayout(); });

// ── Start ──

connect();
requestAnimationFrame(animate);
