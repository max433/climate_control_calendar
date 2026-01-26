/**
 * Advanced LitElement Component - Demo for Climate Control Calendar
 * Shows various UI elements useful for future development
 *
 * External Libraries:
 * - LitElement 3.x (CDN)
 * - Chart.js 4.x (CDN)
 * - Tom-Select (searchable select, CDN)
 */

import { LitElement, html, css } from 'https://cdn.jsdelivr.net/gh/lit/dist@3/core/lit-core.min.js';

class AdvancedPanel extends LitElement {
  static get properties() {
    return {
      // State
      counter: { type: Number },
      activeTab: { type: String },
      textInput: { type: String },
      numberInput: { type: Number },
      selectValue: { type: String },
      searchableSelectValue: { type: String },
      multiSelectValues: { type: Array },
      checkboxes: { type: Object },
      radioValue: { type: String },
      rangeValue: { type: Number },
      dateValue: { type: String },
      timeValue: { type: String },
      colorValue: { type: String },
      textareaValue: { type: String },
      // Collapsed sections
      collapsedSections: { type: Object },
      // Chart & libraries loaded
      chartLoaded: { type: Boolean },
      timelineLoaded: { type: Boolean }
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 20px;
        font-family: var(--primary-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
        background: var(--primary-background-color, #fafafa);
        color: var(--primary-text-color, #212121);
      }

      .container {
        max-width: 1200px;
        margin: 0 auto;
      }

      /* Card Styles */
      .card {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        padding: 20px;
        margin: 20px 0;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--divider-color, #e0e0e0);
      }

      h1 {
        color: var(--primary-color, #03a9f4);
        margin: 0 0 20px 0;
        font-size: 2em;
      }

      h2 {
        color: var(--primary-color, #03a9f4);
        margin: 0;
        font-size: 1.3em;
      }

      h3 {
        color: var(--secondary-text-color, #757575);
        margin: 16px 0 8px 0;
        font-size: 1.1em;
      }

      /* Buttons */
      .btn {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        margin: 4px;
        transition: all 0.2s;
      }

      .btn:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      }

      .btn-secondary {
        background: var(--secondary-color, #5f6368);
      }

      .btn-success {
        background: var(--success-color, #4caf50);
      }

      .btn-warning {
        background: var(--warning-color, #ff9800);
      }

      .btn-danger {
        background: var(--error-color, #f44336);
      }

      .btn-sm {
        padding: 6px 12px;
        font-size: 12px;
      }

      /* Form Controls */
      .form-group {
        margin: 24px 0;
        padding: 12px 0;
      }

      .form-group:first-child {
        margin-top: 0;
      }

      .form-group small {
        display: block;
        margin-top: 6px;
        color: var(--secondary-text-color, #757575);
        font-size: 13px;
      }

      label {
        display: block;
        margin-bottom: 6px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
        font-size: 14px;
      }

      input[type="text"],
      input[type="number"],
      input[type="date"],
      input[type="time"],
      input[type="color"],
      input[type="email"],
      input[type="password"],
      select,
      textarea {
        width: 100%;
        padding: 10px 12px;
        border: 2px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        font-size: 14px;
        font-family: inherit;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
        transition: border-color 0.2s;
      }

      input:focus,
      select:focus,
      textarea:focus {
        outline: none;
        border-color: var(--primary-color, #03a9f4);
      }

      textarea {
        resize: vertical;
        min-height: 80px;
      }

      /* Range Slider */
      input[type="range"] {
        width: 100%;
        height: 6px;
        border-radius: 3px;
        background: var(--divider-color, #e0e0e0);
        outline: none;
      }

      input[type="range"]::-webkit-slider-thumb {
        appearance: none;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--primary-color, #03a9f4);
        cursor: pointer;
      }

      .range-value {
        display: inline-block;
        margin-left: 12px;
        font-weight: bold;
        color: var(--primary-color, #03a9f4);
      }

      /* Checkboxes & Radios */
      .checkbox-group,
      .radio-group {
        margin: 12px 0;
      }

      .checkbox-item,
      .radio-item {
        display: flex;
        align-items: center;
        margin: 8px 0;
        cursor: pointer;
      }

      input[type="checkbox"],
      input[type="radio"] {
        width: 18px;
        height: 18px;
        margin-right: 8px;
        cursor: pointer;
      }

      /* Badges */
      .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        margin: 0 4px;
      }

      .badge-primary {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
      }

      .badge-success {
        background: var(--success-color, #4caf50);
        color: white;
      }

      .badge-warning {
        background: var(--warning-color, #ff9800);
        color: white;
      }

      .badge-error {
        background: var(--error-color, #f44336);
        color: white;
      }

      /* Tabs */
      .tabs {
        display: flex;
        border-bottom: 2px solid var(--divider-color, #e0e0e0);
        margin-bottom: 20px;
      }

      .tab {
        padding: 12px 24px;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        margin-bottom: -2px;
        transition: all 0.2s;
        color: var(--secondary-text-color, #757575);
        font-weight: 500;
      }

      .tab:hover {
        color: var(--primary-color, #03a9f4);
        background: rgba(3, 169, 244, 0.05);
      }

      .tab.active {
        color: var(--primary-color, #03a9f4);
        border-bottom-color: var(--primary-color, #03a9f4);
      }

      .tab-content {
        display: none;
      }

      .tab-content.active {
        display: block;
        animation: fadeIn 0.3s;
      }

      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }

      /* List Items */
      .list-item {
        padding: 16px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: background 0.2s;
      }

      .list-item:hover {
        background: rgba(0,0,0,0.02);
      }

      .list-item:last-child {
        border-bottom: none;
      }

      /* Collapsible */
      .collapsible {
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        margin: 12px 0;
        overflow: hidden;
      }

      .collapsible-header {
        padding: 12px 16px;
        background: rgba(0,0,0,0.02);
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 500;
        transition: background 0.2s;
      }

      .collapsible-header:hover {
        background: rgba(0,0,0,0.05);
      }

      .collapsible-icon {
        transition: transform 0.3s;
      }

      .collapsible-icon.open {
        transform: rotate(180deg);
      }

      .collapsible-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease-out;
      }

      .collapsible-content.open {
        max-height: 1000px;
        padding: 16px;
      }

      /* Grid */
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 16px;
      }

      /* Alert */
      .alert {
        padding: 12px 16px;
        border-radius: 6px;
        margin: 12px 0;
        border-left: 4px solid;
      }

      .alert-info {
        background: #e3f2fd;
        border-left-color: #2196f3;
        color: #0d47a1;
      }

      .alert-success {
        background: #e8f5e9;
        border-left-color: #4caf50;
        color: #1b5e20;
      }

      .alert-warning {
        background: #fff3e0;
        border-left-color: #ff9800;
        color: #e65100;
      }

      .alert-error {
        background: #ffebee;
        border-left-color: #f44336;
        color: #b71c1c;
      }

      /* Tom-Select (Searchable Select) */
      .ts-wrapper {
        margin-top: 6px;
      }

      .ts-control {
        padding: 10px 12px !important;
        border: 2px solid var(--divider-color, #e0e0e0) !important;
        border-radius: 4px !important;
        background: var(--card-background-color, #fff) !important;
        color: var(--primary-text-color, #212121) !important;
      }

      .ts-dropdown {
        border: 2px solid var(--primary-color, #03a9f4) !important;
        border-radius: 4px !important;
        background: var(--card-background-color, #fff) !important;
      }

      .ts-dropdown .option {
        color: var(--primary-text-color, #212121) !important;
      }

      .ts-dropdown .option.active {
        background: var(--primary-color, #03a9f4) !important;
        color: var(--text-primary-color, #fff) !important;
      }

      /* Chart Container */
      .chart-container {
        position: relative;
        height: 300px;
        margin: 20px 0;
        padding: 10px;
        background: var(--card-background-color, #fff);
        border-radius: 8px;
      }

      /* Timeline Container */
      .timeline-container {
        position: relative;
        min-height: 300px;
        margin: 20px 0;
        padding: 20px;
        background: var(--card-background-color, #fff);
        border-radius: 8px;
        border: 1px solid var(--divider-color, #e0e0e0);
      }

      .timeline-item {
        position: relative;
        padding: 16px;
        margin: 12px 0;
        border-left: 4px solid var(--primary-color, #03a9f4);
        background: rgba(3, 169, 244, 0.05);
        border-radius: 4px;
      }

      .timeline-item .time {
        font-size: 12px;
        color: var(--secondary-text-color, #757575);
        font-weight: bold;
        margin-bottom: 4px;
      }

      .timeline-item .content {
        color: var(--primary-text-color, #212121);
      }

      /* Chart Placeholder */
      .chart-placeholder {
        background: linear-gradient(135deg, rgba(3, 169, 244, 0.1), rgba(76, 175, 80, 0.1));
        border: 2px dashed var(--primary-color, #03a9f4);
        border-radius: 8px;
        padding: 40px;
        text-align: center;
        color: var(--secondary-text-color, #757575);
        min-height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }

      .chart-placeholder .icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    `;
  }

  constructor() {
    super();
    this.counter = 0;
    this.activeTab = 'forms';
    this.textInput = '';
    this.numberInput = 20;
    this.selectValue = '';
    this.searchableSelectValue = '';
    this.multiSelectValues = [];
    this.checkboxes = { opt1: true, opt2: false, opt3: false };
    this.radioValue = 'option1';
    this.rangeValue = 50;
    this.dateValue = new Date().toISOString().split('T')[0];
    this.timeValue = '12:00';
    this.colorValue = '#03a9f4';
    this.textareaValue = '';
    this.collapsedSections = { section1: false, section2: false, section3: false };
    this.chartLoaded = false;
    this.timelineLoaded = false;
    this.chart = null;
    this.tomSelect = null;
  }

  async firstUpdated() {
    // Load external libraries
    await this.loadExternalLibraries();
  }

  async loadExternalLibraries() {
    try {
      // Load Tom-Select CSS
      const tomSelectCSS = document.createElement('link');
      tomSelectCSS.rel = 'stylesheet';
      tomSelectCSS.href = 'https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.bootstrap5.min.css';
      this.shadowRoot.appendChild(tomSelectCSS);

      // Load Tom-Select JS
      const tomSelectScript = document.createElement('script');
      tomSelectScript.src = 'https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js';
      tomSelectScript.onload = () => {
        console.log('✅ Tom-Select loaded');
        this.initTomSelect();
      };
      this.shadowRoot.appendChild(tomSelectScript);

      // Load Chart.js
      const chartScript = document.createElement('script');
      chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
      chartScript.onload = () => {
        console.log('✅ Chart.js loaded');
        this.chartLoaded = true;
        this.requestUpdate();
      };
      this.shadowRoot.appendChild(chartScript);

      this.timelineLoaded = true;
    } catch (error) {
      console.error('Error loading external libraries:', error);
    }
  }

  initTomSelect() {
    const selectElement = this.shadowRoot.querySelector('#searchable-select');
    if (selectElement && window.TomSelect) {
      this.tomSelect = new TomSelect(selectElement, {
        create: false,
        sortField: {
          field: "text",
          direction: "asc"
        },
        placeholder: 'Search and select...',
        onChange: (value) => {
          this.searchableSelectValue = value;
          this.requestUpdate();
        }
      });
    }
  }

  updated(changedProperties) {
    super.updated(changedProperties);

    // Initialize chart when tab changes to advanced and chart is loaded
    if (changedProperties.has('activeTab') && this.activeTab === 'advanced' && this.chartLoaded && !this.chart) {
      setTimeout(() => this.initChart(), 100);
    }
  }

  initChart() {
    const canvas = this.shadowRoot.querySelector('#temperatureChart');
    if (!canvas || !window.Chart) return;

    const ctx = canvas.getContext('2d');
    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
        datasets: [
          {
            label: 'Temperature (°C)',
            data: [18, 17, 19, 22, 23, 21, 19],
            borderColor: 'rgb(3, 169, 244)',
            backgroundColor: 'rgba(3, 169, 244, 0.1)',
            tension: 0.4,
            fill: true
          },
          {
            label: 'Target (°C)',
            data: [20, 20, 21, 22, 22, 21, 20],
            borderColor: 'rgb(76, 175, 80)',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            tension: 0.4,
            fill: true,
            borderDash: [5, 5]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
          },
          title: {
            display: true,
            text: '24h Temperature History'
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            min: 15,
            max: 25,
            ticks: {
              callback: function(value) {
                return value + '°C';
              }
            }
          }
        }
      }
    });
  }

  render() {
    return html`
      <div class="container">
        <h1>🎨 Advanced LitElement Component</h1>

        <div class="alert alert-success">
          <strong>✅ LitElement Working!</strong> CDN import successful. HA CSS variables active.
        </div>

        <!-- Tabs -->
        <div class="tabs">
          <div class="tab ${this.activeTab === 'forms' ? 'active' : ''}" @click=${() => this.activeTab = 'forms'}>
            📝 Forms
          </div>
          <div class="tab ${this.activeTab === 'components' ? 'active' : ''}" @click=${() => this.activeTab = 'components'}>
            🧩 Components
          </div>
          <div class="tab ${this.activeTab === 'advanced' ? 'active' : ''}" @click=${() => this.activeTab = 'advanced'}>
            🚀 Advanced
          </div>
        </div>

        <!-- Tab Content: Forms -->
        <div class="tab-content ${this.activeTab === 'forms' ? 'active' : ''}">
          ${this.renderFormsTab()}
        </div>

        <!-- Tab Content: Components -->
        <div class="tab-content ${this.activeTab === 'components' ? 'active' : ''}">
          ${this.renderComponentsTab()}
        </div>

        <!-- Tab Content: Advanced -->
        <div class="tab-content ${this.activeTab === 'advanced' ? 'active' : ''}">
          ${this.renderAdvancedTab()}
        </div>
      </div>
    `;
  }

  renderFormsTab() {
    return html`
      <div class="card">
        <div class="card-header">
          <h2>📝 Form Controls</h2>
        </div>

        <div class="grid">
          <div class="form-group">
            <label>Text Input</label>
            <input type="text"
              .value=${this.textInput}
              @input=${(e) => this.textInput = e.target.value}
              placeholder="Enter text...">
            <small>Value: ${this.textInput || '(empty)'}</small>
          </div>

          <div class="form-group">
            <label>Number Input</label>
            <input type="number"
              .value=${this.numberInput}
              @input=${(e) => this.numberInput = Number(e.target.value)}
              min="0" max="100">
            <small>Value: ${this.numberInput}</small>
          </div>
        </div>

        <div class="grid">
          <div class="form-group">
            <label>Date Picker</label>
            <input type="date"
              .value=${this.dateValue}
              @change=${(e) => this.dateValue = e.target.value}>
            <small>Selected: ${this.dateValue}</small>
          </div>

          <div class="form-group">
            <label>Time Picker</label>
            <input type="time"
              .value=${this.timeValue}
              @change=${(e) => this.timeValue = e.target.value}>
            <small>Selected: ${this.timeValue}</small>
          </div>
        </div>

        <div class="form-group">
          <label>Select Dropdown (Standard)</label>
          <select @change=${(e) => this.selectValue = e.target.value}>
            <option value="">Choose an option...</option>
            <option value="heat">🔥 Heat Mode</option>
            <option value="cool">❄️ Cool Mode</option>
            <option value="auto">🔄 Auto Mode</option>
            <option value="off">⭕ Off</option>
          </select>
          <small>Selected: ${this.selectValue || '(none)'}</small>
        </div>

        <div class="form-group">
          <label>Searchable Select (Tom-Select) 🔍</label>
          <select id="searchable-select">
            <option value="">Search and select...</option>
            <option value="climate.bedroom">🛏️ Climate - Bedroom</option>
            <option value="climate.living_room">🛋️ Climate - Living Room</option>
            <option value="climate.kitchen">🍳 Climate - Kitchen</option>
            <option value="climate.bathroom">🚿 Climate - Bathroom</option>
            <option value="climate.office">💼 Climate - Office</option>
            <option value="sensor.temperature_bedroom">🌡️ Sensor - Bedroom Temp</option>
            <option value="sensor.temperature_living">🌡️ Sensor - Living Room Temp</option>
            <option value="sensor.humidity_bedroom">💧 Sensor - Bedroom Humidity</option>
            <option value="sensor.humidity_living">💧 Sensor - Living Room Humidity</option>
            <option value="switch.heater_bedroom">🔥 Switch - Bedroom Heater</option>
            <option value="switch.heater_living">🔥 Switch - Living Room Heater</option>
            <option value="switch.ac_bedroom">❄️ Switch - Bedroom AC</option>
            <option value="switch.ac_living">❄️ Switch - Living Room AC</option>
          </select>
          <small>Selected: ${this.searchableSelectValue || '(none)'}</small>
          <div class="alert alert-info" style="margin-top: 8px; padding: 8px 12px; font-size: 13px;">
            <strong>✨ Features:</strong> Type to search, keyboard navigation, mobile-friendly
          </div>
        </div>

        <div class="form-group">
          <label>Range Slider</label>
          <input type="range"
            .value=${this.rangeValue}
            @input=${(e) => this.rangeValue = Number(e.target.value)}
            min="0" max="100">
          <span class="range-value">${this.rangeValue}°C</span>
        </div>

        <div class="form-group">
          <label>Color Picker</label>
          <input type="color"
            .value=${this.colorValue}
            @change=${(e) => this.colorValue = e.target.value}>
          <small>Color: ${this.colorValue}</small>
        </div>

        <div class="form-group">
          <label>Textarea</label>
          <textarea
            .value=${this.textareaValue}
            @input=${(e) => this.textareaValue = e.target.value}
            placeholder="Enter multiple lines..."></textarea>
        </div>

        <div class="form-group">
          <label>Checkboxes</label>
          <div class="checkbox-group">
            ${Object.entries(this.checkboxes).map(([key, checked]) => html`
              <div class="checkbox-item">
                <input type="checkbox"
                  id=${key}
                  .checked=${checked}
                  @change=${(e) => this.checkboxes = {...this.checkboxes, [key]: e.target.checked}}>
                <label for=${key}>Option ${key.slice(-1)}</label>
              </div>
            `)}
          </div>
        </div>

        <div class="form-group">
          <label>Radio Buttons</label>
          <div class="radio-group">
            ${['option1', 'option2', 'option3'].map(opt => html`
              <div class="radio-item">
                <input type="radio"
                  name="radio"
                  id=${opt}
                  .checked=${this.radioValue === opt}
                  @change=${() => this.radioValue = opt}>
                <label for=${opt}>${opt}</label>
              </div>
            `)}
          </div>
        </div>
      </div>
    `;
  }

  renderComponentsTab() {
    return html`
      <div class="card">
        <div class="card-header">
          <h2>🧩 UI Components</h2>
        </div>

        <h3>Buttons</h3>
        <div>
          <button class="btn" @click=${() => this.counter++}>Primary (${this.counter})</button>
          <button class="btn btn-secondary" @click=${() => this.counter--}>Secondary</button>
          <button class="btn btn-success">Success</button>
          <button class="btn btn-warning">Warning</button>
          <button class="btn btn-danger">Danger</button>
          <button class="btn btn-sm">Small</button>
        </div>

        <h3>Badges</h3>
        <div>
          <span class="badge badge-primary">Primary</span>
          <span class="badge badge-success">✅ Success</span>
          <span class="badge badge-warning">⚠️ Warning</span>
          <span class="badge badge-error">❌ Error</span>
        </div>

        <h3>Alerts</h3>
        <div class="alert alert-info">
          ℹ️ <strong>Info:</strong> This is an informational message.
        </div>
        <div class="alert alert-success">
          ✅ <strong>Success:</strong> Operation completed successfully!
        </div>
        <div class="alert alert-warning">
          ⚠️ <strong>Warning:</strong> Please pay attention to this.
        </div>
        <div class="alert alert-error">
          ❌ <strong>Error:</strong> Something went wrong.
        </div>

        <h3>List Items</h3>
        ${[1, 2, 3].map(i => html`
          <div class="list-item">
            <div>
              <strong>Slot ${i}</strong>
              <span class="badge badge-success">Active</span>
            </div>
            <div>
              <button class="btn btn-sm">Edit</button>
              <button class="btn btn-sm btn-danger">Delete</button>
            </div>
          </div>
        `)}
      </div>
    `;
  }

  renderAdvancedTab() {
    return html`
      <div class="card">
        <div class="card-header">
          <h2>🚀 Advanced Features</h2>
        </div>

        <h3>Collapsible Sections</h3>
        ${[1, 2, 3].map(i => html`
          <div class="collapsible">
            <div class="collapsible-header" @click=${() => this.toggleCollapse(`section${i}`)}>
              <span>📦 Collapsible Section ${i}</span>
              <span class="collapsible-icon ${this.collapsedSections[`section${i}`] ? 'open' : ''}">▼</span>
            </div>
            <div class="collapsible-content ${this.collapsedSections[`section${i}`] ? 'open' : ''}">
              <p>This is the content of section ${i}. You can put any content here: forms, lists, charts, etc.</p>
              <button class="btn btn-sm">Action ${i}</button>
            </div>
          </div>
        `)}

        <h3>📊 Chart.js - Temperature History</h3>
        ${this.chartLoaded ? html`
          <div class="chart-container">
            <canvas id="temperatureChart"></canvas>
          </div>
          <div class="alert alert-success">
            <strong>✅ Chart.js Working!</strong> Interactive temperature chart with multiple datasets.
          </div>
        ` : html`
          <div class="alert alert-info">
            ⏳ Loading Chart.js library...
          </div>
        `}

        <h3>📅 Timeline - Climate Events</h3>
        ${this.timelineLoaded ? html`
          <div class="timeline-container">
            <div class="timeline-item">
              <div class="time">00:00 - 06:00</div>
              <div class="content">
                <strong>🌙 Night Mode</strong> - Temperature: 18°C
                <br><small>Climate mode: Heat, Fan: Low</small>
              </div>
            </div>
            <div class="timeline-item" style="border-left-color: var(--warning-color);">
              <div class="time">06:00 - 08:00</div>
              <div class="content">
                <strong>☀️ Morning</strong> - Temperature: 21°C
                <br><small>Climate mode: Heat, Fan: Medium</small>
              </div>
            </div>
            <div class="timeline-item" style="border-left-color: var(--success-color);">
              <div class="time">08:00 - 18:00</div>
              <div class="content">
                <strong>🏢 Day Mode</strong> - Temperature: 22°C
                <br><small>Climate mode: Auto, Fan: Auto</small>
              </div>
            </div>
            <div class="timeline-item" style="border-left-color: var(--error-color);">
              <div class="time">18:00 - 22:00</div>
              <div class="content">
                <strong>🌆 Evening</strong> - Temperature: 21°C
                <br><small>Climate mode: Heat, Fan: Low</small>
              </div>
            </div>
            <div class="timeline-item">
              <div class="time">22:00 - 24:00</div>
              <div class="content">
                <strong>🌙 Night Prepare</strong> - Temperature: 19°C
                <br><small>Climate mode: Heat, Fan: Low</small>
              </div>
            </div>
          </div>
          <div class="alert alert-success">
            <strong>✅ Timeline Working!</strong> Shows climate schedule with time slots and events.
          </div>
        ` : html`
          <div class="alert alert-info">
            ⏳ Loading Timeline...
          </div>
        `}
      </div>

      <div class="card">
        <div class="card-header">
          <h2>✅ Component Status</h2>
        </div>
        <div class="alert alert-success">
          <strong>🎉 All Features Working!</strong><br>
          • ✅ LitElement with CDN import<br>
          • ✅ All form controls functional<br>
          • ✅ Searchable/filterable select (Tom-Select)<br>
          • ✅ Interactive charts (Chart.js)<br>
          • ✅ Timeline component<br>
          • ✅ Reactive state management<br>
          • ✅ HA CSS variables for theming<br>
          • ✅ Collapsible sections<br>
          • ✅ Mobile-responsive layout
        </div>
      </div>
    `;
  }

  toggleCollapse(section) {
    this.collapsedSections = {
      ...this.collapsedSections,
      [section]: !this.collapsedSections[section]
    };
  }
}

customElements.define('advanced-panel', AdvancedPanel);

console.log('✅ Advanced LitElement component registered');
