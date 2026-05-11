// ═══════════════════════════════════════
// AgentWorld Pixel Frontend — Clean
// ═══════════════════════════════════════

const TILE_SIZE = 32;
const ZOOM = 3;
let game = null;
let ws = null;
let entities = {};
let sprites = {};
let zoneData = null;
let eventIndex = 0;

const SPRITE_COLORS = {
    counter_bar:    0x8B4513,
    table:          0x6B4226,
    door:           0x654321,
    char_male_01:   0x3498DB,
    char_witcher:   0xC0C0C0,
    char_sorceress: 0x9B59B6,
    char_bard:      0xE74C3C,
};

const ZONE_COLORS = {
    bar_zone: 0x3a2a1a,
    square:   0xf5e6c8,
    herb_hut: 0x2d5016,
};

// ═══════════════════════════════════════
// Phaser Scene
// ═══════════════════════════════════════
class WorldScene extends Phaser.Scene {
    constructor() { super('WorldScene'); }

    create() {
        this.cameras.main.setBackgroundColor('#1a1a2e');
        this.tileGfx = this.add.graphics();
        this.entitySprites = {};
        this.zoneGfx = null;
        this.currentZoneId = null;

        // Keyboard: Tab to cycle camera focus
        this.input.keyboard.on('keydown-TAB', () => this.cycleFocus());

        // Load world data, then connect WS
        this.loadWorldState();
    }

    async loadWorldState() {
        try {
            const resp = await fetch('/api/v1/world/state');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            entities = {};
            data.entities.forEach(e => entities[e.id] = e);
            zoneData = data.zones;

            // Find a zone with agents
            const agents = data.entities.filter(e => e.autonomous);
            const focusZone = agents[0]?.zone || data.zones[0]?.id;
            this.renderZone(focusZone);

            // Update UI
            updateHUD(data.time, focusZone, data.entities.length);
            updateAgentList(data.entities);

            // Connect WebSocket
            this.connectWS();

            document.getElementById('status').textContent = '● 已连接';
        } catch (err) {
            console.error('World load failed:', err);
            document.getElementById('status').textContent = '✗ 加载失败';
            setTimeout(() => this.loadWorldState(), 2000);
        }
    }

    renderZone(zoneId) {
        this.currentZoneId = zoneId;
        const zone = zoneData.find(z => z.id === zoneId);
        if (!zone) return;

        // Clear old sprites
        Object.values(this.entitySprites).forEach(o => {
            if (o.gfx) o.gfx.destroy();
            if (o.label) o.label.destroy();
            if (o.nametag) o.nametag.destroy();
        });
        this.entitySprites = {};
        if (this.zoneGfx) this.zoneGfx.destroy();

        const w = zone.width * TILE_SIZE;
        const h = zone.height * TILE_SIZE;
        const bg = ZONE_COLORS[zoneId] || 0x333333;

        // Draw ground
        this.zoneGfx = this.add.graphics();
        this.zoneGfx.fillStyle(bg, 1);
        this.zoneGfx.fillRect(0, 0, w, h);

        // Grid
        this.zoneGfx.lineStyle(1, Phaser.Display.Color.ValueToColor(bg).darken(30).color, 0.2);
        for (let x = 0; x <= zone.width; x++)  this.zoneGfx.lineBetween(x*TILE_SIZE, 0, x*TILE_SIZE, h);
        for (let y = 0; y <= zone.height; y++) this.zoneGfx.lineBetween(0, y*TILE_SIZE, w, y*TILE_SIZE);

        // Spawn entities
        const zoneEnts = Object.values(entities).filter(e => e.zone === zoneId);
        let hasAutonomous = false;
        zoneEnts.forEach(e => {
            const o = this.spawnEntity(e);
            if (e.autonomous) hasAutonomous = true;
        });

        // Camera
        this.cameras.main.setBounds(0, 0, w, h);
        this.cameras.main.setZoom(ZOOM);
        this.cameras.main.centerOn(w/2, h/2);

        // Update HUD
        const el = document.getElementById('hud-zone');
        if (el) el.textContent = `📍 ${zone.name}`;
    }

    spawnEntity(e) {
        if (!e.pos) return null;
        const ts = TILE_SIZE;
        const x = e.pos[0] * ts + ts / 2;
        const y = e.pos[1] * ts + ts / 2;

        const color = SPRITE_COLORS[e.sprite] || 0x95A5A6;

        // Draw colored rectangle
        const gfx = this.add.graphics();
        gfx.fillStyle(color, 1);
        const size = ts * 0.55;
        gfx.fillRect(x - size/2, y - size/2, size, size);
        // Pixel border
        gfx.lineStyle(1, 0xffffff, 0.3);
        gfx.strokeRect(x - size/2, y - size/2, size, size);

        // Name tag (for autonomous)
        let nametag = null;
        if (e.autonomous) {
            nametag = this.add.text(x, y - ts/2 - 4, e.name || e.id, {
                fontSize: '5px', fontFamily: 'monospace',
                color: '#f0a500', stroke: '#000', strokeThickness: 1,
            }).setOrigin(0.5);
        }

        const obj = { gfx, nametag, x, y, id: e.id, autonomous: e.autonomous };
        this.entitySprites[e.id] = obj;
        return obj;
    }

    moveSprite(entityId, to, durationMs) {
        const obj = this.entitySprites[entityId];
        if (!obj || !obj.gfx) return;
        const ts = TILE_SIZE;
        const tx = to[0] * ts + ts / 2;
        const ty = to[1] * ts + ts / 2;
        const d = durationMs || 500;

        const targets = [obj.gfx];
        if (obj.nametag) targets.push(obj.nametag);

        this.tweens.add({
            targets,
            x: tx,
            y: ty,
            duration: Math.min(d, 2000),
            ease: 'Linear',
        });
        obj.x = tx; obj.y = ty;
    }

    showBubble(entityId, text) {
        const obj = this.entitySprites[entityId];
        if (!obj) return;
        const b = this.add.text(obj.x, obj.y - 22, text.substring(0, 30), {
            fontSize: '5px', fontFamily: 'monospace',
            color: '#fff', backgroundColor: '#222',
            padding: { x: 2, y: 1 },
        }).setOrigin(0.5).setDepth(10);

        this.tweens.add({
            targets: b, alpha: 0, delay: 3000, duration: 500,
            onComplete: () => b.destroy()
        });
    }

    cycleFocus() {
        const autonomous = Object.values(this.entitySprites).filter(o => o.autonomous);
        if (autonomous.length === 0) return;
        const idx = autonomous.findIndex(o => o.id === this._focusId);
        const next = autonomous[(idx + 1) % autonomous.length];
        this._focusId = next.id;
        this.cameras.main.pan(next.x, next.y, 500);
    }

    // ── WebSocket ──
    connectWS() {
        if (ws) { ws.close(); ws = null; }
        const url = `ws://${location.host}/ws/live`;
        console.log('[WS] connecting:', url);
        ws = new WebSocket(url);

        ws.onopen = () => {
            console.log('[WS] connected');
            document.getElementById('status').textContent = '● 已连接';
        };

        ws.onmessage = (msg) => {
            try {
                const e = JSON.parse(msg.data);
                this.handleEvent(e);
            } catch (err) {
                console.error('[WS] parse error:', err);
            }
        };

        ws.onclose = () => {
            console.log('[WS] disconnected');
            document.getElementById('status').textContent = '○ 断开';
            if (document.getElementById('btn-start').textContent === '⏸ PAUSE') {
                setTimeout(() => this.connectWS(), 3000);
            }
        };

        ws.onerror = (err) => {
            console.error('[WS] error:', err);
        };
    }

    handleEvent(e) {
        addEvent(e);
        switch (e.event) {
            case 'agent_move':
                this.moveSprite(e.agent, e.to, e.duration_ms || 500);
                break;
            case 'interaction_start':
                this.showBubble(e.agent, e.bubble || e.action);
                break;
            case 'interaction_complete':
            case 'world_time':
                if (e.time) updateHUD(e.time);
                break;
            case 'zone_change':
                if (e.zone?.id) this.renderZone(e.zone.id);
                break;
        }
    }
}

// ═══════════════════════════════════════
// UI
// ═══════════════════════════════════════

function updateHUD(time, zone, count) {
    if (time) document.getElementById('hud-time').textContent = '⏱ ' + time;
    if (zone) document.getElementById('hud-zone').textContent = '📍 ' + zone;
    if (count)  document.getElementById('hud-count').textContent = count + ' entities';
}

function updateAgentList(ents) {
    const list = document.getElementById('agent-list');
    const agents = Object.values(entities).filter(e => e.autonomous);
    list.innerHTML = agents.map(a => `<div class="agent-row">
        <span class="agent-name">${a.name||a.id}</span>
        <span class="agent-zone">${a.zone||''}</span>
    </div>`).join('');
}

function addEvent(e) {
    const log = document.getElementById('event-log');
    if (!log) return;
    const now = new Date().toLocaleTimeString();
    let cls = 'event-interact', text = '';
    switch (e.event) {
        case 'agent_move': cls='event-move'; text=`${e.agent_name||e.agent} 移动 (${e.from})→(${e.to})`; break;
        case 'interaction_start': cls='event-interact'; text=`${e.agent_name||e.agent} → ${e.target_name||e.target}: ${e.action}`; break;
        case 'interaction_complete': cls='event-interact'; text=e.observation||''; break;
        case 'zone_change': cls='event-move'; text=`${e.agent_name||e.agent} → ${e.zone?.name||''}`; break;
        case 'world_time': return; // skip
        default: return;
    }
    if (!text) return;
    const div = document.createElement('div');
    div.className = 'event-item ' + cls;
    div.innerHTML = `<span class="evt-time">${now}</span> ${text}`;
    log.insertBefore(div, log.firstChild);
    while (log.children.length > 50) log.removeChild(log.lastChild);
}

function toggleWS() {
    const btn = document.getElementById('btn-start');
    if (btn.textContent === '▶ CONNECT') {
        btn.textContent = '⏸ PAUSE';
        btn.className = 'btn btn-pause';
        if (game?.scene?.scenes[0]) game.scene.scenes[0].connectWS();
    } else {
        btn.textContent = '▶ CONNECT';
        btn.className = 'btn btn-start';
        if (ws) { ws.close(); ws = null; }
    }
}

function stopWS() {
    document.getElementById('btn-start').textContent = '▶ CONNECT';
    document.getElementById('btn-start').className = 'btn btn-start';
    if (ws) { ws.close(); ws = null; }
    document.getElementById('status').textContent = '○ 断开';
}

// ═══════════════════════════════════════
// Boot
// ═══════════════════════════════════════
const config = {
    type: Phaser.AUTO,
    width: 800, height: 600,
    parent: 'game-container',
    backgroundColor: '#1a1a2e',
    scale: { mode: Phaser.Scale.RESIZE, autoCenter: Phaser.Scale.CENTER_BOTH },
    scene: [WorldScene],
    pixelArt: true,
    roundPixels: true,
};

game = new Phaser.Game(config);
