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
    this.updateInterval = null;
  }

  // Called when element is connected to the page
  connectedCallback() {
    console.log('🎨 Climate Control Panel - connectedCallback');
    this.render();

    // Start update interval for time
    this.updateInterval = setInterval(() => this.updateTime(), 1000);

    // Wait for hass object to be set
    setTimeout(() => {
      console.log('⏰ Timeout check - hass:', this.hass ? 'EXISTS' : 'NULL');
      this.init();
    }, 500);
  }

  disconnectedCallback() {
    console.log('🎨 Climate Control Panel - disconnectedCallback');
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }

  // Called when hass object is set by Home Assistant
  set panel(panel) {
    console.log('🔧 set panel() called with:', panel);
    this._panel = panel;
    this.hass = panel?.hass;
    console.log('✅ Panel hass object:', this.hass ? 'SET' : 'NULL');
    if (this.hass) {
      console.log('📋 Hass object keys:', Object.keys(this.hass).slice(0, 10));
      this.init();
    }
  }

  updateTime() {
    const timeElement = this.shadowRoot.querySelector('.live-time');
    if (timeElement) {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('it-IT', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      timeElement.textContent = timeStr;
    }
  }

  async init() {
    if (!this.hass) {
      console.warn('⚠️ init() called but hass is null');
      return;
    }

    console.log('🚀 Initializing panel with hass connection');
    console.log('🔍 Hass user:', this.hass.user);
    console.log('🔍 Hass states count:', Object.keys(this.hass.states || {}).length);

    try {
      // Try to load data
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
      // METHOD 1: Try config_entries API
      console.log('🔍 Attempting config_entries/get...');
      const entries = await this.hass.callWS({
        type: 'config_entries/get',
      });

      console.log('📦 All config entries received:', entries?.length || 0);

      // Filter for our integration
      const ourEntries = entries?.filter(e => e.domain === 'climate_control_calendar') || [];
      console.log('📦 Our integration entries:', ourEntries.length);

      if (ourEntries.length > 0) {
        const entry = ourEntries[0];
        console.log('✅ Found entry:', {
          entry_id: entry.entry_id,
          title: entry.title,
          hasData: !!entry.data,
          hasOptions: !!entry.options
        });

        // Extract data
        this.slots = entry.options?.slots || [];
        this.bindings = entry.options?.bindings || [];
        this.calendars = entry.data?.calendar_entities || [];

        console.log('✅ Data extracted:', {
          slots: this.slots.length,
          bindings: this.bindings.length,
          calendars: this.calendars.length
        });

        if (this.slots.length > 0) {
          console.log('📊 Sample slot:', this.slots[0]);
        }
        if (this.bindings.length > 0) {
          console.log('🔗 Sample binding:', this.bindings[0]);
        }

        this.render();
      } else {
        console.warn('⚠️ No config entries found for climate_control_calendar');

        // Try METHOD 2: Check states for any related entities
        console.log('🔍 Checking hass.states for climate_control_calendar entities...');
        const relatedStates = Object.keys(this.hass.states)
          .filter(key => key.includes('climate_control'))
          .map(key => ({ entity_id: key, state: this.hass.states[key] }));

        console.log('📊 Related states:', relatedStates.length, relatedStates);
      }

    } catch (error) {
      console.error('❌ Failed to load data:', error);
      console.error('❌ Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      throw error;
    }
  }

  subscribeToUpdates() {
    if (!this.hass?.connection) {
      console.warn('⚠️ No connection available for subscriptions');
      return;
    }

    try {
      // Subscribe to config entry updates
      this.hass.connection.subscribeEvents((event) => {
        console.log('🔄 Config entry changed event:', event);
        this.loadIntegrationData();
      }, 'config_entry_changed');

      console.log('✅ Subscribed to config_entry_changed events');
    } catch (error) {
      console.error('❌ Failed to subscribe:', error);
    }
  }

  render() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

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

        .debug-info {
          background: rgba(0, 0, 0, 0.5);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 15px;
          border-radius: 8px;
          margin-top: 20px;
          font-family: monospace;
          font-size: 0.9em;
          color: #aaa;
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
        <p class="subtitle">Web Interface - ${this.hass ? 'Connected ✅' : 'Waiting for connection...'}</p>

        <div class="status-bar">
          <div class="status-badge">
            <div class="status-dot"></div>
            <span class="live-time">${timeStr}</span>
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
        ${this.renderDebugInfo()}
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

  renderDebugInfo() {
    return `
      <div class="card">
        <h2>🐛 Debug Info</h2>
        <div class="debug-info">
          Hass object: ${this.hass ? '✅ Connected' : '❌ Not connected'}<br>
          Console: Open browser console (F12) for detailed logs<br>
          Data loaded: slots=${this.slots.length}, bindings=${this.bindings.length}, calendars=${this.calendars.length}
        </div>
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
          <p style="margin-top: 20px; color: #888;">Check browser console (F12) for details</p>
        </div>
      </div>
    `;
  }
}

// Define the custom element
customElements.define('climate-panel-card', ClimatePanelCard);

console.log('🚀 Climate Control Panel - Custom element registered');
