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
    this.climate_entities = [];
    this.dry_run = true;
    this.debug_mode = false;
    this.updateInterval = null;
    this.refreshInterval = null;
    this.logs = []; // Visual debug logs
    this.maxLogs = 50; // Keep last 50 logs
    // Debug mode toggle - saved in localStorage
    this.debugEnabled = localStorage.getItem('climate_debug_enabled') !== 'false'; // Default: true
  }

  // Toggle debug mode
  toggleDebug() {
    this.debugEnabled = !this.debugEnabled;
    localStorage.setItem('climate_debug_enabled', this.debugEnabled);
    this.log('🔧', `Debug mode ${this.debugEnabled ? 'ENABLED' : 'DISABLED'}`);
    this.render();
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
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
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

      // Start auto-refresh every 30 seconds
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
      }
      this.refreshInterval = setInterval(() => {
        this.log('🔄', 'Auto-refresh triggered (every 30s)');
        this.loadIntegrationData();
      }, 30000);

    } catch (error) {
      this.log('❌', 'Failed to initialize', {
        error: error.message,
        stack: error.stack
      });
      this.showError(error.message);
    }
  }

  async manualRefresh() {
    this.log('🔄', 'Manual refresh requested');
    await this.loadIntegrationData();
  }

  async loadIntegrationData() {
    this.log('📥', 'Loading Climate Control Calendar data...');

    try {
      // Call our HTTP API endpoint
      this.log('🔍', 'Fetching /api/climate_control_calendar/config...');

      const response = await fetch('/api/climate_control_calendar/config', {
        headers: {
          'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
        }
      });

      this.log('📦', 'HTTP response received', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      this.log('📦', 'JSON data parsed', {
        hasSlots: !!data.slots,
        hasBindings: !!data.bindings,
        hasCalendars: !!data.calendars
      });

      // Extract data from API response
      this.slots = data?.slots || [];
      this.bindings = data?.bindings || [];
      this.calendars = data?.calendars || [];
      this.climate_entities = data?.climate_entities || [];
      this.dry_run = data?.dry_run ?? true;
      this.debug_mode = data?.debug_mode ?? false;

      this.log('✅', 'Data extracted successfully', {
        slots: this.slots.length,
        bindings: this.bindings.length,
        calendars: this.calendars.length,
        climate_entities: this.climate_entities.length,
        dry_run: this.dry_run,
        debug_mode: this.debug_mode
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

        .btn {
          background: rgba(0, 212, 255, 0.2);
          color: #00d4ff;
          border: 1px solid #00d4ff;
          padding: 8px 16px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.9em;
          margin: 5px;
          transition: all 0.2s;
        }

        .btn:hover {
          background: rgba(0, 212, 255, 0.4);
        }

        .btn-danger {
          background: rgba(255, 68, 68, 0.2);
          color: #ff4444;
          border-color: #ff4444;
        }

        .btn-danger:hover {
          background: rgba(255, 68, 68, 0.4);
        }

        .btn-small {
          padding: 4px 8px;
          font-size: 0.8em;
        }

        .actions {
          display: flex;
          gap: 10px;
          margin-top: 15px;
          flex-wrap: wrap;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
        }

        .card-header h2 {
          margin: 0;
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
          <div class="status-badge">🌡️ ${this.climate_entities.length} Climate Entities</div>
          <div class="status-badge" style="cursor: pointer;" id="refresh-btn">
            🔄 Refresh
          </div>
          <div class="status-badge" style="cursor: pointer;" id="debug-toggle">
            🐛 Debug: ${this.debugEnabled ? 'ON' : 'OFF'}
          </div>
        </div>

        ${this.debugEnabled ? `
        <div class="card">
          <h2>🐛 Debug Console</h2>
          <div class="debug-logs">
            ${this.logs.length === 0 ? '<div style="color: #888;">Waiting for logs...</div>' : ''}
          </div>
        </div>
        ` : ''}

        ${this.renderBasicConfig()}
        ${this.renderSlots()}
        ${this.renderBindings()}
        ${this.renderCalendars()}
      </div>
    `;

    // Update logs after render
    this.updateDebugLogs();

    // Attach event listeners
    const debugToggle = this.shadowRoot.querySelector('#debug-toggle');
    if (debugToggle) {
      debugToggle.addEventListener('click', () => this.toggleDebug());
    }

    const refreshBtn = this.shadowRoot.querySelector('#refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.manualRefresh());
    }

    // Attach action button listeners
    this.shadowRoot.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        const id = e.target.dataset.id;
        this.handleAction(action, id);
      });
    });
  }

  async handleAction(action, id) {
    this.log('🎬', `Action: ${action}`, { id });

    try {
      switch (action) {
        case 'edit-basic-config':
          await this.editBasicConfig();
          break;
        case 'add-slot':
          await this.addSlot();
          break;
        case 'edit-slot':
          await this.editSlot(id);
          break;
        case 'delete-slot':
          await this.deleteSlot(id);
          break;
        case 'add-binding':
          await this.addBinding();
          break;
        case 'edit-binding':
          await this.editBinding(id);
          break;
        case 'delete-binding':
          await this.deleteBinding(id);
          break;
        default:
          this.log('⚠️', `Unknown action: ${action}`);
      }
    } catch (error) {
      this.log('❌', `Action failed: ${action}`, { error: error.message });
      alert(`Error: ${error.message}`);
    }
  }

  async deleteSlot(slotId) {
    const slot = this.slots.find(s => s.id === slotId);
    if (!slot) return;

    if (!confirm(`Delete slot "${slot.label}"?`)) {
      return;
    }

    this.log('🗑️', `Deleting slot ${slotId}...`);

    await this.hass.callService('climate_control_calendar', 'remove_slot', {
      slot_id: slotId
    });

    this.log('✅', 'Slot deleted successfully - waiting for WebSocket update');

    // Don't reload manually - WebSocket subscription will handle it automatically
    // This prevents navigation issues from full DOM recreation
  }

  async deleteBinding(bindingId) {
    const binding = this.bindings.find(b => b.id === bindingId);
    if (!binding) return;

    if (!confirm(`Delete binding "${binding.match?.value || 'Unnamed'}"?`)) {
      return;
    }

    this.log('🗑️', `Deleting binding ${bindingId}...`);

    await this.hass.callService('climate_control_calendar', 'remove_binding', {
      binding_id: bindingId
    });

    this.log('✅', 'Binding deleted successfully - waiting for WebSocket update');

    // Don't reload manually - WebSocket subscription will handle it automatically
    // This prevents navigation issues from full DOM recreation
  }

  async addSlot() {
    // For now, just navigate to HA config
    this.log('➕', 'Add slot - redirecting to HA config...');
    alert('Please use Home Assistant Configuration UI to add slots for now.\n\nFull UI editor coming soon!');
  }

  async editSlot(slotId) {
    // For now, just navigate to HA config
    this.log('✏️', 'Edit slot - redirecting to HA config...');
    alert('Please use Home Assistant Configuration UI to edit slots for now.\n\nFull UI editor coming soon!');
  }

  async addBinding() {
    // For now, just navigate to HA config
    this.log('➕', 'Add binding - redirecting to HA config...');
    alert('Please use Home Assistant Configuration UI to add bindings for now.\n\nFull UI editor coming soon!');
  }

  async editBinding(bindingId) {
    // For now, just navigate to HA config
    this.log('✏️', 'Edit binding - redirecting to HA config...');
    alert('Please use Home Assistant Configuration UI to edit bindings for now.\n\nFull UI editor coming soon!');
  }

  async editBasicConfig() {
    this.log('✏️', 'Edit basic configuration...');

    // Get all available entities
    const allCalendars = Object.keys(this.hass.states)
      .filter(id => id.startsWith('calendar.'))
      .sort();

    const allClimateEntities = Object.keys(this.hass.states)
      .filter(id => id.startsWith('climate.'))
      .sort();

    // Build form HTML with checkboxes
    const calendarCheckboxes = allCalendars.map(cal => {
      const checked = this.calendars.includes(cal) ? 'checked' : '';
      return `
        <label style="display: block; margin: 5px 0;">
          <input type="checkbox" name="calendars" value="${cal}" ${checked}>
          ${cal}
        </label>
      `;
    }).join('');

    const climateCheckboxes = allClimateEntities.map(ent => {
      const checked = this.climate_entities.includes(ent) ? 'checked' : '';
      return `
        <label style="display: block; margin: 5px 0;">
          <input type="checkbox" name="climate_entities" value="${ent}" ${checked}>
          ${ent}
        </label>
      `;
    }).join('');

    // Create a modal dialog
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    modal.innerHTML = `
      <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 30px;
        border-radius: 12px;
        max-width: 600px;
        width: 90%;
        max-height: 80%;
        overflow-y: auto;
        border: 1px solid rgba(255, 255, 255, 0.2);
      ">
        <h2 style="margin-top: 0; color: #00d4ff;">⚙️ Edit Basic Configuration</h2>

        <div style="margin: 20px 0;">
          <h3 style="color: #00d4ff; margin-bottom: 10px;">📅 Calendar Entities</h3>
          <div style="max-height: 150px; overflow-y: auto; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
            ${calendarCheckboxes || '<p style="color: #888;">No calendar entities found</p>'}
          </div>
        </div>

        <div style="margin: 20px 0;">
          <h3 style="color: #00d4ff; margin-bottom: 10px;">🌡️ Climate Entities</h3>
          <div style="max-height: 150px; overflow-y: auto; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
            ${climateCheckboxes || '<p style="color: #888;">No climate entities found</p>'}
          </div>
        </div>

        <div style="margin: 20px 0;">
          <h3 style="color: #00d4ff; margin-bottom: 10px;">🔧 Options</h3>
          <label style="display: block; margin: 10px 0;">
            <input type="checkbox" id="dry_run" ${this.dry_run ? 'checked' : ''}>
            Dry Run Mode (test without applying changes)
          </label>
          <label style="display: block; margin: 10px 0;">
            <input type="checkbox" id="debug_mode" ${this.debug_mode ? 'checked' : ''}>
            Debug Mode (verbose logging)
          </label>
        </div>

        <div style="display: flex; gap: 10px; margin-top: 20px;">
          <button id="save-btn" style="
            flex: 1;
            background: rgba(0, 212, 255, 0.2);
            color: #00d4ff;
            border: 1px solid #00d4ff;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
          ">💾 Save</button>
          <button id="cancel-btn" style="
            flex: 1;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
          ">❌ Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Handle save
    modal.querySelector('#save-btn').addEventListener('click', async () => {
      try {
        // Collect selected calendars
        const selectedCalendars = Array.from(modal.querySelectorAll('input[name="calendars"]:checked'))
          .map(cb => cb.value);

        // Collect selected climate entities
        const selectedClimate = Array.from(modal.querySelectorAll('input[name="climate_entities"]:checked'))
          .map(cb => cb.value);

        const dryRun = modal.querySelector('#dry_run').checked;
        const debugMode = modal.querySelector('#debug_mode').checked;

        this.log('💾', 'Saving basic config...', {
          calendars: selectedCalendars.length,
          climate: selectedClimate.length,
          dry_run: dryRun,
          debug_mode: debugMode
        });

        // Send to API
        const response = await fetch('/api/climate_control_calendar/config', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            calendar_entities: selectedCalendars,
            climate_entities: selectedClimate,
            dry_run: dryRun,
            debug_mode: debugMode,
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        this.log('✅', 'Configuration saved successfully', result);

        // Close modal
        document.body.removeChild(modal);

        // Reload data - WebSocket will handle it
        this.log('🔄', 'Waiting for config update via WebSocket...');

      } catch (error) {
        this.log('❌', 'Failed to save config', { error: error.message });
        alert(`Error saving configuration: ${error.message}`);
      }
    });

    // Handle cancel
    modal.querySelector('#cancel-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });
  }

  renderBasicConfig() {
    return `
      <div class="card">
        <div class="card-header">
          <h2>⚙️ Basic Configuration</h2>
          <button class="btn" data-action="edit-basic-config">✏️ Edit</button>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
          <div class="list-item">
            <h3>📅 Calendar Entities</h3>
            <div style="margin-top: 10px;">
              ${this.calendars.length > 0 ? this.calendars.map(cal => `
                <div style="margin: 5px 0; color: #00d4ff;">• ${cal}</div>
              `).join('') : '<div style="color: #888;">None configured</div>'}
            </div>
          </div>
          <div class="list-item">
            <h3>🌡️ Climate Entities</h3>
            <div style="margin-top: 10px;">
              ${this.climate_entities.length > 0 ? this.climate_entities.map(ent => `
                <div style="margin: 5px 0; color: #00d4ff;">• ${ent}</div>
              `).join('') : '<div style="color: #888;">None configured</div>'}
            </div>
          </div>
          <div class="list-item">
            <h3>🔧 Options</h3>
            <div style="margin-top: 10px;">
              <div style="margin: 5px 0;">
                <span class="badge">${this.dry_run ? '✅ Dry Run: ON' : '❌ Dry Run: OFF'}</span>
              </div>
              <div style="margin: 5px 0;">
                <span class="badge">${this.debug_mode ? '✅ Debug: ON' : '❌ Debug: OFF'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderSlots() {
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
          <div class="actions">
            <button class="btn btn-small" data-action="edit-slot" data-id="${slot.id}">✏️ Edit</button>
            <button class="btn btn-small btn-danger" data-action="delete-slot" data-id="${slot.id}">🗑️ Delete</button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card">
        <div class="card-header">
          <h2>🎯 Slots (${this.slots.length})</h2>
          <button class="btn" data-action="add-slot">➕ Add Slot</button>
        </div>
        ${this.slots.length === 0 ? `
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No slots configured yet</p>
            <p style="margin-top: 10px; color: #666;">Click "Add Slot" to create one</p>
          </div>
        ` : slotsList}
      </div>
    `;
  }

  renderBindings() {
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
            <span class="badge">⚡ Priority: ${priority}</span>
          </div>
          <div class="actions">
            <button class="btn btn-small" data-action="edit-binding" data-id="${binding.id}">✏️ Edit</button>
            <button class="btn btn-small btn-danger" data-action="delete-binding" data-id="${binding.id}">🗑️ Delete</button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card">
        <div class="card-header">
          <h2>🔗 Bindings (${this.bindings.length})</h2>
          <button class="btn" data-action="add-binding">➕ Add Binding</button>
        </div>
        ${this.bindings.length === 0 ? `
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No bindings configured yet</p>
            <p style="margin-top: 10px; color: #666;">Click "Add Binding" to create one</p>
          </div>
        ` : bindingsList}
      </div>
    `;
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
