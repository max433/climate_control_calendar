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
    this.calendar_configs = {};
    this.dry_run = true;
    this.debug_mode = false;
    this.updateInterval = null;
    this.refreshInterval = null;
    this.statusRefreshInterval = null;
    // Status data
    this.statusData = null;
    this.logs = []; // Visual debug logs
    this.maxLogs = 50; // Keep last 50 logs
    // Debug mode toggle - saved in localStorage
    this.debugEnabled = localStorage.getItem('climate_debug_enabled') !== 'false'; // Default: true
    // Navigation state
    this.currentPage = localStorage.getItem('climate_current_page') || 'config';
    this.sidebarOpen = false;
  }

  // Toggle debug mode
  toggleDebug() {
    this.debugEnabled = !this.debugEnabled;
    localStorage.setItem('climate_debug_enabled', this.debugEnabled);
    this.log('🔧', `Debug mode ${this.debugEnabled ? 'ENABLED' : 'DISABLED'}`);
    this.render();
  }

  // Toggle sidebar
  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
    this.render();
  }

  // Navigate to page
  navigateTo(page) {
    this.currentPage = page;
    localStorage.setItem('climate_current_page', page);
    this.sidebarOpen = false;
    this.log('📄', `Navigated to ${page}`);

    // Setup page-specific refresh intervals
    if (page === 'monitor') {
      this.startStatusRefresh();
    } else {
      this.stopStatusRefresh();
    }

    this.render();
  }

  startStatusRefresh() {
    // Clear existing interval
    this.stopStatusRefresh();

    // Load status immediately
    this.loadStatusData();

    // Refresh every 5 seconds for monitor page
    this.statusRefreshInterval = setInterval(() => {
      this.loadStatusData();
    }, 5000);

    this.log('🔄', 'Started status auto-refresh (5s)');
  }

  stopStatusRefresh() {
    if (this.statusRefreshInterval) {
      clearInterval(this.statusRefreshInterval);
      this.statusRefreshInterval = null;
      this.log('⏹️', 'Stopped status auto-refresh');
    }
  }

  async loadStatusData() {
    if (!this.hass) return;

    try {
      const response = await fetch('/api/climate_control_calendar/status', {
        headers: {
          'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      this.statusData = await response.json();
      this.log('📊', 'Status data loaded', this.statusData.summary);

      // Re-render only the monitor page content if we're on that page
      if (this.currentPage === 'monitor') {
        this.updateMonitorPage();
      }

    } catch (error) {
      this.log('❌', 'Failed to load status data', { error: error.message });
    }
  }

  updateMonitorPage() {
    // Update only the page-content div to avoid full re-render
    const pageContent = this.shadowRoot.querySelector('.page-content');
    if (pageContent) {
      pageContent.innerHTML = this.renderMonitorPage();
    }
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
    if (this.statusRefreshInterval) {
      clearInterval(this.statusRefreshInterval);
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
      this.calendar_configs = data?.calendar_configs || {};
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
          position: relative;
        }

        .hamburger-menu {
          position: fixed;
          top: 20px;
          left: 20px;
          width: 40px;
          height: 40px;
          background: rgba(0, 212, 255, 0.2);
          border: 1px solid #00d4ff;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 5px;
          z-index: 1001;
          transition: all 0.3s;
        }

        .hamburger-menu:hover {
          background: rgba(0, 212, 255, 0.4);
        }

        .hamburger-line {
          width: 24px;
          height: 2px;
          background: #00d4ff;
          transition: all 0.3s;
        }

        .hamburger-menu.open .hamburger-line:nth-child(1) {
          transform: rotate(45deg) translateY(7px);
        }

        .hamburger-menu.open .hamburger-line:nth-child(2) {
          opacity: 0;
        }

        .hamburger-menu.open .hamburger-line:nth-child(3) {
          transform: rotate(-45deg) translateY(-7px);
        }

        .sidebar {
          position: fixed;
          top: 0;
          left: ${this.sidebarOpen ? '0' : '-280px'};
          width: 280px;
          height: 100%;
          background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
          border-right: 1px solid rgba(0, 212, 255, 0.3);
          transition: left 0.3s ease;
          z-index: 1000;
          overflow-y: auto;
          padding: 80px 20px 20px 20px;
        }

        .sidebar-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.5);
          display: ${this.sidebarOpen ? 'block' : 'none'};
          z-index: 999;
        }

        .nav-item {
          padding: 15px 20px;
          margin: 5px 0;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          border-left: 3px solid transparent;
        }

        .nav-item:hover {
          background: rgba(0, 212, 255, 0.1);
          border-left-color: #00d4ff;
        }

        .nav-item.active {
          background: rgba(0, 212, 255, 0.2);
          border-left-color: #00d4ff;
        }

        .nav-item-icon {
          font-size: 1.2em;
          margin-right: 10px;
        }

        .page-content {
          margin-top: 20px;
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

      <!-- Hamburger Menu -->
      <div class="hamburger-menu ${this.sidebarOpen ? 'open' : ''}" id="hamburger-btn">
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
      </div>

      <!-- Sidebar Overlay -->
      <div class="sidebar-overlay" id="sidebar-overlay"></div>

      <!-- Sidebar -->
      <div class="sidebar">
        <div class="nav-item ${this.currentPage === 'config' ? 'active' : ''}" data-page="config">
          <span class="nav-item-icon">⚙️</span>
          Configuration
        </div>
        <div class="nav-item ${this.currentPage === 'monitor' ? 'active' : ''}" data-page="monitor">
          <span class="nav-item-icon">📊</span>
          Monitoring
        </div>
        <div class="nav-item ${this.currentPage === 'charts' ? 'active' : ''}" data-page="charts">
          <span class="nav-item-icon">📈</span>
          Charts & Stats
        </div>
        <div class="nav-item ${this.currentPage === 'about' ? 'active' : ''}" data-page="about">
          <span class="nav-item-icon">ℹ️</span>
          About
        </div>
      </div>

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

        <div class="page-content">
          ${this.renderPage()}
        </div>
      </div>
    `;

    // Update logs after render
    this.updateDebugLogs();

    // Attach event listeners
    const hamburgerBtn = this.shadowRoot.querySelector('#hamburger-btn');
    if (hamburgerBtn) {
      hamburgerBtn.addEventListener('click', () => this.toggleSidebar());
    }

    const sidebarOverlay = this.shadowRoot.querySelector('#sidebar-overlay');
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', () => this.toggleSidebar());
    }

    const debugToggle = this.shadowRoot.querySelector('#debug-toggle');
    if (debugToggle) {
      debugToggle.addEventListener('click', () => this.toggleDebug());
    }

    const refreshBtn = this.shadowRoot.querySelector('#refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.manualRefresh());
    }

    // Attach nav item listeners
    this.shadowRoot.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const page = e.currentTarget.dataset.page;
        if (page) {
          this.navigateTo(page);
        }
      });
    });

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
        case 'edit-calendar':
          await this.editCalendar(id);
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

        // Refresh data manually (like the refresh button)
        await this.manualRefresh();

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

  renderPage() {
    switch (this.currentPage) {
      case 'config':
        return this.renderConfigPage();
      case 'monitor':
        return this.renderMonitorPage();
      case 'charts':
        return this.renderChartsPage();
      case 'about':
        return this.renderAboutPage();
      default:
        return this.renderConfigPage();
    }
  }

  renderConfigPage() {
    return `
      ${this.renderBasicConfig()}
      ${this.renderSlots()}
      ${this.renderBindings()}
      ${this.renderCalendars()}
    `;
  }

  renderMonitorPage() {
    if (!this.statusData) {
      return `
        <div class="card">
          <h2>📊 Real-Time Monitoring</h2>
          <p style="color: #888; text-align: center; padding: 40px 20px;">
            Loading status data...
          </p>
        </div>
      `;
    }

    const { active_events, climate_states, matched_bindings, engine_state, summary } = this.statusData;

    return `
      <!-- Summary Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
        <div class="card" style="text-align: center;">
          <h3 style="color: #00d4ff; margin: 0 0 10px 0;">📅 Active Events</h3>
          <div style="font-size: 2.5em; font-weight: bold;">${summary.active_events_count}</div>
        </div>
        <div class="card" style="text-align: center;">
          <h3 style="color: #00d4ff; margin: 0 0 10px 0;">🌡️ Climates ON</h3>
          <div style="font-size: 2.5em; font-weight: bold;">${summary.climates_on}/${summary.total_climates}</div>
        </div>
        <div class="card" style="text-align: center;">
          <h3 style="color: #00d4ff; margin: 0 0 10px 0;">🔗 Matched Bindings</h3>
          <div style="font-size: 2.5em; font-weight: bold;">${matched_bindings.length}</div>
        </div>
      </div>

      <!-- Active Calendar Events -->
      <div class="card">
        <h2>📅 Active Calendar Events (${active_events.length})</h2>
        ${active_events.length === 0 ? `
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No active events at the moment</p>
          </div>
        ` : active_events.map(event => `
          <div class="list-item" style="border-left-color: #00ff88;">
            <h3>${event.summary || 'Unnamed Event'}</h3>
            <div>
              <span class="badge">📅 ${event.calendar_id.split('.')[1]}</span>
              ${event.all_day ? '<span class="badge">🕐 All Day</span>' : ''}
            </div>
            ${event.description ? `<p style="margin-top: 10px; color: #ccc;">${event.description}</p>` : ''}
            <div style="margin-top: 10px; color: #888; font-size: 0.9em;">
              <div>⏰ Start: ${this.formatDateTime(event.start)}</div>
              <div>⏰ End: ${this.formatDateTime(event.end)}</div>
              ${event.location ? `<div>📍 ${event.location}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>

      <!-- Climate Entities Status -->
      <div class="card">
        <h2>🌡️ Climate Entities Status (${climate_states.length})</h2>
        ${climate_states.length === 0 ? `
          <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No climate entities configured</p>
          </div>
        ` : `
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">
            ${climate_states.map(climate => this.renderClimateCard(climate)).join('')}
          </div>
        `}
      </div>

      <!-- Matched Bindings -->
      ${matched_bindings.length > 0 ? `
      <div class="card">
        <h2>🔗 Currently Matched Bindings (${matched_bindings.length})</h2>
        ${matched_bindings.map(binding => {
          const slot = this.slots.find(s => s.id === binding.slot_id);
          return `
            <div class="list-item" style="border-left-color: #00d4ff;">
              <h3>${binding.match?.value || 'Unnamed'}</h3>
              <div>
                <span class="badge">🎯 Slot: ${slot?.label || binding.slot_id}</span>
                <span class="badge">📋 ${binding.match?.type}</span>
                <span class="badge">⚡ Priority: ${binding.priority || 0}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
      ` : ''}

      <!-- Engine State -->
      <div class="card">
        <h2>⚙️ Engine Status</h2>
        <div style="padding: 15px; background: rgba(0,0,0,0.3); border-radius: 8px;">
          <div style="margin: 5px 0;">
            <span style="color: #00d4ff;">Engine Active:</span>
            <span style="color: ${engine_state.has_engine ? '#00ff88' : '#ff4444'};">
              ${engine_state.has_engine ? '✅ Yes' : '❌ No'}
            </span>
          </div>
          ${engine_state.last_evaluation ? `
            <div style="margin: 5px 0;">
              <span style="color: #00d4ff;">Last Evaluation:</span>
              <span>${this.formatDateTime(engine_state.last_evaluation)}</span>
            </div>
          ` : ''}
          <div style="margin: 5px 0;">
            <span style="color: #00d4ff;">Timestamp:</span>
            <span>${this.formatDateTime(this.statusData.timestamp)}</span>
          </div>
        </div>
      </div>
    `;
  }

  renderClimateCard(climate) {
    const temp = climate.attributes.current_temperature;
    const targetTemp = climate.attributes.temperature;
    const hvacMode = climate.state;
    const hvacAction = climate.attributes.hvac_action;

    const isOn = hvacMode !== 'off';
    const statusColor = isOn ? '#00ff88' : '#888';

    return `
      <div class="list-item" style="border-left-color: ${statusColor};">
        <h3>${climate.entity_id.split('.')[1].replace(/_/g, ' ')}</h3>
        <div style="margin: 10px 0;">
          <div style="font-size: 1.5em; color: ${statusColor}; margin-bottom: 5px;">
            ${temp !== null && temp !== undefined ? `${temp}°C` : 'N/A'}
            ${targetTemp !== null && targetTemp !== undefined ? ` → ${targetTemp}°C` : ''}
          </div>
          <div>
            <span class="badge">${this.getHvacModeIcon(hvacMode)} ${hvacMode.toUpperCase()}</span>
            ${hvacAction ? `<span class="badge">${this.getHvacActionIcon(hvacAction)} ${hvacAction}</span>` : ''}
          </div>
        </div>
        ${climate.attributes.preset_mode ? `
          <div style="margin-top: 8px;">
            <span class="badge">⚙️ ${climate.attributes.preset_mode}</span>
          </div>
        ` : ''}
        <div style="margin-top: 8px; font-size: 0.85em; color: #666;">
          Updated: ${this.formatTimeAgo(climate.last_updated)}
        </div>
      </div>
    `;
  }

  getHvacModeIcon(mode) {
    const icons = {
      'heat': '🔥',
      'cool': '❄️',
      'heat_cool': '🔄',
      'auto': '🤖',
      'off': '⭕',
      'dry': '💨',
      'fan_only': '🌀',
    };
    return icons[mode] || '❓';
  }

  getHvacActionIcon(action) {
    const icons = {
      'heating': '🔥',
      'cooling': '❄️',
      'idle': '⏸️',
      'off': '⭕',
      'drying': '💨',
      'fan': '🌀',
    };
    return icons[action] || '❓';
  }

  formatDateTime(isoString) {
    if (!isoString) return 'N/A';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return isoString;
    }
  }

  formatTimeAgo(isoString) {
    if (!isoString) return 'N/A';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const seconds = Math.floor((now - date) / 1000);

      if (seconds < 60) return `${seconds}s ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
      if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
      return `${Math.floor(seconds / 86400)}d ago`;
    } catch (e) {
      return isoString;
    }
  }

  renderChartsPage() {
    return `
      <div class="card">
        <h2>📈 Charts & Statistics</h2>
        <p style="color: #888; text-align: center; padding: 40px 20px;">
          Charts and statistics dashboard coming soon!<br><br>
          This will show:<br>
          • Temperature history graphs<br>
          • Usage statistics<br>
          • Event frequency charts<br>
          • Energy consumption trends
        </p>
      </div>
    `;
  }

  renderAboutPage() {
    return `
      <div class="card">
        <h2>ℹ️ About Climate Control Calendar</h2>
        <div style="padding: 20px;">
          <h3 style="color: #00d4ff; margin-top: 20px;">Version</h3>
          <p>Web UI Alpha (v${this.hass?.config?.version || 'unknown'})</p>

          <h3 style="color: #00d4ff; margin-top: 20px;">Description</h3>
          <p>Climate Control Calendar is a Home Assistant custom integration that automatically controls your climate devices based on calendar events.</p>

          <h3 style="color: #00d4ff; margin-top: 20px;">Features</h3>
          <ul style="color: #ccc;">
            <li>Calendar-based climate automation</li>
            <li>Flexible slot system for climate presets</li>
            <li>Event matching with regex support</li>
            <li>Multi-calendar support</li>
            <li>Priority-based conflict resolution</li>
            <li>Dry run mode for testing</li>
          </ul>

          <h3 style="color: #00d4ff; margin-top: 20px;">Current Configuration</h3>
          <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-top: 10px;">
            <div>📅 Calendars: ${this.calendars.length}</div>
            <div>🌡️ Climate Entities: ${this.climate_entities.length}</div>
            <div>🎯 Slots: ${this.slots.length}</div>
            <div>🔗 Bindings: ${this.bindings.length}</div>
            <div>🔧 Dry Run: ${this.dry_run ? 'Enabled' : 'Disabled'}</div>
            <div>🐛 Debug: ${this.debug_mode ? 'Enabled' : 'Disabled'}</div>
          </div>

          <h3 style="color: #00d4ff; margin-top: 20px;">Links</h3>
          <p>
            <a href="https://github.com/max433/climate_control_calendar" target="_blank" style="color: #00d4ff;">
              📦 GitHub Repository
            </a>
          </p>
        </div>
      </div>
    `;
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

  async editCalendar(calendarId) {
    this.log('✏️', `Edit calendar: ${calendarId}`);

    // Get current config for this calendar
    const currentConfig = this.calendar_configs[calendarId] || {
      enabled: true,
      default_priority: 0,
      description: '',
    };

    // Count bindings using this calendar
    const bindingCount = this.bindings.filter(b =>
      b.calendars === '*' || (Array.isArray(b.calendars) && b.calendars.includes(calendarId)) || b.calendars === calendarId
    ).length;

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
        max-width: 500px;
        width: 90%;
        border: 1px solid rgba(255, 255, 255, 0.2);
      ">
        <h2 style="margin-top: 0; color: #00d4ff;">📅 Edit Calendar</h2>
        <p style="color: #888; margin-bottom: 20px;">${calendarId}</p>

        <div style="margin: 20px 0;">
          <label style="display: block; margin-bottom: 15px;">
            <input type="checkbox" id="enabled" ${currentConfig.enabled ? 'checked' : ''}>
            <strong>Enable this calendar</strong>
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              When disabled, events from this calendar will be ignored
            </div>
          </label>

          <label style="display: block; margin-bottom: 15px;">
            <strong>Default Priority (0-100)</strong>
            <input type="number" id="priority" min="0" max="100" value="${currentConfig.default_priority || 0}"
              style="width: 100%; padding: 8px; margin-top: 5px; background: rgba(0,0,0,0.3); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px;">
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              Higher priority calendars take precedence in conflicts
            </div>
          </label>

          <label style="display: block; margin-bottom: 15px;">
            <strong>Description (optional)</strong>
            <textarea id="description" rows="3"
              style="width: 100%; padding: 8px; margin-top: 5px; background: rgba(0,0,0,0.3); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px;"
            >${currentConfig.description || ''}</textarea>
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              A note to help you remember what this calendar is for
            </div>
          </label>

          <div style="background: rgba(0,212,255,0.1); padding: 10px; border-radius: 8px; border-left: 3px solid #00d4ff;">
            <strong>📊 Stats:</strong> ${bindingCount} binding${bindingCount !== 1 ? 's' : ''} using this calendar
          </div>
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
        const enabled = modal.querySelector('#enabled').checked;
        const priority = parseInt(modal.querySelector('#priority').value, 10);
        const description = modal.querySelector('#description').value.trim();

        this.log('💾', `Saving calendar config for ${calendarId}...`, { enabled, priority, description });

        // Update calendar_configs
        const updatedConfigs = {...this.calendar_configs};
        updatedConfigs[calendarId] = {
          enabled,
          default_priority: priority,
          description,
        };

        // Send to API
        const response = await fetch('/api/climate_control_calendar/config', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            calendar_configs: updatedConfigs,
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        this.log('✅', 'Calendar configuration saved successfully', result);

        // Close modal
        document.body.removeChild(modal);

        // Refresh data manually (like the refresh button)
        await this.manualRefresh();

      } catch (error) {
        this.log('❌', 'Failed to save calendar config', { error: error.message });
        alert(`Error saving calendar configuration: ${error.message}`);
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

    const calendarsList = this.calendars.map(cal => {
      const config = this.calendar_configs[cal] || {};
      const enabled = config.enabled !== false; // Default to true
      const priority = config.default_priority || 0;
      const description = config.description || '';
      const bindingCount = this.bindings.filter(b =>
        b.calendars === '*' || (Array.isArray(b.calendars) && b.calendars.includes(cal)) || b.calendars === cal
      ).length;

      return `
        <div class="list-item">
          <h3>${cal} ${!enabled ? '(Disabled)' : ''}</h3>
          <div>
            <span class="badge">${enabled ? '✅ Enabled' : '❌ Disabled'}</span>
            <span class="badge">⚡ Priority: ${priority}</span>
            <span class="badge">🔗 ${bindingCount} binding${bindingCount !== 1 ? 's' : ''}</span>
          </div>
          ${description ? `<div style="margin-top: 8px; color: #888; font-style: italic;">${description}</div>` : ''}
          <div class="actions">
            <button class="btn btn-small" data-action="edit-calendar" data-id="${cal}">✏️ Edit</button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card">
        <div class="card-header">
          <h2>📅 Calendars (${this.calendars.length})</h2>
        </div>
        ${calendarsList}
      </div>
    `;
  }

  showError(message) {
    this.log('❌', 'Showing error screen', { message });
    // Keep render method to show error in debug console too
  }
}

// Define the custom element
customElements.define('climate-panel-card', ClimatePanelCard);

console.log('🚀 Climate Control Panel - Custom element registered');
