/**
 * Climate Control Calendar Panel
 * Custom element with WebSocket connection to Home Assistant
 * WITH VISUAL DEBUG CONSOLE FOR MOBILE
 */

// I18n system
class I18n {
  constructor() {
    this.translations = {};
    this.language = 'en';
    this.loaded = false;
  }

  async loadTranslations(language) {
    try {
      const response = await fetch(`/api/climate_control_calendar/translations/${language}`);
      if (response.ok) {
        this.translations = await response.json();
        this.language = language;
        this.loaded = true;
        console.log(`✅ Translations loaded for language: ${language}`);
        return true;
      }
    } catch (error) {
      console.error(`❌ Failed to load translations for ${language}:`, error);
    }

    // Fallback to English
    if (language !== 'en') {
      return await this.loadTranslations('en');
    }

    return false;
  }

  // Translate a key with optional replacements
  t(key, replacements = {}) {
    if (!this.loaded) {
      return key; // Return key if translations not loaded yet
    }

    const keys = key.split('.');
    let value = this.translations;

    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        return key; // Key not found, return the key itself
      }
    }

    if (typeof value !== 'string') {
      return key;
    }

    // Replace placeholders
    let result = value;
    for (const [placeholder, replacement] of Object.entries(replacements)) {
      result = result.replace(`{${placeholder}}`, replacement);
    }

    return result;
  }
}

// Global i18n instance
const i18n = new I18n();

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
    // I18n ready flag
    this.i18nReady = false;
    // Theme state (light/dark)
    this.theme = localStorage.getItem('climate_theme') || 'dark';
  }

  // Toggle debug mode
  toggleDebug() {
    this.debugEnabled = !this.debugEnabled;
    localStorage.setItem('climate_debug_enabled', this.debugEnabled);
    this.log('🔧', `Debug mode ${this.debugEnabled ? 'ENABLED' : 'DISABLED'}`);
    this.render();
  }

  // Toggle theme (dark/light)
  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('climate_theme', this.theme);
    this.log('🎨', `Theme switched to ${this.theme}`);
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
      // Load translations first
      if (!i18n.loaded) {
        // Detect language from Home Assistant
        const language = this.hass.language || 'en';
        await i18n.loadTranslations(language);
        this.i18nReady = true;
        this.log('🌍', `Translations loaded for language: ${language}`);
        // Re-render with translations
        this.render();
      }

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

  // Helper method for translations
  t(key, replacements = {}) {
    return i18n.t(key, replacements);
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
      <!-- Bootstrap 5.3.3 Official CSS -->
      <link rel="stylesheet" href="/local/climate_control_calendar/bootstrap.min.css">

      <!-- Select2 CSS -->
      <link rel="stylesheet" href="/local/climate_control_calendar/select2.min.css">
      <link rel="stylesheet" href="/local/climate_control_calendar/select2-bootstrap-5-theme.min.css">

      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          color-scheme: ${this.theme};
        }

        :host([data-bs-theme="dark"]) {
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

        /* Searchable Select Styles */
        .searchable-select-container {
          position: relative;
          width: 100%;
        }

        .searchable-select-display {
          width: 100%;
          padding: 8px 30px 8px 10px;
          background: rgba(0,0,0,0.3);
          color: white;
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 4px;
          font-size: 14px;
          cursor: pointer;
          background-image: url('data:image/svg+xml;utf8,<svg fill="white" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5z"/></svg>');
          background-repeat: no-repeat;
          background-position: right 5px center;
          background-size: 20px;
        }

        .searchable-select-display:focus {
          outline: none;
          border-color: #00d4ff;
          box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2);
          background-image: url('data:image/svg+xml;utf8,<svg fill="%2300d4ff" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>');
        }

        .searchable-select-display::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .searchable-select-dropdown {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          max-height: 250px;
          overflow-y: auto;
          background: rgba(20, 20, 35, 0.98);
          border: 1px solid #00d4ff;
          border-radius: 4px;
          margin-top: 4px;
          z-index: 1000;
          box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }

        .searchable-select-option {
          padding: 10px 12px;
          cursor: pointer;
          color: white;
          transition: background 0.2s;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .searchable-select-option:last-child {
          border-bottom: none;
        }

        .searchable-select-option:hover {
          background: rgba(0, 212, 255, 0.2);
        }

        .searchable-select-option.selected {
          background: rgba(0, 212, 255, 0.3);
          font-weight: bold;
        }

        .searchable-select-no-results {
          color: rgba(255, 255, 255, 0.5);
          font-style: italic;
          cursor: default;
        }

        .searchable-select-no-results:hover {
          background: transparent;
        }

        .searchable-select-dropdown::-webkit-scrollbar {
          width: 8px;
        }

        .searchable-select-dropdown::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.2);
        }

        .searchable-select-dropdown::-webkit-scrollbar-thumb {
          background: rgba(0, 212, 255, 0.5);
          border-radius: 4px;
        }

        .searchable-select-dropdown::-webkit-scrollbar-thumb:hover {
          background: rgba(0, 212, 255, 0.7);
        }
      </style>

      <!-- jQuery (required for Select2) -->
      <script src="/local/climate_control_calendar/jquery.slim.min.js"></script>

      <!-- Select2 JS -->
      <script src="/local/climate_control_calendar/select2.min.js"></script>

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
          ${this.t('navigation.config')}
        </div>
        <div class="nav-item ${this.currentPage === 'monitor' ? 'active' : ''}" data-page="monitor">
          <span class="nav-item-icon">📊</span>
          ${this.t('navigation.monitor')}
        </div>
        <div class="nav-item ${this.currentPage === 'charts' ? 'active' : ''}" data-page="charts">
          <span class="nav-item-icon">📈</span>
          ${this.t('navigation.charts')}
        </div>
        <div class="nav-item ${this.currentPage === 'about' ? 'active' : ''}" data-page="about">
          <span class="nav-item-icon">ℹ️</span>
          ${this.t('navigation.about')}
        </div>

        <div style="margin-top: auto; padding: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
          <div class="nav-item" id="theme-toggle" style="cursor: pointer;">
            <span class="nav-item-icon">${this.theme === 'dark' ? '🌙' : '☀️'}</span>
            ${this.theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
          </div>
        </div>
      </div>

      <div class="container">
        <h1>🌡️ ${this.t('header.title')}</h1>
        <p class="subtitle">${this.t('header.subtitle')} - ${this.hass ? this.t('header.connected') + ' ✅' : this.t('header.waiting')}</p>

        <div class="status-bar">
          <div class="status-badge">
            <span class="status-dot"></span>
            <span class="live-time">${timeStr}</span>
          </div>
          <div class="status-badge">📊 ${this.slots.length} ${this.t('status_bar.slots')}</div>
          <div class="status-badge">🔗 ${this.bindings.length} ${this.t('status_bar.bindings')}</div>
          <div class="status-badge">📅 ${this.calendars.length} ${this.t('status_bar.calendars')}</div>
          <div class="status-badge">🌡️ ${this.climate_entities.length} ${this.t('status_bar.climate_entities')}</div>
          <div class="status-badge" style="cursor: pointer;" id="refresh-btn">
            🔄 ${this.t('status_bar.refresh')}
          </div>
          <div class="status-badge" style="cursor: pointer;" id="debug-toggle">
            🐛 ${this.t('status_bar.debug')}: ${this.debugEnabled ? 'ON' : 'OFF'}
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

    // Apply theme attribute
    this.setAttribute('data-bs-theme', this.theme);

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

    const themeToggle = this.shadowRoot.querySelector('#theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => this.toggleTheme());
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

  // Helper: Parse value that can be template or number
  parseTemplateOrNumber(value, fieldName, min = -50, max = 50) {
    if (!value || !value.trim()) {
      return { valid: true, value: null, isTemplate: false };
    }

    const trimmed = value.trim();

    // Check if it's a template
    if (trimmed.includes('{{') && trimmed.includes('}}')) {
      // It's a template, return as string
      return { valid: true, value: trimmed, isTemplate: true };
    }

    // It's a static value, validate as number
    const num = parseFloat(trimmed);
    if (isNaN(num)) {
      return {
        valid: false,
        error: `${fieldName} must be a number or a template ({{ ... }})`,
        isTemplate: false
      };
    }

    if (num < min || num > max) {
      return {
        valid: false,
        error: `${fieldName} must be between ${min} and ${max}°C`,
        isTemplate: false
      };
    }

    return { valid: true, value: num, isTemplate: false };
  }

  // Helper: Evaluate template and return rendered value
  async evaluateTemplate(templateString) {
    if (!templateString || !templateString.includes('{{') || !templateString.includes('}}')) {
      return { success: false, error: 'Not a template' };
    }

    try {
      // Use Home Assistant's template rendering via WebSocket
      const result = await this.hass.callWS({
        type: 'render_template',
        template: templateString
      });

      return { success: true, value: result };
    } catch (error) {
      return { success: false, error: error.message || 'Template rendering failed' };
    }
  }

  // Helper: Add template preview to an input element
  addTemplatePreview(inputElement, previewId) {
    // Check if preview already exists
    let previewDiv = inputElement.parentElement.querySelector(`#${previewId}`);
    if (!previewDiv) {
      previewDiv = document.createElement('div');
      previewDiv.id = previewId;
      previewDiv.style.cssText = 'color: #888; font-size: 0.85em; margin-top: 5px; padding: 5px; background: rgba(0,0,0,0.2); border-radius: 4px; display: none;';
      inputElement.parentElement.appendChild(previewDiv);
    }

    // Add blur event listener for live evaluation
    inputElement.addEventListener('blur', async () => {
      const value = inputElement.value.trim();

      // Hide preview if empty or not a template
      if (!value || !value.includes('{{') || !value.includes('}}')) {
        previewDiv.style.display = 'none';
        return;
      }

      // Show loading state
      previewDiv.style.display = 'block';
      previewDiv.innerHTML = '⏳ Evaluating template...';
      previewDiv.style.color = '#888';

      // Evaluate template
      const result = await this.evaluateTemplate(value);

      if (result.success) {
        previewDiv.innerHTML = `✅ Current value: <strong style="color: #00d4ff;">${result.value}</label>`;
        previewDiv.style.color = '#00ff88';
      } else {
        previewDiv.innerHTML = `❌ Error: ${result.error}`;
        previewDiv.style.color = '#ff4444';
      }
    });

    return previewDiv;
  }

  async addSlot() {
    this.log('➕', 'Add new slot...');

    // Get all climate entities
    const allClimateEntities = Object.keys(this.hass.states)
      .filter(id => id.startsWith('climate.'))
      .sort();

    // Create modal with tabs
    const modal = this.createModal(`
      <h2 style="margin-top: 0; color: #00d4ff;">➕ ${this.t('pages.config.slots.add')}</h2>

      <!-- Tabs Navigation -->
      <div class="tabs-nav">
        <button class="tab-btn active" data-tab="basic">🔧 Basic Settings</button>
        <button class="tab-btn" data-tab="overrides">🎯 Entity Overrides</button>
        <button class="tab-btn" data-tab="advanced">⚙️ Advanced</button>
      </div>

      <!-- Tab: Basic Settings -->
      <div class="tab-content active" data-tab="basic">
        <div class="mb-3">
          <label for="label" class="form-label">Label *</label>
          <input type="text" class="form-control" id="label" required
            placeholder="e.g., Night, Work Hours, Vacation">
          <div class="form-text">
            A descriptive name for this slot
          </div>
        </div>

        <div class="mb-3">
          <label for="temperature" class="form-label">Target Temperature (°C)</label>
          <input type="text" class="form-control" id="temperature"
            placeholder="e.g., 20.5 or {{ states('sensor.temp') }}">
          <div class="form-text">
            💡 Supports templates: <code style="color: #00d4ff;">{{ '{{ states("sensor.temp") }}' }}</code>
          </div>
        </div>

        <div class="alert alert-info text-center">OR (for heat_cool mode)</div>

        <div class="row g-2 mb-3">
          <div class="col-md-6">
            <label for="target_temp_low" class="form-label">Min Temperature (°C)</label>
            <input type="text" class="form-control" id="target_temp_low"
              placeholder="18 or {{ ... }}">
          </div>
          <div class="col-md-6">
            <label for="target_temp_high" class="form-label">Max Temperature (°C)</label>
            <input type="text" class="form-control" id="target_temp_high"
              placeholder="22 or {{ ... }}">
          </div>
        </div>

        <div class="mb-3">
          <label for="hvac_mode" class="form-label">HVAC Mode</label>
          <select id="hvac_mode" class="form-select">
            <option value="">-- Not set --</option>
            <option value="heat">🔥 Heat</option>
            <option value="cool">❄️ Cool</option>
            <option value="heat_cool">🔄 Heat/Cool (Auto)</option>
            <option value="auto">🤖 Auto</option>
            <option value="off">⭕ Off</option>
            <option value="dry">💨 Dry</option>
            <option value="fan_only">🌀 Fan Only</option>
          </select>
        </div>

        <div class="mb-3">
          <label for="preset_mode" class="form-label">Preset Mode</label>
          <input type="text" class="form-control" id="preset_mode"
            placeholder="e.g., eco, comfort, away">
          <div class="form-text">
            Device-specific preset (check your device capabilities)
          </div>
        </div>
      </div>

      <!-- Tab: Entity Overrides -->
      <div class="tab-content" data-tab="overrides">
        <div class="alert alert-info">
          ℹ️ Override default settings for specific entities. Disabled entities will use the default settings from Basic tab.
        </div>

        <div id="entity-overrides-container">
          ${allClimateEntities.map(entityId => `
            <div class="card mb-2" data-entity="${entityId}">
              <div class="card-header">
                <div class="form-check">
                  <input type="checkbox" class="form-check-input override-toggle" id="override-${entityId}" data-entity="${entityId}">
                  <label class="form-check-label fw-bold" for="override-${entityId}">
                    ${entityId}
                  </label>
                </div>
              </div>
              <div class="card-body entity-override-form" style="display: none;">
                <div class="row g-2">
                  <div class="col-md-6">
                    <label class="form-label">Temperature (°C)</label>
                    <input type="text" class="form-control form-control-sm override-temperature" data-entity="${entityId}"
                      placeholder="20 or {{ ... }}">
                    <div class="form-text">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </div>

                  <div class="col-md-6">
                    <label class="form-label">HVAC Mode</label>
                    <select class="form-select form-select-sm override-hvac-mode" data-entity="${entityId}">
                      <option value="">-- Use default --</option>
                      <option value="heat">🔥 Heat</option>
                      <option value="cool">❄️ Cool</option>
                      <option value="heat_cool">🔄 Heat/Cool</option>
                      <option value="auto">🤖 Auto</option>
                      <option value="off">⭕ Off</option>
                      <option value="dry">💨 Dry</option>
                      <option value="fan_only">🌀 Fan Only</option>
                    </select>
                  </div>

                  <div class="col-md-6">
                    <label class="form-label">Min Temp (°C)</label>
                    <input type="text" class="form-control form-control-sm override-temp-low" data-entity="${entityId}"
                      placeholder="18 or {{ ... }}">
                    <div class="form-text">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </div>

                  <div class="col-md-6">
                    <label class="form-label">Max Temp (°C)</label>
                    <input type="text" class="form-control form-control-sm override-temp-high" data-entity="${entityId}"
                      placeholder="22 or {{ ... }}">
                    <div class="form-text">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </div>

                  <div class="col-12">
                    <label class="form-label">Preset Mode</label>
                    <input type="text" class="form-control form-control-sm override-preset" data-entity="${entityId}"
                      placeholder="eco or {{ ... }}">
                    <div class="form-text">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Tab: Advanced -->
      <div class="tab-content" data-tab="advanced">
        <div class="mb-3">
          <label for="humidity" class="form-label">Humidity (%)</label>
          <input type="number" class="form-control" id="humidity" min="0" max="100" step="1"
            placeholder="0-100">
        </div>

        <div class="mb-3">
          <label for="aux_heat" class="form-label">Auxiliary Heat</label>
          <select id="aux_heat" class="form-select">
            <option value="">-- Not configured --</option>
            <option value="on">On</option>
            <option value="off">Off</option>
          </select>
        </div>

        <div class="mb-3">
          <label for="fan_mode" class="form-label">Fan Mode</label>
          <input type="text" class="form-control" id="fan_mode"
            placeholder="e.g., auto, low, medium, high">
        </div>

        <div class="mb-3">
          <label for="swing_mode" class="form-label">Swing Mode</label>
          <input type="text" class="form-control" id="swing_mode"
            placeholder="e.g., off, vertical, horizontal, both">
        </div>

        <div class="mb-3">
          <label class="form-label">Excluded Entities</label>
          <div class="border rounded p-2" style="max-height: 150px; overflow-y: auto;">
            ${allClimateEntities.map(ent => `
              <div class="form-check">
                <input type="checkbox" class="form-check-input" name="excluded_entities" id="excl-${ent}" value="${ent}">
                <label class="form-check-label" for="excl-${ent}">
                  ${ent}
                </label>
              </div>
            `).join('')}
          </div>
          <div class="form-text">
            These entities won't be affected by this slot at all
          </div>
        </div>
      </div>

      <div id="error-message" class="alert alert-danger" style="display: none;"></div>

      <div class="d-flex gap-2 mt-3">
        <button id="save-btn" class="btn btn-primary">💾 Save</button>
        <button id="cancel-btn" class="btn btn-secondary">❌ Cancel</button>
      </div>
    `);

    // Add tab styles to modal
    const style = document.createElement('style');
    style.textContent = `
      .tabs-nav {
        display: flex;
        gap: 5px;
        margin: 15px 0;
        border-bottom: 2px solid rgba(255,255,255,0.1);
      }
      .tab-btn {
        padding: 10px 20px;
        background: rgba(0,0,0,0.3);
        color: #888;
        border: none;
        border-bottom: 3px solid transparent;
        cursor: pointer;
        font-size: 0.95em;
        transition: all 0.3s;
        flex: 1;
      }
      .tab-btn:hover {
        background: rgba(0,212,255,0.1);
        color: #00d4ff;
      }
      .tab-btn.active {
        background: rgba(0,212,255,0.15);
        color: #00d4ff;
        border-bottom-color: #00d4ff;
        font-weight: bold;
      }
      .tab-content {
        display: none;
        padding: 20px 0;
        animation: fadeIn 0.3s;
      }
      .tab-content.active {
        display: block;
      }
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .entity-override-item {
        margin-bottom: 15px;
        padding: 12px;
        background: rgba(0,0,0,0.2);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
      }
      .entity-override-header {
        display: flex;
        align-items: center;
      }
      .entity-override-form {
        transition: all 0.3s ease;
      }
    `;
    modal.appendChild(style);

    document.body.appendChild(modal);

    // Initialize searchable selects
    this.initSelect2(modal);

    // Setup tab switching
    modal.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.dataset.tab;

        // Update tab buttons
        modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update tab content
        modal.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        modal.querySelector(`.tab-content[data-tab="${targetTab}"]`).classList.add('active');
      });
    });

    // Setup override toggle switches
    modal.querySelectorAll('.override-toggle').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const entityId = e.target.dataset.entity;
        const form = modal.querySelector(`.entity-override-item[data-entity="${entityId}"] .entity-override-form`);

        if (e.target.checked) {
          form.style.display = 'block';
        } else {
          form.style.display = 'none';
          // Clear override fields when disabled
          form.querySelectorAll('input, select').forEach(input => {
            if (input.type === 'number' || input.type === 'text') {
              input.value = '';
            } else if (input.tagName === 'SELECT') {
              input.value = '';
            }
          });
        }
      });
    });

    // Setup template preview for all template-supporting fields
    const templateFields = [
      { selector: '#temperature', id: 'preview-temperature' },
      { selector: '#target_temp_low', id: 'preview-temp-low' },
      { selector: '#target_temp_high', id: 'preview-temp-high' }
    ];

    templateFields.forEach(({ selector, id }) => {
      const field = modal.querySelector(selector);
      if (field) {
        this.addTemplatePreview(field, id);
      }
    });

    // Setup template preview for entity override fields
    modal.querySelectorAll('.override-temperature, .override-temp-low, .override-temp-high, .override-preset').forEach((input, idx) => {
      this.addTemplatePreview(input, `preview-override-${input.className}-${idx}`);
    });

    // Handle save
    modal.querySelector('#save-btn').addEventListener('click', async () => {
      try {
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.style.display = 'none';

        const label = modal.querySelector('#label').value.trim();
        if (!label) {
          errorDiv.textContent = 'Label is required';
          errorDiv.style.display = 'block';
          return;
        }

        // Build climate payload
        const payload = {};

        const temperature = modal.querySelector('#temperature').value;
        const tempLow = modal.querySelector('#target_temp_low').value;
        const tempHigh = modal.querySelector('#target_temp_high').value;
        const hvacMode = modal.querySelector('#hvac_mode').value;
        const presetMode = modal.querySelector('#preset_mode').value;
        const humidity = modal.querySelector('#humidity').value;
        const auxHeat = modal.querySelector('#aux_heat').value;
        const fanMode = modal.querySelector('#fan_mode')?.value;
        const swingMode = modal.querySelector('#swing_mode')?.value;

        // Temperature validation (supports templates)
        const tempResult = this.parseTemplateOrNumber(temperature, 'Temperature');
        const tempLowResult = this.parseTemplateOrNumber(tempLow, 'Min temperature');
        const tempHighResult = this.parseTemplateOrNumber(tempHigh, 'Max temperature');

        if (!tempResult.valid) {
          errorDiv.textContent = tempResult.error;
          errorDiv.style.display = 'block';
          return;
        }
        if (!tempLowResult.valid) {
          errorDiv.textContent = tempLowResult.error;
          errorDiv.style.display = 'block';
          return;
        }
        if (!tempHighResult.valid) {
          errorDiv.textContent = tempHighResult.error;
          errorDiv.style.display = 'block';
          return;
        }

        if (tempResult.value && (tempLowResult.value || tempHighResult.value)) {
          errorDiv.textContent = 'Cannot use both single temperature and temperature range';
          errorDiv.style.display = 'block';
          return;
        }

        if (tempResult.value !== null) {
          payload.temperature = tempResult.value;
        }

        if (tempLowResult.value !== null) {
          payload.target_temp_low = tempLowResult.value;
        }

        if (tempHighResult.value !== null) {
          payload.target_temp_high = tempHighResult.value;
        }

        // Validate range only if both are static numbers
        if (tempLowResult.value !== null && tempHighResult.value !== null &&
            !tempLowResult.isTemplate && !tempHighResult.isTemplate) {
          if (tempLowResult.value >= tempHighResult.value) {
            errorDiv.textContent = 'Min temperature must be lower than max temperature';
            errorDiv.style.display = 'block';
            return;
          }
        }

        if (hvacMode) payload.hvac_mode = hvacMode;
        if (presetMode) payload.preset_mode = presetMode;

        if (humidity) {
          const hum = parseInt(humidity);
          if (hum < 0 || hum > 100) {
            errorDiv.textContent = 'Humidity must be between 0 and 100%';
            errorDiv.style.display = 'block';
            return;
          }
          payload.humidity = hum;
        }

        if (auxHeat === 'on') payload.aux_heat = true;
        else if (auxHeat === 'off') payload.aux_heat = false;

        if (fanMode) payload.fan_mode = fanMode;
        if (swingMode) payload.swing_mode = swingMode;

        // Check at least one climate setting
        if (Object.keys(payload).length === 0) {
          errorDiv.textContent = 'Please configure at least one climate setting in Basic Settings tab';
          errorDiv.style.display = 'block';
          return;
        }

        // Collect entity_overrides
        const entityOverrides = {};
        modal.querySelectorAll('.override-toggle:checked').forEach(checkbox => {
          const entityId = checkbox.dataset.entity;
          const overridePayload = {};

          const overrideTemp = modal.querySelector(`.override-temperature[data-entity="${entityId}"]`)?.value;
          const overrideTempLow = modal.querySelector(`.override-temp-low[data-entity="${entityId}"]`)?.value;
          const overrideTempHigh = modal.querySelector(`.override-temp-high[data-entity="${entityId}"]`)?.value;
          const overrideHvac = modal.querySelector(`.override-hvac-mode[data-entity="${entityId}"]`)?.value;
          const overridePreset = modal.querySelector(`.override-preset[data-entity="${entityId}"]`)?.value;

          // Support templates in entity overrides
          const overrideTempResult = this.parseTemplateOrNumber(overrideTemp, 'Override temperature');
          const overrideTempLowResult = this.parseTemplateOrNumber(overrideTempLow, 'Override min temp');
          const overrideTempHighResult = this.parseTemplateOrNumber(overrideTempHigh, 'Override max temp');

          if (overrideTempResult.valid && overrideTempResult.value !== null) {
            overridePayload.temperature = overrideTempResult.value;
          }

          if (overrideTempLowResult.valid && overrideTempLowResult.value !== null) {
            overridePayload.target_temp_low = overrideTempLowResult.value;
          }

          if (overrideTempHighResult.valid && overrideTempHighResult.value !== null) {
            overridePayload.target_temp_high = overrideTempHighResult.value;
          }

          if (overrideHvac) overridePayload.hvac_mode = overrideHvac;
          if (overridePreset) overridePayload.preset_mode = overridePreset;

          // Only add to entity_overrides if at least one field is set
          if (Object.keys(overridePayload).length > 0) {
            entityOverrides[entityId] = overridePayload;
          }
        });

        // Get excluded entities
        const excludedEntities = Array.from(modal.querySelectorAll('input[name="excluded_entities"]:checked'))
          .map(cb => cb.value);

        this.log('💾', 'Creating new slot...', { label, payload, entityOverrides, excludedEntities });

        // Call service
        const serviceData = {
          label: label,
          default_climate_payload: payload,
        };

        if (Object.keys(entityOverrides).length > 0) {
          serviceData.entity_overrides = entityOverrides;
        }

        if (excludedEntities.length > 0) {
          serviceData.excluded_entities = excludedEntities;
        }

        await this.hass.callService('climate_control_calendar', 'add_slot', serviceData);

        this.log('✅', 'Slot created successfully');

        // Close modal
        document.body.removeChild(modal);

        // Refresh data
        await this.manualRefresh();

      } catch (error) {
        this.log('❌', 'Failed to create slot', { error: error.message });
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
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

  createModal(content) {
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
      overflow-y: auto;
      padding: 20px;
    `;

    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      padding: 30px;
      border-radius: 12px;
      max-width: 700px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      border: 1px solid rgba(255, 255, 255, 0.2);
      margin: auto;
    `;
    modalContent.innerHTML = content;

    // Add button styles
    const style = document.createElement('style');
    style.textContent = `
      .modal-btn {
        flex: 1;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 1em;
        border: 1px solid;
        transition: all 0.2s;
      }
      .modal-btn-primary {
        background: rgba(0, 212, 255, 0.2);
        color: #00d4ff;
        border-color: #00d4ff;
      }
      .modal-btn-primary:hover {
        background: rgba(0, 212, 255, 0.4);
      }
      .modal-btn-secondary {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border-color: rgba(255, 255, 255, 0.2);
      }
      .modal-btn-secondary:hover {
        background: rgba(255, 255, 255, 0.2);
      }
    `;
    modalContent.appendChild(style);

    modal.appendChild(modalContent);
    return modal;
  }

  // Initialize Select2 on select elements with many options
  initSelect2(container, minOptions = 5) {
    // Check if jQuery is loaded
    if (typeof this.shadowRoot.querySelector('script[src*="jquery"]') === 'undefined') {
      console.warn('jQuery not loaded, skipping Select2 initialization');
      return;
    }

    const selects = container.querySelectorAll('select');
    selects.forEach(select => {
      // Add Bootstrap class
      select.classList.add('form-select');

      // Skip if already initialized
      if (select.dataset.select2Init === 'true') {
        return;
      }

      // Skip HVAC/preset/fan/swing mode selects (few options)
      if (select.id && (select.id.includes('hvac_mode') || select.id.includes('preset_mode') ||
          select.id.includes('fan_mode') || select.id.includes('swing_mode'))) {
        return;
      }

      // Initialize Select2 only on selects with many options
      if (select.options.length >= minOptions) {
        try {
          // Use jQuery from shadow DOM
          const $ = this.shadowRoot.ownerDocument.defaultView.$;

          if ($ && $.fn && $.fn.select2) {
            $(select).select2({
              theme: 'bootstrap-5',
              width: '100%',
              dropdownParent: $(container),
              placeholder: 'Type to search...',
              allowClear: false
            });
            select.dataset.select2Init = 'true';
          }
        } catch (err) {
          console.warn('Failed to initialize Select2:', err);
        }
      }
    });
  }

  async editSlot(slotId) {
    this.log('✏️', `Edit slot: ${slotId}`);

    const slot = this.slots.find(s => s.id === slotId);
    if (!slot) {
      alert('Slot not found');
      return;
    }

    const payload = slot.default_climate_payload || slot.climate_payload || {};
    const entityOverrides = slot.entity_overrides || {};
    const excludedEntities = slot.excluded_entities || [];

    // Get all climate entities
    const allClimateEntities = Object.keys(this.hass.states)
      .filter(id => id.startsWith('climate.'))
      .sort();

    // Count bindings using this slot
    const bindingCount = this.bindings.filter(b => b.slot_id === slotId).length;

    // Create modal with tabs
    const modal = this.createModal(`
      <h2 style="margin-top: 0; color: #00d4ff;">✏️ Edit Slot</h2>
      <p style="color: #888; margin-bottom: 20px;">
        ID: ${slotId}<br>
        Used by ${bindingCount} binding${bindingCount !== 1 ? 's' : ''}
      </p>

      <!-- Tabs Navigation -->
      <div class="tabs-nav">
        <button class="tab-btn active" data-tab="basic">🔧 Basic Settings</button>
        <button class="tab-btn" data-tab="overrides">🎯 Entity Overrides</button>
        <button class="tab-btn" data-tab="advanced">⚙️ Advanced</button>
      </div>

      <!-- Tab: Basic Settings -->
      <div class="tab-content active" data-tab="basic">
        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Label *</label>
          <input type="text" class="form-control" id="label" required value="${slot.label || ''}">
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Target Temperature (°C)</label>
          <input type="text" class="form-control" id="temperature" value="${payload.temperature || ''}"
            placeholder="e.g., 20.5 or {{ states('sensor.temp') }}">
          <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
            💡 Supports templates: <code style="color: #00d4ff;">{{ '{{ states("sensor.temp") }}' }}</code>
          </div>
        </label>

        <div style="color: #00d4ff; margin: 15px 0; text-align: center;">OR (for heat_cool mode)</div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
          <label style="display: block;">
            <label class="form-label">Min Temperature (°C)</label>
            <input type="text" class="form-control" id="target_temp_low" value="${payload.target_temp_low || ''}"
              placeholder="18 or {{ ... }}">
          </label>
          <label style="display: block;">
            <label class="form-label">Max Temperature (°C)</label>
            <input type="text" class="form-control" id="target_temp_high" value="${payload.target_temp_high || ''}"
              placeholder="22 or {{ ... }}">
          </label>
        </div>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">HVAC Mode</label>
          <select id="hvac_mode">
            <option value="">-- Not set --</option>
            <option value="heat" ${payload.hvac_mode === 'heat' ? 'selected' : ''}>🔥 Heat</option>
            <option value="cool" ${payload.hvac_mode === 'cool' ? 'selected' : ''}>❄️ Cool</option>
            <option value="heat_cool" ${payload.hvac_mode === 'heat_cool' ? 'selected' : ''}>🔄 Heat/Cool (Auto)</option>
            <option value="auto" ${payload.hvac_mode === 'auto' ? 'selected' : ''}>🤖 Auto</option>
            <option value="off" ${payload.hvac_mode === 'off' ? 'selected' : ''}>⭕ Off</option>
            <option value="dry" ${payload.hvac_mode === 'dry' ? 'selected' : ''}>💨 Dry</option>
            <option value="fan_only" ${payload.hvac_mode === 'fan_only' ? 'selected' : ''}>🌀 Fan Only</option>
          </select>
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Preset Mode</label>
          <input type="text" class="form-control" id="preset_mode" value="${payload.preset_mode || ''}"
            placeholder="e.g., eco, comfort, away">
          <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
            Device-specific preset (check your device capabilities)
          </div>
        </label>
      </div>

      <!-- Tab: Entity Overrides -->
      <div class="tab-content" data-tab="overrides">
        <div style="color: #888; margin-bottom: 15px; padding: 10px; background: rgba(0,212,255,0.1); border-radius: 8px;">
          ℹ️ Override default settings for specific entities. ${Object.keys(entityOverrides).length > 0 ? `Currently ${Object.keys(entityOverrides).length} override(s) configured.` : 'Disabled entities will use default settings from Basic tab.'}
        </div>

        <div id="entity-overrides-container">
          ${allClimateEntities.map(entityId => {
            const override = entityOverrides[entityId] || {};
            const hasOverride = Object.keys(override).length > 0;
            return `
            <div class="entity-override-item" data-entity="${entityId}">
              <div class="entity-override-header">
                <label style="display: flex; align-items: center; cursor: pointer; user-select: none;">
                  <input type="checkbox" class="override-toggle" data-entity="${entityId}" ${hasOverride ? 'checked' : ''}>
                  <span style="font-weight: bold;">${entityId}</span>
                  ${hasOverride ? '<span style="margin-left: 10px; color: #00d4ff; font-size: 0.9em;">✓ Customized</span>' : ''}
                </label>
              </div>
              <div class="entity-override-form" style="display: ${hasOverride ? 'block' : 'none'}; margin-top: 10px; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 8px; border-left: 3px solid #00d4ff;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                  <label style="display: block;">
                    <label class="form-label">Temperature (°C)</label>
                    <input type="text" class="form-control" class="override-temperature" data-entity="${entityId}" value="${override.temperature || ''}"
                      placeholder="20 or {{ ... }}">
                    <div style="color: #888; font-size: 0.75em; margin-top: 3px;">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </label>

                  <label style="display: block;">
                    <label class="form-label">HVAC Mode</label>
                    <select class="override-hvac-mode" data-entity="${entityId}">
                      <option value="">-- Use default --</option>
                      <option value="heat" ${override.hvac_mode === 'heat' ? 'selected' : ''}>🔥 Heat</option>
                      <option value="cool" ${override.hvac_mode === 'cool' ? 'selected' : ''}>❄️ Cool</option>
                      <option value="heat_cool" ${override.hvac_mode === 'heat_cool' ? 'selected' : ''}>🔄 Heat/Cool</option>
                      <option value="auto" ${override.hvac_mode === 'auto' ? 'selected' : ''}>🤖 Auto</option>
                      <option value="off" ${override.hvac_mode === 'off' ? 'selected' : ''}>⭕ Off</option>
                      <option value="dry" ${override.hvac_mode === 'dry' ? 'selected' : ''}>💨 Dry</option>
                      <option value="fan_only" ${override.hvac_mode === 'fan_only' ? 'selected' : ''}>🌀 Fan Only</option>
                    </select>
                  </label>

                  <label style="display: block;">
                    <label class="form-label">Min Temp (°C)</label>
                    <input type="text" class="form-control" class="override-temp-low" data-entity="${entityId}" value="${override.target_temp_low || ''}"
                      placeholder="18 or {{ ... }}">
                    <div style="color: #888; font-size: 0.75em; margin-top: 3px;">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </label>

                  <label style="display: block;">
                    <label class="form-label">Max Temp (°C)</label>
                    <input type="text" class="form-control" class="override-temp-high" data-entity="${entityId}" value="${override.target_temp_high || ''}"
                      placeholder="22 or {{ ... }}">
                    <div style="color: #888; font-size: 0.75em; margin-top: 3px;">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </label>

                  <label style="display: block; grid-column: 1 / -1;">
                    <label class="form-label">Preset Mode</label>
                    <input type="text" class="form-control" class="override-preset" data-entity="${entityId}" value="${override.preset_mode || ''}"
                      placeholder="eco or {{ ... }}">
                    <div style="color: #888; font-size: 0.75em; margin-top: 3px;">
                      💡 <code>{{ states(...) }}</code>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          `}).join('')}
        </div>
      </div>

      <!-- Tab: Advanced -->
      <div class="tab-content" data-tab="advanced">
        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Humidity (%)</label>
          <input type="number" class="form-control" id="humidity" min="0" max="100" step="1" value="${payload.humidity || ''}"
            placeholder="0-100">
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Auxiliary Heat</label>
          <select id="aux_heat">
            <option value="">-- Not configured --</option>
            <option value="on" ${payload.aux_heat === true ? 'selected' : ''}>On</option>
            <option value="off" ${payload.aux_heat === false ? 'selected' : ''}>Off</option>
          </select>
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Fan Mode</label>
          <input type="text" class="form-control" id="fan_mode" value="${payload.fan_mode || ''}"
            placeholder="e.g., auto, low, medium, high">
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Swing Mode</label>
          <input type="text" class="form-control" id="swing_mode" value="${payload.swing_mode || ''}"
            placeholder="e.g., off, vertical, horizontal, both">
        </label>

        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Excluded Entities</label>
          <div style="max-height: 150px; overflow-y: auto; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; margin-top: 5px; border: 1px solid rgba(255,255,255,0.2);">
            ${allClimateEntities.map(ent => `
              <label style="display: block; margin: 5px 0;">
                <input type="checkbox" name="excluded_entities" value="${ent}" ${excludedEntities.includes(ent) ? 'checked' : ''}>
                ${ent}
              </label>
            `).join('')}
          </div>
          <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
            These entities won't be affected by this slot at all
          </div>
        </label>
      </div>

      <div id="error-message" style="color: #ff4444; margin: 10px 0; display: none;"></div>

      <div style="display: flex; gap: 10px; margin-top: 20px;">
        <button id="save-btn" class="btn btn-primary">💾 Save</button>
        <button id="cancel-btn" class="btn btn-secondary">❌ Cancel</button>
      </div>
    `);

    // Add tab styles
    const style = document.createElement('style');
    style.textContent = `
      .tabs-nav {
        display: flex;
        gap: 5px;
        margin: 15px 0;
        border-bottom: 2px solid rgba(255,255,255,0.1);
      }
      .tab-btn {
        padding: 10px 20px;
        background: rgba(0,0,0,0.3);
        color: #888;
        border: none;
        border-bottom: 3px solid transparent;
        cursor: pointer;
        font-size: 0.95em;
        transition: all 0.3s;
        flex: 1;
      }
      .tab-btn:hover {
        background: rgba(0,212,255,0.1);
        color: #00d4ff;
      }
      .tab-btn.active {
        background: rgba(0,212,255,0.15);
        color: #00d4ff;
        border-bottom-color: #00d4ff;
        font-weight: bold;
      }
      .tab-content {
        display: none;
        padding: 20px 0;
        animation: fadeIn 0.3s;
      }
      .tab-content.active {
        display: block;
      }
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .entity-override-item {
        margin-bottom: 15px;
        padding: 12px;
        background: rgba(0,0,0,0.2);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
      }
      .entity-override-header {
        display: flex;
        align-items: center;
      }
      .entity-override-form {
        transition: all 0.3s ease;
      }
    `;
    modal.appendChild(style);

    document.body.appendChild(modal);

    // Initialize searchable selects
    this.initSelect2(modal);

    // Setup tab switching
    modal.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.dataset.tab;

        // Update tab buttons
        modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update tab content
        modal.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        modal.querySelector(`.tab-content[data-tab="${targetTab}"]`).classList.add('active');
      });
    });

    // Setup override toggle switches
    modal.querySelectorAll('.override-toggle').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const entityId = e.target.dataset.entity;
        const form = modal.querySelector(`.entity-override-item[data-entity="${entityId}"] .entity-override-form`);

        if (e.target.checked) {
          form.style.display = 'block';
        } else {
          form.style.display = 'none';
          // Clear override fields when disabled
          form.querySelectorAll('input, select').forEach(input => {
            if (input.type === 'number' || input.type === 'text') {
              input.value = '';
            } else if (input.tagName === 'SELECT') {
              input.value = '';
            }
          });
        }
      });
    });

    // Setup template preview for all template-supporting fields
    const templateFields = [
      { selector: '#temperature', id: 'preview-temperature' },
      { selector: '#target_temp_low', id: 'preview-temp-low' },
      { selector: '#target_temp_high', id: 'preview-temp-high' }
    ];

    templateFields.forEach(({ selector, id }) => {
      const field = modal.querySelector(selector);
      if (field) {
        this.addTemplatePreview(field, id);
      }
    });

    // Setup template preview for entity override fields
    modal.querySelectorAll('.override-temperature, .override-temp-low, .override-temp-high, .override-preset').forEach((input, idx) => {
      this.addTemplatePreview(input, `preview-override-${input.className}-${idx}`);
    });

    // Handle save
    modal.querySelector('#save-btn').addEventListener('click', async () => {
      try {
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.style.display = 'none';

        const label = modal.querySelector('#label').value.trim();
        if (!label) {
          errorDiv.textContent = 'Label is required';
          errorDiv.style.display = 'block';
          return;
        }

        // Build new payload
        const newPayload = {};
        const temperature = modal.querySelector('#temperature').value;
        const tempLow = modal.querySelector('#target_temp_low').value;
        const tempHigh = modal.querySelector('#target_temp_high').value;
        const hvacMode = modal.querySelector('#hvac_mode').value;
        const presetMode = modal.querySelector('#preset_mode').value;
        const humidity = modal.querySelector('#humidity').value;
        const auxHeat = modal.querySelector('#aux_heat').value;
        const fanMode = modal.querySelector('#fan_mode')?.value;
        const swingMode = modal.querySelector('#swing_mode')?.value;

        // Temperature validation (supports templates)
        const tempResult = this.parseTemplateOrNumber(temperature, 'Temperature');
        const tempLowResult = this.parseTemplateOrNumber(tempLow, 'Min temperature');
        const tempHighResult = this.parseTemplateOrNumber(tempHigh, 'Max temperature');

        if (!tempResult.valid) {
          errorDiv.textContent = tempResult.error;
          errorDiv.style.display = 'block';
          return;
        }
        if (!tempLowResult.valid) {
          errorDiv.textContent = tempLowResult.error;
          errorDiv.style.display = 'block';
          return;
        }
        if (!tempHighResult.valid) {
          errorDiv.textContent = tempHighResult.error;
          errorDiv.style.display = 'block';
          return;
        }

        if (tempResult.value && (tempLowResult.value || tempHighResult.value)) {
          errorDiv.textContent = 'Cannot use both single temperature and temperature range';
          errorDiv.style.display = 'block';
          return;
        }

        if (tempResult.value !== null) {
          newPayload.temperature = tempResult.value;
        }

        if (tempLowResult.value !== null) {
          newPayload.target_temp_low = tempLowResult.value;
        }

        if (tempHighResult.value !== null) {
          newPayload.target_temp_high = tempHighResult.value;
        }

        // Validate range only if both are static numbers
        if (tempLowResult.value !== null && tempHighResult.value !== null &&
            !tempLowResult.isTemplate && !tempHighResult.isTemplate) {
          if (tempLowResult.value >= tempHighResult.value) {
            errorDiv.textContent = 'Min temperature must be lower than max temperature';
            errorDiv.style.display = 'block';
            return;
          }
        }

        if (hvacMode) newPayload.hvac_mode = hvacMode;
        if (presetMode) newPayload.preset_mode = presetMode;

        if (humidity) {
          const hum = parseInt(humidity);
          if (hum < 0 || hum > 100) {
            errorDiv.textContent = 'Humidity must be between 0 and 100%';
            errorDiv.style.display = 'block';
            return;
          }
          newPayload.humidity = hum;
        }

        if (auxHeat === 'on') newPayload.aux_heat = true;
        else if (auxHeat === 'off') newPayload.aux_heat = false;

        if (fanMode) newPayload.fan_mode = fanMode;
        if (swingMode) newPayload.swing_mode = swingMode;

        if (Object.keys(newPayload).length === 0) {
          errorDiv.textContent = 'Please configure at least one climate setting in Basic Settings tab';
          errorDiv.style.display = 'block';
          return;
        }

        // Collect entity_overrides
        const newEntityOverrides = {};
        modal.querySelectorAll('.override-toggle:checked').forEach(checkbox => {
          const entityId = checkbox.dataset.entity;
          const overridePayload = {};

          const overrideTemp = modal.querySelector(`.override-temperature[data-entity="${entityId}"]`)?.value;
          const overrideTempLow = modal.querySelector(`.override-temp-low[data-entity="${entityId}"]`)?.value;
          const overrideTempHigh = modal.querySelector(`.override-temp-high[data-entity="${entityId}"]`)?.value;
          const overrideHvac = modal.querySelector(`.override-hvac-mode[data-entity="${entityId}"]`)?.value;
          const overridePreset = modal.querySelector(`.override-preset[data-entity="${entityId}"]`)?.value;

          // Support templates in entity overrides
          const overrideTempResult = this.parseTemplateOrNumber(overrideTemp, 'Override temperature');
          const overrideTempLowResult = this.parseTemplateOrNumber(overrideTempLow, 'Override min temp');
          const overrideTempHighResult = this.parseTemplateOrNumber(overrideTempHigh, 'Override max temp');

          if (overrideTempResult.valid && overrideTempResult.value !== null) {
            overridePayload.temperature = overrideTempResult.value;
          }

          if (overrideTempLowResult.valid && overrideTempLowResult.value !== null) {
            overridePayload.target_temp_low = overrideTempLowResult.value;
          }

          if (overrideTempHighResult.valid && overrideTempHighResult.value !== null) {
            overridePayload.target_temp_high = overrideTempHighResult.value;
          }

          if (overrideHvac) overridePayload.hvac_mode = overrideHvac;
          if (overridePreset) overridePayload.preset_mode = overridePreset;

          // Only add to entity_overrides if at least one field is set
          if (Object.keys(overridePayload).length > 0) {
            newEntityOverrides[entityId] = overridePayload;
          }
        });

        const newExcludedEntities = Array.from(modal.querySelectorAll('input[name="excluded_entities"]:checked'))
          .map(cb => cb.value);

        this.log('💾', 'Updating slot...', { slotId, label, newPayload, newEntityOverrides, newExcludedEntities });

        // Update slot via API
        const response = await fetch('/api/climate_control_calendar/config', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            slots: this.slots.map(s => {
              if (s.id === slotId) {
                return {
                  id: slotId,
                  label: label,
                  default_climate_payload: newPayload,
                  entity_overrides: Object.keys(newEntityOverrides).length > 0 ? newEntityOverrides : undefined,
                  excluded_entities: newExcludedEntities.length > 0 ? newExcludedEntities : undefined,
                };
              }
              return s;
            })
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        this.log('✅', 'Slot updated successfully');

        // Close modal
        document.body.removeChild(modal);

        // Refresh
        await this.manualRefresh();

      } catch (error) {
        this.log('❌', 'Failed to update slot', { error: error.message });
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
      }
    });

    // Handle cancel
    modal.querySelector('#cancel-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });
  }

  showAddConditionDialog(parentModal, conditions, updateCallback) {
    // Create inner modal for condition configuration
    const conditionModal = this.createModal(`
      <h2 style="margin-top: 0; color: #00d4ff;">➕ Add Condition</h2>

      <div style="margin-bottom: 20px; padding: 10px; background: rgba(0,212,255,0.1); border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
        <span style="color: #888; font-size: 0.9em;">💡 Use Advanced Mode for complex conditions or custom JSON</span>
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
          <span style="font-weight: bold; color: #00d4ff;">Advanced Mode</span>
          <input type="checkbox" id="advanced-mode-toggle">
        </label>
      </div>

      <!-- Basic Mode Container -->
      <div id="basic-mode-container">
        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Condition Type *</label>
          <select id="condition_type">
            <option value="state">State - Check entity state</option>
            <option value="numeric_state">Numeric State - Compare numeric value</option>
            <option value="time">Time - Check time range/weekday</option>
            <option value="template">Template - Custom Jinja2 condition</option>
          </select>
        </label>

        <div id="condition-form-container"></div>
      </div>

      <!-- Advanced Mode Container -->
      <div id="advanced-mode-container" style="display: none;">
        <label style="display: block; margin-bottom: 15px;">
          <label class="form-label">Condition JSON *</label>
          <textarea class="form-control" id="condition-json" rows="8"
            placeholder='{\n  "condition": "state",\n  "entity_id": "binary_sensor.window",\n  "state": "off"\n}'></textarea>
          <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
            Enter condition as JSON. Supports all Home Assistant condition types: state, numeric_state, time, template, and, or, not, zone, device, etc.
          </div>
        </label>
      </div>

      <div id="condition-error-message" style="color: #ff4444; margin: 10px 0; display: none;"></div>

      <div style="display: flex; gap: 10px; margin-top: 20px;">
        <button id="condition-save-btn" class="btn btn-primary">✅ Add</button>
        <button id="condition-cancel-btn" class="btn btn-secondary">❌ Cancel</button>
      </div>
    `);

    conditionModal.style.zIndex = '10002'; // Higher than parent modal

    // Get all entities for selectors
    const allEntities = Object.keys(this.hass.states).sort();

    // Function to render form based on selected type
    const renderConditionForm = (type) => {
      const container = conditionModal.querySelector('#condition-form-container');

      if (type === 'state') {
        container.innerHTML = `
          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Entity *</label>
            <select id="cond_entity_id" required>
              ${allEntities.map(ent => `<option value="${ent}">${ent}</option>`).join('')}
            </select>
          </label>

          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">State *</label>
            <input type="text" class="form-control" id="cond_state" required
              placeholder="e.g., on, off, home, away">
            <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
              Example: sensor.presence = "home"
            </div>
          </label>
        `;
      } else if (type === 'numeric_state') {
        container.innerHTML = `
          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Entity *</label>
            <select id="cond_entity_id" required>
              ${allEntities.map(ent => `<option value="${ent}">${ent}</option>`).join('')}
            </select>
          </label>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <label style="display: block;">
              <label class="form-label">Above</label>
              <input type="number" class="form-control" id="cond_above" step="0.1"
                placeholder="Min value">
            </label>

            <label style="display: block;">
              <label class="form-label">Below</label>
              <input type="number" class="form-control" id="cond_below" step="0.1"
                placeholder="Max value">
            </label>
          </div>

          <div style="color: #888; font-size: 0.85em; margin-top: 10px;">
            Example: sensor.temperature above 25 and below 30
          </div>
        `;
      } else if (type === 'time') {
        container.innerHTML = `
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
            <label style="display: block;">
              <label class="form-label">After</label>
              <input type="time" id="cond_after">
            </label>

            <label style="display: block;">
              <label class="form-label">Before</label>
              <input type="time" id="cond_before">
            </label>
          </div>

          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Weekday</label>
            <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-top: 5px;">
              ${['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map(day => `
                <label style="display: flex; flex-direction: column; align-items: center; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; cursor: pointer;">
                  <input type="checkbox" name="cond_weekday" value="${day}">
                  <span style="font-size: 0.8em;">${day.toUpperCase()}</span>
                </label>
              `).join('')}
            </div>
            <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
              Leave all unchecked for any day
            </div>
          </label>

          <div style="color: #888; font-size: 0.85em; margin-top: 10px;">
            Example: Between 22:00-06:00 on Mon, Tue, Wed
          </div>
        `;
      } else if (type === 'template') {
        container.innerHTML = `
          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Template *</label>
            <textarea class="form-control" id="cond_template" required rows="4"
              placeholder="{{ states('sensor.temp') | float > 25 }}"></textarea>
            <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
              Jinja2 template that must evaluate to true<br>
              Example: <code style="color: #00d4ff;">{{ '{{ is_state("binary_sensor.workday", "on") }}' }}</code>
            </div>
          </label>
        `;
      }
    };

    // Initial render for state type
    renderConditionForm('state');

    // Update form when type changes
    conditionModal.querySelector('#condition_type').addEventListener('change', (e) => {
      renderConditionForm(e.target.value);
      // Re-initialize searchable selects after form change
      this.initSelect2(conditionModal);
    });

    document.body.appendChild(conditionModal);

    // Initialize searchable selects
    this.initSelect2(conditionModal);

    // Handle Advanced Mode toggle
    const advancedToggle = conditionModal.querySelector('#advanced-mode-toggle');
    const basicContainer = conditionModal.querySelector('#basic-mode-container');
    const advancedContainer = conditionModal.querySelector('#advanced-mode-container');

    advancedToggle.addEventListener('change', (e) => {
      if (e.target.checked) {
        basicContainer.style.display = 'none';
        advancedContainer.style.display = 'block';
      } else {
        basicContainer.style.display = 'block';
        advancedContainer.style.display = 'none';
      }
    });

    // Handle add condition
    conditionModal.querySelector('#condition-save-btn').addEventListener('click', () => {
      const errorDiv = conditionModal.querySelector('#condition-error-message');
      errorDiv.style.display = 'none';

      const isAdvancedMode = advancedToggle.checked;
      let condition;

      try {
        // Advanced Mode: Parse JSON
        if (isAdvancedMode) {
          const jsonText = conditionModal.querySelector('#condition-json')?.value?.trim();

          if (!jsonText) {
            errorDiv.textContent = 'Condition JSON is required';
            errorDiv.style.display = 'block';
            return;
          }

          try {
            condition = JSON.parse(jsonText);
          } catch (parseError) {
            errorDiv.textContent = `Invalid JSON: ${parseError.message}`;
            errorDiv.style.display = 'block';
            return;
          }

          // Validate that condition has required field
          if (!condition.condition && !condition.type) {
            errorDiv.textContent = 'Condition must have "condition" or "type" field';
            errorDiv.style.display = 'block';
            return;
          }

          // Normalize: ensure "condition" field exists
          if (!condition.condition && condition.type) {
            condition.condition = condition.type;
          }

        // Basic Mode: Use form-guided approach
        } else {
          const condType = conditionModal.querySelector('#condition_type').value;
          condition = { type: condType };

          if (condType === 'state') {
          const entityId = conditionModal.querySelector('#cond_entity_id')?.value;
          const state = conditionModal.querySelector('#cond_state')?.value?.trim();

          if (!entityId || !state) {
            errorDiv.textContent = 'Entity and state are required';
            errorDiv.style.display = 'block';
            return;
          }

          condition.entity_id = entityId;
          condition.state = state;

        } else if (condType === 'numeric_state') {
          const entityId = conditionModal.querySelector('#cond_entity_id')?.value;
          const above = conditionModal.querySelector('#cond_above')?.value;
          const below = conditionModal.querySelector('#cond_below')?.value;

          if (!entityId) {
            errorDiv.textContent = 'Entity is required';
            errorDiv.style.display = 'block';
            return;
          }

          if (!above && !below) {
            errorDiv.textContent = 'Specify at least "above" or "below"';
            errorDiv.style.display = 'block';
            return;
          }

          condition.entity_id = entityId;
          if (above) condition.above = parseFloat(above);
          if (below) condition.below = parseFloat(below);

        } else if (condType === 'time') {
          const after = conditionModal.querySelector('#cond_after')?.value;
          const before = conditionModal.querySelector('#cond_before')?.value;
          const weekdays = Array.from(conditionModal.querySelectorAll('input[name="cond_weekday"]:checked'))
            .map(cb => cb.value);

          if (!after && !before && weekdays.length === 0) {
            errorDiv.textContent = 'Specify at least time range or weekday';
            errorDiv.style.display = 'block';
            return;
          }

          if (after) condition.after = after;
          if (before) condition.before = before;
          if (weekdays.length > 0) condition.weekday = weekdays;

        } else if (condType === 'template') {
          const template = conditionModal.querySelector('#cond_template')?.value?.trim();

          if (!template) {
            errorDiv.textContent = 'Template is required';
            errorDiv.style.display = 'block';
            return;
          }

          if (!template.includes('{{') || !template.includes('}}')) {
            errorDiv.textContent = 'Template must contain {{ }} markers';
            errorDiv.style.display = 'block';
            return;
          }

          condition.value_template = template;
          }
        } // End of basic mode

        // Add condition to list
        conditions.push(condition);
        updateCallback();

        // Close condition modal
        document.body.removeChild(conditionModal);

      } catch (error) {
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
      }
    });

    // Handle cancel
    conditionModal.querySelector('#condition-cancel-btn').addEventListener('click', () => {
      document.body.removeChild(conditionModal);
    });

    // Close on backdrop click
    conditionModal.addEventListener('click', (e) => {
      if (e.target === conditionModal) {
        document.body.removeChild(conditionModal);
      }
    });
  }

  async addBinding() {
    this.log('➕', 'Add new binding...');

    if (this.slots.length === 0) {
      alert('Please create at least one slot first');
      return;
    }

    // Get climate entities for target_entities selector
    const allClimateEntities = Object.keys(this.hass.states)
      .filter(id => id.startsWith('climate.'))
      .sort();

    const modal = this.createModal(`
      <h2 class="text-primary mb-3">➕ ${this.t('pages.config.bindings.add')}</h2>

      <div>
        <div class="mb-3">
          <label for="match_type" class="form-label">Match Type *</label>
          <select id="match_type" class="form-select" required>
            <option value="summary_contains">Summary Contains</option>
            <option value="summary">Exact Summary Match</option>
            <option value="regex">Regular Expression</option>
          </select>
          <div class="form-text">
            How to match calendar events
          </div>
        </div>

        <div class="mb-3">
          <label for="match_value" class="form-label">Match Pattern *</label>
          <input type="text" class="form-control" id="match_value" required
            placeholder="e.g., vacation, work, ^Night$">
          <div class="form-text">
            Text or pattern to match in event summary
          </div>
        </div>

        <div class="mb-3">
          <label for="slot_id" class="form-label">Target Slot *</label>
          <select id="slot_id" class="form-select" required>
            ${this.slots.map(slot => `
              <option value="${slot.id}">${slot.label} (${slot.id})</option>
            `).join('')}
          </select>
          <div class="form-text">
            Which slot to activate when this pattern matches
          </div>
        </div>

        <div class="collapse-section">
          <div class="collapse-header" onclick="this.parentElement.classList.toggle('open')">
            <span>🎯 Conditions</span>
            <span class="collapse-icon">▼</span>
          </div>
          <div class="collapse-content">
            <div class="alert alert-info">
              ℹ️ Binding activates only when ALL conditions are met (AND logic). Leave empty for always active.
            </div>

            <div id="conditions-list" class="mb-3">
              <!-- Conditions will be added here dynamically -->
            </div>

            <button type="button" id="add-condition-btn" class="btn btn-outline-primary btn-sm">
              ➕ Add Condition
            </button>
          </div>
        </div>

        <div class="collapse-section">
          <div class="collapse-header" onclick="this.parentElement.classList.toggle('open')">
            <span>⚙️ Advanced Options</span>
            <span class="collapse-icon">▼</span>
          </div>
          <div class="collapse-content">
            <div class="mb-3">
              <label for="calendars" class="form-label">Calendars</label>
              <select id="calendars" class="form-select">
                <option value="*">* All Calendars</option>
                ${this.calendars.map(cal => `
                  <option value="${cal}">${cal}</option>
                `).join('')}
              </select>
              <div class="form-text">
                Which calendar(s) to monitor for this binding
              </div>
            </div>

            <div class="mb-3">
              <label for="priority" class="form-label">Priority (0-100)</label>
              <input type="number" class="form-control" id="priority" min="0" max="100" step="1"
                placeholder="Leave empty to use calendar default">
              <div class="form-text">
                Higher priority wins in conflicts (empty = use calendar default)
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Target Entities</label>
              <div class="border rounded p-2" style="max-height: 150px; overflow-y: auto;">
                ${allClimateEntities.map(ent => `
                  <div class="form-check">
                    <input type="checkbox" class="form-check-input" name="target_entities" id="add-target-${ent}" value="${ent}">
                    <label class="form-check-label" for="add-target-${ent}">
                      ${ent}
                    </label>
                  </div>
                `).join('')}
              </div>
              <div class="form-text">
                Specific entities for this binding (empty = all configured)
              </div>
            </div>
          </div>
        </div>
      </div>

      <div id="error-message" class="alert alert-danger" style="display: none;"></div>

      <div class="d-flex gap-2 mt-3">
        <button id="save-btn" class="btn btn-primary">💾 Save</button>
        <button id="cancel-btn" class="btn btn-secondary">❌ Cancel</button>
      </div>
    `);

    // Add collapse styles
    const style = document.createElement('style');
    style.textContent = `
      .collapse-section {
        margin: 15px 0;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 8px;
        overflow: hidden;
      }
      .collapse-header {
        padding: 12px 15px;
        background: rgba(0,212,255,0.1);
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        user-select: none;
      }
      .collapse-header:hover {
        background: rgba(0,212,255,0.2);
      }
      .collapse-icon {
        transition: transform 0.3s;
      }
      .collapse-section.open .collapse-icon {
        transform: rotate(180deg);
      }
      .collapse-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
        padding: 0 15px;
      }
      .collapse-section.open .collapse-content {
        max-height: 1000px;
        padding: 15px;
      }
    `;
    modal.appendChild(style);

    document.body.appendChild(modal);

    // Initialize searchable selects
    this.initSelect2(modal);

    // Track conditions for this binding
    let conditions = [];

    // Function to render a condition in the list
    const renderConditionItem = (condition, index) => {
      const conditionType = condition.type || condition.condition;
      let summary = '';

      if (conditionType === 'state') {
        summary = `${condition.entity_id} = ${condition.state}`;
      } else if (conditionType === 'numeric_state') {
        const parts = [];
        if (condition.above !== undefined) parts.push(`> ${condition.above}`);
        if (condition.below !== undefined) parts.push(`< ${condition.below}`);
        summary = `${condition.entity_id} ${parts.join(' and ')}`;
      } else if (conditionType === 'time') {
        const parts = [];
        if (condition.after) parts.push(`after ${condition.after}`);
        if (condition.before) parts.push(`before ${condition.before}`);
        if (condition.weekday) {
          const wd = Array.isArray(condition.weekday) ? condition.weekday.join(', ') : condition.weekday;
          parts.push(`on ${wd}`);
        }
        summary = parts.join(', ');
      } else if (conditionType === 'template') {
        const template = condition.value_template || '';
        summary = template.length > 40 ? template.substring(0, 37) + '...' : template;
      }

      return `
        <div class="condition-item" style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #00d4ff;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
              <div style="color: #00d4ff; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">${conditionType.replace('_', ' ').toUpperCase()}</div>
              <div style="font-size: 0.9em; color: #ddd;">${summary}</div>
            </div>
            <button type="button" class="remove-condition-btn" data-index="${index}"
              style="background: rgba(255,68,68,0.2); color: #ff4444; border: 1px solid #ff4444; padding: 6px 12px; border-radius: 4px; cursor: pointer; flex-shrink: 0; margin-left: 10px;">
              🗑️
            </button>
          </div>
        </div>
      `;
    };

    // Function to update conditions list display
    const updateConditionsList = () => {
      const conditionsList = modal.querySelector('#conditions-list');
      if (conditions.length === 0) {
        conditionsList.innerHTML = '<div style="color: #888; font-style: italic; padding: 10px;">No conditions configured (binding always active)</div>';
      } else {
        conditionsList.innerHTML = conditions.map((cond, idx) => renderConditionItem(cond, idx)).join('');

        // Attach remove handlers
        conditionsList.querySelectorAll('.remove-condition-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            conditions.splice(index, 1);
            updateConditionsList();
          });
        });
      }
    };

    // Initial render
    updateConditionsList();

    // Handle "Add Condition" button
    modal.querySelector('#add-condition-btn').addEventListener('click', () => {
      this.showAddConditionDialog(modal, conditions, updateConditionsList);
    });

    // Handle save
    modal.querySelector('#save-btn').addEventListener('click', async () => {
      try {
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.style.display = 'none';

        const matchType = modal.querySelector('#match_type').value;
        const matchValue = modal.querySelector('#match_value').value.trim();
        const slotId = modal.querySelector('#slot_id').value;
        const calendars = modal.querySelector('#calendars').value;
        const priority = modal.querySelector('#priority').value;

        if (!matchValue) {
          errorDiv.textContent = 'Match pattern is required';
          errorDiv.style.display = 'block';
          return;
        }

        const targetEntities = Array.from(modal.querySelectorAll('input[name="target_entities"]:checked'))
          .map(cb => cb.value);

        this.log('💾', 'Creating new binding...', { matchType, matchValue, slotId, calendars, priority, targetEntities, conditions });

        // Call service
        const serviceData = {
          calendars: calendars,
          match: {
            type: matchType,
            value: matchValue,
          },
          slot_id: slotId,
        };

        if (priority) {
          serviceData.priority = parseInt(priority);
        }

        if (targetEntities.length > 0) {
          serviceData.target_entities = targetEntities;
        }

        if (conditions.length > 0) {
          serviceData.conditions = conditions;
        }

        await this.hass.callService('climate_control_calendar', 'add_binding', serviceData);

        this.log('✅', 'Binding created successfully');

        // Close modal
        document.body.removeChild(modal);

        // Refresh
        await this.manualRefresh();

      } catch (error) {
        this.log('❌', 'Failed to create binding', { error: error.message });
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
      }
    });

    // Handle cancel
    modal.querySelector('#cancel-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });
  }

  async editBinding(bindingId) {
    this.log('✏️', `Edit binding: ${bindingId}`);

    const binding = this.bindings.find(b => b.id === bindingId);
    if (!binding) {
      alert('Binding not found');
      return;
    }

    const match = binding.match || {};
    const targetEntities = binding.target_entities || [];
    const allClimateEntities = Object.keys(this.hass.states)
      .filter(id => id.startsWith('climate.'))
      .sort();

    const modal = this.createModal(`
      <h2 class="text-primary mb-3">✏️ Edit Binding</h2>
      <p class="text-muted mb-3">ID: ${bindingId}</p>

      <div>
        <div class="mb-3">
          <label for="match_type" class="form-label">Match Type *</label>
          <select id="match_type" class="form-select" required>
            <option value="summary_contains" ${match.type === 'summary_contains' ? 'selected' : ''}>Summary Contains</option>
            <option value="summary" ${match.type === 'summary' ? 'selected' : ''}>Exact Summary Match</option>
            <option value="regex" ${match.type === 'regex' ? 'selected' : ''}>Regular Expression</option>
          </select>
        </div>

        <div class="mb-3">
          <label for="match_value" class="form-label">Match Pattern *</label>
          <input type="text" class="form-control" id="match_value" required value="${match.value || ''}">
        </div>

        <div class="mb-3">
          <label for="slot_id" class="form-label">Target Slot *</label>
          <select id="slot_id" class="form-select" required>
            ${this.slots.map(slot => `
              <option value="${slot.id}" ${binding.slot_id === slot.id ? 'selected' : ''}>
                ${slot.label} (${slot.id})
              </option>
            `).join('')}
          </select>
        </div>

        <div class="collapse-section ${binding.conditions && binding.conditions.length > 0 ? 'open' : ''}">
          <div class="collapse-header" onclick="this.parentElement.classList.toggle('open')">
            <span>🎯 Conditions</span>
            <span class="collapse-icon">▼</span>
          </div>
          <div class="collapse-content">
            <div class="alert alert-info">
              ℹ️ Binding activates only when ALL conditions are met (AND logic). Leave empty for always active.
            </div>

            <div id="conditions-list" class="mb-3">
              <!-- Conditions will be added here dynamically -->
            </div>

            <button type="button" id="add-condition-btn" class="btn btn-outline-primary btn-sm">
              ➕ Add Condition
            </button>
          </div>
        </div>

        <div class="collapse-section open">
          <div class="collapse-header" onclick="this.parentElement.classList.toggle('open')">
            <span>⚙️ Advanced Options</span>
            <span class="collapse-icon">▼</span>
          </div>
          <div class="collapse-content">
            <div class="mb-3">
              <label for="calendars" class="form-label">Calendars</label>
              <select id="calendars" class="form-select">
                <option value="*" ${binding.calendars === '*' ? 'selected' : ''}>* All Calendars</option>
                ${this.calendars.map(cal => `
                  <option value="${cal}" ${binding.calendars === cal ? 'selected' : ''}>
                    ${cal}
                  </option>
                `).join('')}
              </select>
            </div>

            <div class="mb-3">
              <label for="priority" class="form-label">Priority (0-100)</label>
              <input type="number" class="form-control" id="priority" min="0" max="100" step="1" value="${binding.priority !== null && binding.priority !== undefined ? binding.priority : ''}"
                placeholder="Leave empty to use calendar default">
            </div>

            <div class="mb-3">
              <label class="form-label">Target Entities</label>
              <div class="border rounded p-2" style="max-height: 150px; overflow-y: auto;">
                ${allClimateEntities.map(ent => `
                  <div class="form-check">
                    <input type="checkbox" class="form-check-input" name="target_entities" id="target-${ent}" value="${ent}" ${targetEntities.includes(ent) ? 'checked' : ''}>
                    <label class="form-check-label" for="target-${ent}">
                      ${ent}
                    </label>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div id="error-message" class="alert alert-danger" style="display: none;"></div>

      <div class="d-flex gap-2 mt-3">
        <button id="save-btn" class="btn btn-primary">💾 Save</button>
        <button id="cancel-btn" class="btn btn-secondary">❌ Cancel</button>
      </div>
    `);

    // Add collapse styles
    const style = document.createElement('style');
    style.textContent = `
      .collapse-section {
        margin: 15px 0;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 8px;
        overflow: hidden;
      }
      .collapse-header {
        padding: 12px 15px;
        background: rgba(0,212,255,0.1);
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        user-select: none;
      }
      .collapse-header:hover {
        background: rgba(0,212,255,0.2);
      }
      .collapse-icon {
        transition: transform 0.3s;
      }
      .collapse-section.open .collapse-icon {
        transform: rotate(180deg);
      }
      .collapse-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
        padding: 0 15px;
      }
      .collapse-section.open .collapse-content {
        max-height: 1000px;
        padding: 15px;
      }
    `;
    modal.appendChild(style);

    document.body.appendChild(modal);

    // Initialize searchable selects
    this.initSelect2(modal);

    // Track conditions for this binding (initialize with existing)
    let conditions = binding.conditions ? JSON.parse(JSON.stringify(binding.conditions)) : [];

    // Function to render a condition in the list (same as addBinding)
    const renderConditionItem = (condition, index) => {
      const conditionType = condition.type || condition.condition;
      let summary = '';

      if (conditionType === 'state') {
        summary = `${condition.entity_id} = ${condition.state}`;
      } else if (conditionType === 'numeric_state') {
        const parts = [];
        if (condition.above !== undefined) parts.push(`> ${condition.above}`);
        if (condition.below !== undefined) parts.push(`< ${condition.below}`);
        summary = `${condition.entity_id} ${parts.join(' and ')}`;
      } else if (conditionType === 'time') {
        const parts = [];
        if (condition.after) parts.push(`after ${condition.after}`);
        if (condition.before) parts.push(`before ${condition.before}`);
        if (condition.weekday) {
          const wd = Array.isArray(condition.weekday) ? condition.weekday.join(', ') : condition.weekday;
          parts.push(`on ${wd}`);
        }
        summary = parts.join(', ');
      } else if (conditionType === 'template') {
        const template = condition.value_template || '';
        summary = template.length > 40 ? template.substring(0, 37) + '...' : template;
      }

      return `
        <div class="condition-item" style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #00d4ff;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
              <div style="color: #00d4ff; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">${conditionType.replace('_', ' ').toUpperCase()}</div>
              <div style="font-size: 0.9em; color: #ddd;">${summary}</div>
            </div>
            <button type="button" class="remove-condition-btn" data-index="${index}"
              style="background: rgba(255,68,68,0.2); color: #ff4444; border: 1px solid #ff4444; padding: 6px 12px; border-radius: 4px; cursor: pointer; flex-shrink: 0; margin-left: 10px;">
              🗑️
            </button>
          </div>
        </div>
      `;
    };

    // Function to update conditions list display
    const updateConditionsList = () => {
      const conditionsList = modal.querySelector('#conditions-list');
      if (conditions.length === 0) {
        conditionsList.innerHTML = '<div style="color: #888; font-style: italic; padding: 10px;">No conditions configured (binding always active)</div>';
      } else {
        conditionsList.innerHTML = conditions.map((cond, idx) => renderConditionItem(cond, idx)).join('');

        // Attach remove handlers
        conditionsList.querySelectorAll('.remove-condition-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            conditions.splice(index, 1);
            updateConditionsList();
          });
        });
      }
    };

    // Initial render
    updateConditionsList();

    // Handle "Add Condition" button
    modal.querySelector('#add-condition-btn').addEventListener('click', () => {
      this.showAddConditionDialog(modal, conditions, updateConditionsList);
    });

    // Handle save
    modal.querySelector('#save-btn').addEventListener('click', async () => {
      try {
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.style.display = 'none';

        const matchType = modal.querySelector('#match_type').value;
        const matchValue = modal.querySelector('#match_value').value.trim();
        const slotId = modal.querySelector('#slot_id').value;
        const calendars = modal.querySelector('#calendars').value;
        const priority = modal.querySelector('#priority').value;

        if (!matchValue) {
          errorDiv.textContent = 'Match pattern is required';
          errorDiv.style.display = 'block';
          return;
        }

        const newTargetEntities = Array.from(modal.querySelectorAll('input[name="target_entities"]:checked'))
          .map(cb => cb.value);

        this.log('💾', 'Updating binding...', { bindingId, matchType, matchValue, slotId, calendars, priority, newTargetEntities, conditions });

        // Update binding in list
        const response = await fetch('/api/climate_control_calendar/config', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.hass.auth.data.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            bindings: this.bindings.map(b => {
              if (b.id === bindingId) {
                const updated = {
                  id: bindingId,
                  calendars: calendars,
                  match: {
                    type: matchType,
                    value: matchValue,
                  },
                  slot_id: slotId,
                  priority: priority ? parseInt(priority) : null,
                  target_entities: newTargetEntities.length > 0 ? newTargetEntities : null,
                };

                // Add conditions if present
                if (conditions.length > 0) {
                  updated.conditions = conditions;
                }

                return updated;
              }
              return b;
            })
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        this.log('✅', 'Binding updated successfully');

        // Close modal
        document.body.removeChild(modal);

        // Refresh
        await this.manualRefresh();

      } catch (error) {
        this.log('❌', 'Failed to update binding', { error: error.message });
        const errorDiv = modal.querySelector('#error-message');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
      }
    });

    // Handle cancel
    modal.querySelector('#cancel-btn').addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });
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
          <button class="btn btn-primary btn-sm" data-action="edit-basic-config">✏️ Edit</button>
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
        <div class="list-group-item">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <h5 class="mb-2">${slot.label || 'Unnamed Slot'}</h5>
              <div class="mb-2">
                <span class="badge bg-primary me-1">🌡️ ${temp}°C</span>
                <span class="badge bg-info me-1">🔥 ${mode}</span>
                ${payload.preset_mode ? `<span class="badge bg-secondary me-1">⚙️ ${payload.preset_mode}</span>` : ''}
                ${payload.humidity ? `<span class="badge bg-info me-1">💧 ${payload.humidity}%</span>` : ''}
              </div>
            </div>
            <div class="btn-group">
              <button class="btn btn-sm btn-outline-primary" data-action="edit-slot" data-id="${slot.id}">✏️ Edit</button>
              <button class="btn btn-sm btn-outline-danger" data-action="delete-slot" data-id="${slot.id}">🗑️ Delete</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h2 class="h5 mb-0">🎯 Slots (${this.slots.length})</h2>
          <button class="btn btn-primary btn-sm" data-action="add-slot">➕ Add Slot</button>
        </div>
        ${this.slots.length === 0 ? `
          <div class="card-body text-center text-muted">
            <div class="fs-1">📭</div>
            <p>No slots configured yet</p>
            <p class="text-secondary">Click "Add Slot" to create one</p>
          </div>
        ` : `<div class="list-group list-group-flush">${slotsList}</div>`}
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
        <div class="list-group-item">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <h5 class="mb-2">${matchValue || 'Unnamed'}</h5>
              <div class="mb-2">
                <span class="badge bg-primary me-1">📋 ${matchType}</span>
                <span class="badge bg-success me-1">🎯 ${slotLabel}</span>
                <span class="badge bg-warning me-1">⚡ Priority: ${priority}</span>
              </div>
            </div>
            <div class="btn-group">
              <button class="btn btn-sm btn-outline-primary" data-action="edit-binding" data-id="${binding.id}">✏️ Edit</button>
              <button class="btn btn-sm btn-outline-danger" data-action="delete-binding" data-id="${binding.id}">🗑️ Delete</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h2 class="h5 mb-0">🔗 Bindings (${this.bindings.length})</h2>
          <button class="btn btn-primary btn-sm" data-action="add-binding">➕ Add Binding</button>
        </div>
        ${this.bindings.length === 0 ? `
          <div class="card-body text-center text-muted">
            <div class="fs-1">📭</div>
            <p>No bindings configured yet</p>
            <p class="text-secondary">Click "Add Binding" to create one</p>
          </div>
        ` : `<div class="list-group list-group-flush">${bindingsList}</div>`}
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
            <label class="form-label">Enable this calendar</label>
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              When disabled, events from this calendar will be ignored
            </div>
          </label>

          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Default Priority (0-100)</label>
            <input type="number" class="form-control" id="priority" min="0" max="100" value="${currentConfig.default_priority || 0}">
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              Higher priority calendars take precedence in conflicts
            </div>
          </label>

          <label style="display: block; margin-bottom: 15px;">
            <label class="form-label">Description (optional)</label>
            <textarea class="form-control" id="description" rows="3"
            >${currentConfig.description || ''}</textarea>
            <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
              A note to help you remember what this calendar is for
            </div>
          </label>

          <div style="background: rgba(0,212,255,0.1); padding: 10px; border-radius: 8px; border-left: 3px solid #00d4ff;">
            <label class="form-label">📊 Stats:</label> ${bindingCount} binding${bindingCount !== 1 ? 's' : ''} using this calendar
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
        <div class="card mb-3">
          <div class="card-header">
            <h2 class="h5 mb-0">📅 Calendars</h2>
          </div>
          <div class="card-body text-center text-muted">
            <div class="fs-1">📭</div>
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
        <div class="list-group-item">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <h5 class="mb-2">${cal} ${!enabled ? '<span class="badge bg-secondary">Disabled</span>' : ''}</h5>
              <div class="mb-2">
                <span class="badge ${enabled ? 'bg-success' : 'bg-danger'} me-1">${enabled ? '✅ Enabled' : '❌ Disabled'}</span>
                <span class="badge bg-warning me-1">⚡ Priority: ${priority}</span>
                <span class="badge bg-info me-1">🔗 ${bindingCount} binding${bindingCount !== 1 ? 's' : ''}</span>
              </div>
              ${description ? `<div class="text-muted fst-italic small">${description}</div>` : ''}
            </div>
            <button class="btn btn-sm btn-outline-primary" data-action="edit-calendar" data-id="${cal}">✏️ Edit</button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="card mb-3">
        <div class="card-header">
          <h2 class="h5 mb-0">📅 Calendars (${this.calendars.length})</h2>
        </div>
        <div class="list-group list-group-flush">
          ${calendarsList}
        </div>
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
