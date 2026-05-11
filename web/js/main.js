// ═══════════════════════════════════════
// AgentWorld Pixel Frontend — Main
// ═══════════════════════════════════════

const API = 'http://' + location.host;
const WS  = 'ws://' + location.host + '/ws/live';

let phaserGame = null;
let wsClient = null;
let isRunning = false;

// ── Sprites: color + emoji labels ──
const SPRITE_PALETTE = {
    counter_bar:    { color: 0x8B4513, icon: '🍺' },
    table:          { color: 0x6B4226, icon: '🪑' },
    door:           { color: 0x654321, icon: '🚪' },
    char_male_01:   { color: 0x3498DB, icon: '🧑' },
    char_witcher:   { color: 0xC0C0C0, icon: '⚔️' },
    char_sorceress: { color: 0x9B59B6, icon: '🔮' },
    char_bard:      { color: 0xE74C3C, icon: '🎵' },
    default:        { color: 0x95A5A6, icon: '?' },
};

const ZONE_COLORS = {
    bar_zone: 0x3a2a1a,
    square:   0xf5e6c8,
    herb_hut: 0x2d5016,
};

// ═══════════════════════════════════════
// World Scene (Phaser)
// ═══════════════════════════════════════
class WorldScene extends Phaser.Scene {
    constructor() { super('WorldScene'); }

    create() {
        this.cameras.main.setBackgroundColor('#1a1a2e');
        this.entitySprites = {};
        this.tileSize  = 32;
        this.zoomLevel = 3;
        this.currentZone = null;
        this.tileGraphics = null;
        this.followTarget = null;

        // Load initial state
        fetch(API + '/api/v1/world/state')
            .then(r => r.json())
            .then(data => this.loadWorld(data));

        // Start WebSocket
        this.connectWS();
    }

    loadWorld(data) {
        console.log('[WorldScene] Loaded', data.entities.length, 'entities');
        this.worldTime = data.time;
        this.zones = data.zones;
        this.entities = {};
        data.entities.forEach(e => this.entities[e.id] = e);

        // Show first zone by default
        const firstZone = data.zones.find(z => {
            const agents = data.entities.filter(e => e.pos &&
                e.zone === z.id && (e.autonomous || e.sprite));
            return agents.length > 0;
        });
        this.loadZone(firstZone || data.zones[0]);

        updateHUD(data);
        updateAgentList(data.entities);
    }

    loadZone(zoneData) {
        if (!zoneData) return;
        this.currentZone = zoneData;
        console.log('[WorldScene] Zone:', zoneData.name);

        // Clear old sprites
        Object.values(this.entitySprites).forEach(s => s.destroy());
        this.entitySprites = {};
        if (this.tileGraphics) this.tileGraphics.destroy();

        const ts = this.tileSize;
        const w = zoneData.width  * ts;
        const h = zoneData.height * ts;

        // Draw ground tiles
        this.tileGraphics = this.add.graphics();
        const bgColor = ZONE_COLORS[zoneData.id] || 0x333333;
        this.tileGraphics.fillStyle(bgColor, 1);
        this.tileGraphics.fillRect(0, 0, w, h);

        // Grid lines (pixel style)
        this.tileGraphics.lineStyle(1, Phaser.Display.Color.ValueToColor(bgColor).darken(20).color, 0.3);
        for (let x = 0; x <= zoneData.width; x++) {
            this.tileGraphics.lineBetween(x * ts, 0, x * ts, h);
        }
        for (let y = 0; y <= zoneData.height; y++) {
            this.tileGraphics.lineBetween(0, y * ts, w, y * ts);
        }

        // Draw entities in this zone
        const zoneEntities = Object.values(this.entities).filter(
            e => e.zone === zoneData.id
        );
        zoneEntities.forEach(e => this.spawnSprite(e));

        // Camera setup
        this.cameras.main.setBounds(0, 0, w, h);
        const agentSprites = Object.entries(this.entitySprites)
            .filter(([id]) => this.entities[id]?.autonomous);
        if (agentSprites.length > 0) {
            this.cameras.main.startFollow(agentSprites[0][1], true, 0.3, 0.3);
            this.followTarget = agentSprites[0][1];
        }

        this.cameras.main.setZoom(this.zoomLevel);
    }

    spawnSprite(entity) {
        if (!entity.pos) return;
        const ts = this.tileSize;
        const palette = SPRITE_PALETTE[entity.sprite] || SPRITE_PALETTE['default'];
        const x = entity.pos[0] * ts + ts / 2;
        const y = entity.pos[1] * ts + ts / 2;

        // Colored square
        const gfx = this.add.graphics();
        gfx.fillStyle(palette.color, 1);
        gfx.fillRect(x - ts/3, y - ts/3, ts*2/3, ts*2/3);

        // Emoji label
        const isAutonomous = entity.autonomous || entity.sprite === 'char_witcher'
            || entity.sprite === 'char_sorceress' || entity.sprite === 'char_bard'
            || entity.sprite === 'char_male_01';
        const label = this.add.text(x, y - ts/2 - 2, palette.icon, {
            fontSize: '0px',
            fontFamily: 'serif',
        }).setOrigin(0.5).setScale(0.5);

        if (isAutonomous) {
            // Name tag
            this.add.text(x, y - ts/2 + 8, entity.name || '?', {
                fontSize: '4px',
                fontFamily: '"Press Start 2P", monospace',
                color: '#f0a500',
            }).setOrigin(0.5).setScale(0.6);
        }

        this.entitySprites[entity.id] = { gfx, label, x, y };
    }

    moveSprite(entityId, to, durationMs) {
        const s = this.entitySprites[entityId];
        if (!s || s.node) return;
        const ts = this.tileSize;
        const tx = to[0] * ts + ts / 2;
        const ty = to[1] * ts + ts / 2;

        this.tweens.add({
            targets: [s.gfx, s.label],
            x: tx - s.x + (s.gfx.x || s.x),
            y: ty - s.y + (s.gfx.y || s.y),
            duration: Math.min(durationMs || 500, 2000),
            ease: 'Linear',
            onUpdate: () => {
                s.gfx.x = s.gfx.x || s.x;
                s.gfx.y = s.gfx.y || s.y;
            }
        });
        s.x = tx; s.y = ty;
    }

    showBubble(entityId, text) {
        const s = this.entitySprites[entityId];
        if (!s) return;
        const bubble = this.add.text(
            s.x || s.gfx.x, (s.y || s.gfx.y) - 20, text.substring(0, 25),
            {
                fontSize: '5px',
                fontFamily: '"Press Start 2P", monospace',
                color: '#fff',
                backgroundColor: '#222',
                padding: { x: 3, y: 2 },
            }
        ).setOrigin(0.5).setScale(0.5);

        this.tweens.add({
            targets: bubble,
            alpha: 0,
            delay: 3000,
            duration: 500,
            onComplete: () => bubble.destroy()
        });
    }

    // ── WebSocket ──
    connectWS() {
        if (wsClient) wsClient.close();
        wsClient = new WebSocket(WS);

        wsClient.onopen = () => {
            console.log('[WS] Connected');
            addEvent({type: 'connected', msg: 'WebSocket 已连接'});
        };

        wsClient.onmessage = (msg) => {
            const e = JSON.parse(msg.data);
            this.handleEvent(e);
        };

        wsClient.onclose = () => {
            console.log('[WS] Disconnected');
            setTimeout(() => { if (isRunning) this.connectWS(); }, 3000);
        };
    }

    handleEvent(e) {
        switch (e.event) {
            case 'agent_move':
                this.moveSprite(e.agent, e.to, e.duration_ms || 500);
                addEvent({type: 'move', agent: e.agent, from: e.from, to: e.to});
                break;

            case 'interaction_start':
                this.showBubble(e.agent, e.bubble || e.action);
                addEvent({type: 'interact', agent: e.agent, target: e.target, action: e.action});
                break;

            case 'interaction_complete':
                addEvent({type: 'result', agent: e.agent, observation: e.observation});
                break;

            case 'zone_change':
                addEvent({type: 'zone', agent: e.agent, zone: e.zone?.name});
                if (e.zone) this.loadZone(e.zone);
                break;

            case 'world_time':
                updateHUD({time: e.time});
                break;
        }
    }

    update() {
        // Rotate follow target between agents
        if (this.followTarget && Phaser.Input.Keyboard.JustDown(
            this.input.keyboard?.addKey(Phaser.Input.Keyboard.KeyCodes.TAB)
        )) {
            const agents = Object.entries(this.entitySprites)
                .filter(([id]) => this.entities[id]?.autonomous);
            if (agents.length > 0) {
                const idx = agents.findIndex(([id]) =>
                    this.entitySprites[id] === this.followTarget);
                const next = agents[(idx + 1) % agents.length];
                this.followTarget = next[1];
                this.cameras.main.startFollow(this.followTarget, true, 0.3, 0.3);
            }
        }
    }
}

// ═══════════════════════════════════════
// UI Functions
// ═══════════════════════════════════════

function updateHUD(data) {
    if (data.time) document.getElementById('hud-time').textContent = '⏱ ' + data.time;
    if (data.zone) document.getElementById('hud-zone').textContent = '📍 ' + data.zone;
    if (data.entities) {
        document.getElementById('hud-entity-count').textContent =
            data.entities.length + ' entities';
    }
}

function updateAgentList(entities) {
    const agents = entities.filter(e => e.autonomous || e.public_attrs);
    const list = document.getElementById('agent-list');
    list.innerHTML = agents.map(a => `
        <div class="agent-row">
            <span class="agent-name">${a.name || a.id}</span>
            <span class="agent-zone">${a.zone || ''}</span>
            <span class="agent-stats">${a.status || ''}</span>
        </div>
    `).join('');
}

function addEvent(e) {
    const log = document.getElementById('event-log');
    const now = new Date().toLocaleTimeString();
    let cls = '', text = '';

    switch (e.type) {
        case 'connected':
            cls = 'event-interact'; text = '🔗 已连接'; break;
        case 'move':
            cls = 'event-move'; text = `${e.agent} 移动 (${e.from})→(${e.to})`; break;
        case 'interact':
            cls = 'event-interact'; text = `${e.agent} → ${e.target}: ${e.action}`; break;
        case 'result':
            cls = 'event-interact'; text = e.observation || e.msg; break;
        case 'zone':
            cls = 'event-move'; text = `${e.agent} 进入 ${e.zone}`; break;
        default:
            cls = ''; text = e.msg || JSON.stringify(e);
    }

    const div = document.createElement('div');
    div.className = 'event-item ' + cls;
    div.innerHTML = `<span class="evt-time">${now}</span> ${text}`;
    log.insertBefore(div, log.firstChild);

    if (log.children.length > 100) log.removeChild(log.lastChild);
}

function toggleSim() {
    const btn = document.getElementById('btn-start');
    if (isRunning) {
        isRunning = false;
        btn.textContent = '▶ START';
        btn.className = 'btn btn-start';
        if (wsClient) wsClient.close();
    } else {
        isRunning = true;
        btn.textContent = '⏸ PAUSE';
        btn.className = 'btn btn-pause';
        if (phaserGame?.scene?.scenes[0]) {
            phaserGame.scene.scenes[0].connectWS();
        }
    }
}

function stopSim() {
    isRunning = false;
    document.getElementById('btn-start').textContent = '▶ START';
    document.getElementById('btn-start').className = 'btn btn-start';
    if (wsClient) wsClient.close();
    addEvent({type: 'result', observation: '已停止观察'});
}

// ═══════════════════════════════════════
// Boot
// ═══════════════════════════════════════
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    parent: 'game-container',
    backgroundColor: '#1a1a2e',
    scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: [WorldScene],
    pixelArt: true,
    roundPixels: true,
};

phaserGame = new Phaser.Game(config);
isRunning = true;
addEvent({type: 'connected', msg: '猎魔人世界已就绪'});
