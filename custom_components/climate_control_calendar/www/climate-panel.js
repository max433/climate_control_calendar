/**
 * Climate Control Calendar Panel
 * Custom element with WebSocket connection to Home Assistant
 */

class ClimatePanelCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.hass = null;
    this.slots = [];
    this.bindings = [];
    this.calendars = [];
  }

  // Called when element is connected to the page
  connectedCallback() {
    console.log('🎨 Climate Control Panel - Initializing...');
    this.render();

    // Wait for hass object to be set
    setTimeout(() => this.init(), 100);
  }

  // Called when hass object is set
  set panel(panel) {
    this._panel = panel;
    this.hass = panel.hass;
    console.log('✅ Panel hass object received:', this.hass ? 'OK' : 'MISSING');
    this.init();
  }

  async init() {
    if (!this.hass) {
      console.warn('⚠️ Waiting for hass object...');
      return;
    }

    console.log('🚀 Initializing panel with hass connection');

    try {
      // Fetch integration config entries
      await this.loadIntegrationData();

      // Subscribe to state changes
      this.subscribeToUpdates();

    } catch (error) {
      console.error('❌ Failed to initialize:', error);
      this.showError(error.message);
    }
  }

  async loadIntegrationData() {
    console.log('📥 Loading Climate Control Calendar data...');

    try {
      // Get all config entries for our integration
      const entries = await this.hass.callWS({
        type: 'config_entries/get',
        domain: 'climate_control_calendar'
      });

      console.log('📦 Config entries received:', entries);

      if (entries && entries.length > 0) {
        const entry = entries[0];

        // Extract data from options
        this.slots = entry.options?.slots || [];
        this.bindings = entry.options?.bindings || [];
        this.calendars = entry.data?.calendar_entities || [];

        console.log('✅ Data loaded:', {
          slots: this.slots.length,
          bindings: this.bindings.length,
          calendars: this.calendars.length
        });

        this.render();
      } else {
        console.warn('⚠️ No config entries found');
      }

    } catch (error) {
      console.error('❌ Failed to load data:', error);
      throw error;
    }
  }

  subscribeToUpdates() {
    // Subscribe to config entry updates
    this.hass.connection.subscribeEvents((event) => {
      console.log('🔄 Config entry updated, reloading data...');
      this.loadIntegrationData();
    }, 'config_entry_changed');
  }

  render() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('it-IT');

    this.shadowRoot.innerHTML = `
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          color: #ffffff;
          min-height: 100vh;
          padding: 40px;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
        }

        h1 {
          font-size: 2.5em;
          margin-bottom: 10px;
          background: linear-gradient(45deg, #00d4ff, #00ff88);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .subtitle {
          color: #888;
          margin-bottom: 30px;
          font-size: 1.1em;
        }

        .status-bar {
          display: flex;
          gap: 20px;
          margin-bottom: 30px;
          flex-wrap: wrap;
        }

        .status-badge {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          padding: 15px 25px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #00ff88;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .card {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 16px;
          padding: 30px;
          margin: 20px 0;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .card h2 {
          margin-bottom: 20px;
          color: #00d4ff;
          font-size: 1.5em;
        }

        .list-item {
          background: rgba(0, 0, 0, 0.3);
          padding: 20px;
          border-radius: 12px;
          margin: 10px 0;
          border-left: 4px solid #00d4ff;
        }

        .list-item h3 {
          color: #fff;
          margin-bottom: 10px;
          font-size: 1.2em;
        }

        .list-item .meta {
          color: #888;
          font-size: 0.9em;
          margin-top: 10px;
        }

        .badge {
          display: inline-block;
          background: rgba(0, 212, 255, 0.2);
          color: #00d4ff;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 0.85em;
          margin-right: 8px;
          margin-top: 8px;
        }

        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #888;
        }

        .empty-state-icon {
          font-size: 4em;
          margin-bottom: 20px;
          opacity: 0.3;
        }

        .error {
          background: rgba(255, 68, 68, 0.2);
          border: 1px solid rgba(255, 68, 68, 0.5);
          color: #ff4444;
          padding: 20px;
          border-radius: 12px;
          margin: 20px 0;
        }

        code {
          background: rgba(0, 0, 0, 0.5);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          font-size: 0.9em;
        }
      </style>

      <div class="container">
        <h1>🌡️ Climate Control Calendar</h1>
        <p class="subtitle">Web Interface - Connected to Home Assistant</p>

        <div class="status-bar">
          <div class="status-badge">
            <div class="status-dot"></div>
            <span>Live: ${timeStr}</span>
          </div>
          <div class="status-badge">
            📊 ${this.slots.length} Slots
          </div>
          <div class="status-badge">
            🔗 ${this.bindings.length} Bindings
          </div>
          <div class="status-badge">
            📅 ${this.calendars.length} Calendars
          </div>
        </div>

        ${this.renderSlots()}
        ${this.renderBindings()}
        ${this.renderCalendars()}
      </div>
    `;
  }

  renderSlots() {
    if (this.slots.length === 0) {
      return `
        <div class="card">
          <h2>🎯 Climate Slots</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No slots configured yet</p>
            <p style="margin-top: 10px; color: #666;">Configure slots in Home Assistant settings</p>
          </div>
        </div>
      `;
    }

    const slotsList = this.slots.map(slot => {
      const payload = slot.default_climate_payload || {};
      const temp = payload.temperature || 'N/A';
      const mode = payload.hvac_mode || 'N/A';

      return `
        <div class="list-item">
          <h3>${slot.label || 'Unnamed Slot'}</h3>
          <div>
            <span class="badge">🌡️ ${temp}°C</span>
            <span class="badge">🔥 ${mode}</span>
            ${payload.preset_mode ? `<span class="badge">⚙️ ${payload.preset_mode}</span>` : ''}
            ${payload.humidity ? `<span class="badge">💧 ${payload.humidity}%</span>` : ''}
          </div>
          <div class="meta">ID: <code>${slot.id}</code></div>
        </div>
      `;
    }).join('');

    return `
      <div class="card">
        <h2>🎯 Climate Slots (${this.slots.length})</h2>
        ${slotsList}
      </div>
    `;
  }

  renderBindings() {
    if (this.bindings.length === 0) {
      return `
        <div class="card">
          <h2>🔗 Event Bindings</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No bindings configured yet</p>
          </div>
        </div>
      `;
    }

    const bindingsList = this.bindings.map(binding => {
      const matchType = binding.match?.type || 'unknown';
      const matchValue = binding.match?.value || '';
      const priority = binding.priority || 0;

      // Find slot label
      const slot = this.slots.find(s => s.id === binding.slot_id);
      const slotLabel = slot?.label || binding.slot_id;

      return `
        <div class="list-item">
          <h3>${matchValue || 'Unnamed Binding'}</h3>
          <div>
            <span class="badge">📋 ${matchType}</span>
            <span class="badge">🎯 → ${slotLabel}</span>
            <span class="badge">⚡ Priority: ${priority}</span>
          </div>
          <div class="meta">
            Calendars: ${Array.isArray(binding.calendars) ? binding.calendars.join(', ') : binding.calendars || 'all'}
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card">
        <h2>🔗 Event Bindings (${this.bindings.length})</h2>
        ${bindingsList}
      </div>
    `;
  }

  renderCalendars() {
    if (this.calendars.length === 0) {
      return `
        <div class="card">
          <h2>📅 Monitored Calendars</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No calendars configured</p>
          </div>
        </div>
      `;
    }

    const calendarsList = this.calendars.map(cal => `
      <div class="list-item">
        <h3>${cal}</h3>
        <div class="meta">Entity ID</div>
      </div>
    `).join('');

    return `
      <div class="card">
        <h2>📅 Monitored Calendars (${this.calendars.length})</h2>
        ${calendarsList}
      </div>
    `;
  }

  showError(message) {
    this.shadowRoot.innerHTML = `
      <style>
        .error-container {
          padding: 40px;
          font-family: Arial;
          background: #1a1a1a;
          color: white;
          min-height: 100vh;
        }
        .error {
          background: rgba(255, 68, 68, 0.2);
          border: 1px solid rgba(255, 68, 68, 0.5);
          color: #ff4444;
          padding: 30px;
          border-radius: 12px;
        }
      </style>
      <div class="error-container">
        <div class="error">
          <h1>⚠️ Error</h1>
          <p>${message}</p>
        </div>
      </div>
    `;
  }
}

// Define the custom element
customElements.define('climate-panel-card', ClimatePanelCard);

console.log('🚀 Climate Control Panel - Custom element registered');
