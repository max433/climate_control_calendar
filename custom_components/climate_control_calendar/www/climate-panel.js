/**
 * Climate Control Calendar Panel
 * Custom element with WebSocket connection to Home Assistant
 * WITH VISUAL DEBUG CONSOLE FOR MOBILE
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
    this.logs = []; // Visual debug logs
    this.maxLogs = 50; // Keep last 50 logs
  }

  // Custom log function that shows in UI
  log(emoji, message, data = null) {
    const timestamp = new Date().toLocaleTimeString('it-IT');
    const logEntry = {
      time: timestamp,
      emoji,
      message,
      data: data ? JSON.stringify(data, null, 2) : null
    };

    this.logs.push(logEntry);

    // Keep only last N logs
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Also log to browser console
    if (data) {
      console.log(`${emoji} ${message}`, data);
    } else {
      console.log(`${emoji} ${message}`);
    }

    // Update debug section
    this.updateDebugLogs();
  }

  updateDebugLogs() {
    const logsContainer = this.shadowRoot.querySelector('.debug-logs');
    if (logsContainer) {
      logsContainer.innerHTML = this.logs.map(log => `
        <div class="log-entry">
          <span class="log-time">${log.time}</span>
          <span class="log-message">${log.emoji} ${log.message}</span>
          ${log.data ? `<pre class="log-data">${log.data}</pre>` : ''}
        </div>
      `).join('');

      // Auto-scroll to bottom
      logsContainer.scrollTop = logsContainer.scrollHeight;
    }
  }

  // Called when element is connected to the page
  connectedCallback() {
    this.log('🎨', 'Panel connected to page');
    this.render();

    // Start update interval for time
    this.updateInterval = setInterval(() => this.updateTime(), 1000);

    // Wait for hass object to be set
    setTimeout(() => {
      this.log('⏰', 'Timeout check', { hassExists: !!this.hass });
      this.init();
    }, 500);
  }

  disconnectedCallback() {
    this.log('🎨', 'Panel disconnected');
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }

  // Called when hass object is set by Home Assistant
  set panel(panel) {
    this.log('🔧', 'set panel() called');
    this._panel = panel;
    this.hass = panel?.hass;

    if (this.hass) {
      this.log('✅', 'Hass object received', {
        user: this.hass.user?.name,
        statesCount: Object.keys(this.hass.states || {}).length
      });
      this.init();
    } else {
      this.log('❌', 'Hass object is NULL');
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
      this.log('⚠️', 'init() called but hass is null');
      return;
    }

    this.log('🚀', 'Initializing panel with hass connection');

    try {
      // Try to load data
      await this.loadIntegrationData();

      // Subscribe to state changes
      this.subscribeToUpdates();

    } catch (error) {
      this.log('❌', 'Failed to initialize', {
        error: error.message,
        stack: error.stack
      });
      this.showError(error.message);
    }
  }

  async loadIntegrationData() {
    this.log('📥', 'Loading Climate Control Calendar data...');

    try {
      // Call our custom service to get configuration
      this.log('🔍', 'Calling climate_control_calendar.get_config service...');

      // Use WebSocket call_service with return_response
      const response = await this.hass.callWS({
        type: 'call_service',
        domain: 'climate_control_calendar',
        service: 'get_config',
        service_data: {},
        return_response: true
      });

      this.log('📦', 'Service response received', {
        hasResponse: !!response,
        responseType: typeof response,
        responseKeys: response ? Object.keys(response) : []
      });

      // The response is nested in 'response' field
      const data = response?.response || response;

      // Extract data from service response
      this.slots = data?.slots || [];
      this.bindings = data?.bindings || [];
      this.calendars = data?.calendars || [];

      this.log('✅', 'Data extracted successfully', {
        slots: this.slots.length,
        bindings: this.bindings.length,
        calendars: this.calendars.length
      });

      if (this.slots.length > 0) {
        this.log('📊', 'Sample slot', this.slots[0]);
      }
      if (this.bindings.length > 0) {
        this.log('🔗', 'Sample binding', this.bindings[0]);
      }
      if (this.calendars.length > 0) {
        this.log('📅', 'Sample calendar', this.calendars[0]);
      }

      this.render()

    } catch (error) {
      this.log('❌', 'Failed to load data', {
        name: error.name,
        message: error.message,
        stack: error.stack?.split('\n').slice(0, 3).join('\n')
      });
      throw error;
    }
  }

  subscribeToUpdates() {
    if (!this.hass?.connection) {
      this.log('⚠️', 'No connection available for subscriptions');
      return;
    }

    try {
      // Subscribe to config entry updates
      this.hass.connection.subscribeEvents((event) => {
        this.log('🔄', 'Config entry changed event', event);
        this.loadIntegrationData();
      }, 'config_entry_changed');

      this.log('✅', 'Subscribed to config_entry_changed events');
    } catch (error) {
      this.log('❌', 'Failed to subscribe', error);
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
          padding: 20px;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
        }

        h1 {
          font-size: 2em;
          margin-bottom: 10px;
          background: linear-gradient(45deg, #00d4ff, #00ff88);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .subtitle {
          color: #888;
          margin-bottom: 20px;
          font-size: 1em;
        }

        .status-bar {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }

        .status-badge {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          padding: 10px 15px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          font-size: 0.9em;
        }

        .status-dot {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #00ff88;
          animation: pulse 2s infinite;
          margin-right: 8px;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .card {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          padding: 20px;
          margin: 15px 0;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .card h2 {
          margin-bottom: 15px;
          color: #00d4ff;
          font-size: 1.3em;
        }

        .debug-logs {
          background: rgba(0, 0, 0, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 15px;
          max-height: 400px;
          overflow-y: auto;
          font-family: 'Courier New', monospace;
          font-size: 0.85em;
        }

        .log-entry {
          margin-bottom: 10px;
          padding-bottom: 10px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .log-entry:last-child {
          border-bottom: none;
        }

        .log-time {
          color: #888;
          margin-right: 10px;
        }

        .log-message {
          color: #fff;
        }

        .log-data {
          background: rgba(0, 0, 0, 0.4);
          padding: 10px;
          margin-top: 5px;
          border-radius: 4px;
          color: #00d4ff;
          font-size: 0.9em;
          overflow-x: auto;
        }

        .list-item {
          background: rgba(0, 0, 0, 0.3);
          padding: 15px;
          border-radius: 8px;
          margin: 10px 0;
          border-left: 3px solid #00d4ff;
        }

        .list-item h3 {
          color: #fff;
          margin-bottom: 8px;
          font-size: 1.1em;
        }

        .badge {
          display: inline-block;
          background: rgba(0, 212, 255, 0.2);
          color: #00d4ff;
          padding: 4px 10px;
          border-radius: 10px;
          font-size: 0.8em;
          margin-right: 6px;
          margin-top: 6px;
        }

        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #888;
        }

        .empty-state-icon {
          font-size: 3em;
          margin-bottom: 15px;
          opacity: 0.3;
        }

        code {
          background: rgba(0, 0, 0, 0.5);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          font-size: 0.85em;
        }
      </style>

      <div class="container">
        <h1>🌡️ Climate Control Calendar</h1>
        <p class="subtitle">Web UI - ${this.hass ? 'Connected ✅' : 'Waiting...'}</p>

        <div class="status-bar">
          <div class="status-badge">
            <span class="status-dot"></span>
            <span class="live-time">${timeStr}</span>
          </div>
          <div class="status-badge">📊 ${this.slots.length} Slots</div>
          <div class="status-badge">🔗 ${this.bindings.length} Bindings</div>
          <div class="status-badge">📅 ${this.calendars.length} Calendars</div>
        </div>

        <div class="card">
          <h2>🐛 Debug Console (Mobile-Friendly)</h2>
          <div class="debug-logs">
            ${this.logs.length === 0 ? '<div style="color: #888;">Waiting for logs...</div>' : ''}
          </div>
        </div>

        ${this.renderSlots()}
        ${this.renderBindings()}
        ${this.renderCalendars()}
      </div>
    `;

    // Update logs after render
    this.updateDebugLogs();
  }

  renderSlots() {
    if (this.slots.length === 0) {
      return `
        <div class="card">
          <h2>🎯 Climate Slots</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No slots configured</p>
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
        </div>
      `;
    }).join('');

    return `<div class="card"><h2>🎯 Slots (${this.slots.length})</h2>${slotsList}</div>`;
  }

  renderBindings() {
    if (this.bindings.length === 0) {
      return `
        <div class="card">
          <h2>🔗 Bindings</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No bindings configured</p>
          </div>
        </div>
      `;
    }

    const bindingsList = this.bindings.map(binding => {
      const matchType = binding.match?.type || 'unknown';
      const matchValue = binding.match?.value || '';
      const priority = binding.priority || 0;
      const slot = this.slots.find(s => s.id === binding.slot_id);
      const slotLabel = slot?.label || binding.slot_id;

      return `
        <div class="list-item">
          <h3>${matchValue || 'Unnamed'}</h3>
          <div>
            <span class="badge">📋 ${matchType}</span>
            <span class="badge">🎯 ${slotLabel}</span>
            <span class="badge">⚡ ${priority}</span>
          </div>
        </div>
      `;
    }).join('');

    return `<div class="card"><h2>🔗 Bindings (${this.bindings.length})</h2>${bindingsList}</div>`;
  }

  renderCalendars() {
    if (this.calendars.length === 0) {
      return `
        <div class="card">
          <h2>📅 Calendars</h2>
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No calendars configured</p>
          </div>
        </div>
      `;
    }

    const calendarsList = this.calendars.map(cal => `
      <div class="list-item"><h3>${cal}</h3></div>
    `).join('');

    return `<div class="card"><h2>📅 Calendars (${this.calendars.length})</h2>${calendarsList}</div>`;
  }

  showError(message) {
    this.log('❌', 'Showing error screen', { message });
    // Keep render method to show error in debug console too
  }
}

// Define the custom element
customElements.define('climate-panel-card', ClimatePanelCard);

console.log('🚀 Climate Control Panel - Custom element registered');
