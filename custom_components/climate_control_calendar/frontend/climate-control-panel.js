/**
 * Climate Control Calendar Dashboard Panel
 *
 * Main panel component for read-only dashboard.
 * Shows live state and timeline with automatic theme support.
 */

class ClimateControlPanel extends HTMLElement {
  constructor() {
    super();
    this.hass = null;
    this._config = null;
    this._liveState = null;
    this._timeline = null;
    this._loading = true;
    this._subscription = null;
  }

  set panel(panelConfig) {
    this._config = panelConfig;
    this._loadData();
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    if (!hass) return;

    const oldHass = this.hass;
    this._hass = hass;

    if (!oldHass) {
      this._loadData();
      this._subscribeUpdates();
    }
  }

  get hass() {
    return this._hass;
  }

  async _loadData() {
    if (!this.hass || !this._config) return;

    this._loading = true;
    this._render();

    try {
      const entryId = this._config.config_entry_id || this._getFirstEntryId();

      // Load live state and timeline in parallel
      const [liveState, timeline] = await Promise.all([
        this._fetchLiveState(entryId),
        this._fetchTimeline(entryId),
      ]);

      this._liveState = liveState;
      this._timeline = timeline;
      this._loading = false;
      this._render();
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      this._loading = false;
      this._render();
    }
  }

  async _fetchLiveState(entryId) {
    return this.hass.connection.sendMessagePromise({
      type: 'climate_control_calendar/get_live_state',
      entry_id: entryId,
    });
  }

  async _fetchTimeline(entryId, date = null) {
    return this.hass.connection.sendMessagePromise({
      type: 'climate_control_calendar/get_timeline',
      entry_id: entryId,
      date: date,
    });
  }

  async _subscribeUpdates() {
    if (!this.hass || this._subscription) return;

    const entryId = this._config.config_entry_id || this._getFirstEntryId();

    this._subscription = await this.hass.connection.subscribeMessage(
      (msg) => this._handleUpdate(msg),
      {
        type: 'climate_control_calendar/subscribe_updates',
        entry_id: entryId,
      }
    );
  }

  _handleUpdate(message) {
    if (message.type === 'update') {
      console.log('Dashboard update received:', message.timestamp);
      this._loadData();
    }
  }

  _getFirstEntryId() {
    // Get first entry ID from hass.data (fallback)
    const entries = Object.keys(this.hass.config_entries || {});
    return entries.find(e => e.startsWith('climate_control_calendar')) || '';
  }

  _render() {
    if (!this.hass) {
      this.innerHTML = '<div>Loading...</div>';
      return;
    }

    this.innerHTML = `
      <style>
        .panel-container {
          padding: 16px;
          max-width: 1400px;
          margin: 0 auto;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          padding: 16px;
          background: var(--card-background-color);
          border-radius: 8px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
        }

        .panel-header h1 {
          margin: 0;
          font-size: 24px;
          font-weight: 500;
        }

        .refresh-button {
          background: var(--primary-color);
          color: var(--text-primary-color);
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }

        .refresh-button:hover {
          opacity: 0.9;
        }

        .content {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .loading {
          text-align: center;
          padding: 48px;
          font-size: 18px;
          color: var(--secondary-text-color);
        }

        @media (max-width: 768px) {
          .panel-container {
            padding: 8px;
          }
        }
      </style>

      <div class="panel-container">
        <div class="panel-header">
          <h1>📊 Climate Control Calendar Dashboard</h1>
          <button class="refresh-button" id="refresh-btn">🔄 Refresh</button>
        </div>

        <div class="content">
          ${this._loading ? this._renderLoading() : this._renderContent()}
        </div>
      </div>
    `;

    // Attach event listener
    const refreshBtn = this.querySelector('#refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this._loadData());
    }
  }

  _renderLoading() {
    return '<div class="loading">Loading dashboard data...</div>';
  }

  _renderContent() {
    return `
      ${this._renderLiveOverview()}
      ${this._renderTimeline()}
    `;
  }

  _renderLiveOverview() {
    if (!this._liveState) return '';

    const { active_slot, trigger_reason, affected_entities, timestamp } = this._liveState;

    if (!active_slot) {
      return `
        <ha-card>
          <div class="card-content">
            <h2>📊 Live Overview</h2>
            <p style="color: var(--secondary-text-color); font-style: italic;">
              No active slot - No calendar events matched to bindings
            </p>
          </div>
        </ha-card>
      `;
    }

    const entitiesHtml = affected_entities
      .map(entity => {
        if (entity.status === 'ok') {
          return `
            <div style="padding: 8px; background: var(--primary-background-color); border-radius: 4px; margin-bottom: 8px;">
              ✅ <strong>${entity.entity_id}</strong><br>
              &nbsp;&nbsp;&nbsp;&nbsp;Current: ${entity.current_temperature}°C → Target: ${entity.target_temperature}°C (${entity.hvac_mode})
            </div>
          `;
        } else if (entity.status === 'unavailable') {
          return `<div style="padding: 8px; color: var(--warning-color);">⚠️ ${entity.entity_id} - Unavailable</div>`;
        } else {
          return `<div style="padding: 8px; color: var(--error-color);">❌ ${entity.entity_id} - Not found</div>`;
        }
      })
      .join('');

    return `
      <ha-card>
        <div class="card-content">
          <h2>📊 Live Overview</h2>
          <div style="padding: 16px; background: var(--success-color); color: white; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-size: 18px; font-weight: 500;">🟢 Active Slot: "${active_slot.label || active_slot.id}"</div>
            ${trigger_reason ? `
              <div style="margin-top: 8px; opacity: 0.9;">
                📅 Triggered by: Calendar "${trigger_reason.calendar_id}" → Pattern "${trigger_reason.matched_binding?.match?.value || 'unknown'}"<br>
                📆 Event: "${trigger_reason.calendar_event}"<br>
                ⏱️ Active: ${new Date(trigger_reason.event_start).toLocaleTimeString()} → ${new Date(trigger_reason.event_end).toLocaleTimeString()}
              </div>
            ` : ''}
          </div>

          <h3>🎯 Affected Climate Entities (${affected_entities.length})</h3>
          ${entitiesHtml}

          <div style="margin-top: 16px; text-align: right; color: var(--secondary-text-color); font-size: 12px;">
            Last update: ${new Date(timestamp).toLocaleString()}
          </div>
        </div>
      </ha-card>
    `;
  }

  _renderTimeline() {
    if (!this._timeline) return '';

    const { date, events, coverage_percentage, gaps } = this._timeline;

    const eventsHtml = events
      .map(event => {
        const statusIcon = event.status === 'active' ? '🟢' :
                          event.status === 'upcoming' ? '🔵' : '⚪';

        const hasSlot = event.applied_slot !== null;
        const bgColor = hasSlot ? 'var(--success-color)' : 'var(--warning-color)';
        const opacity = event.status === 'past' ? '0.5' : '1';

        return `
          <div style="padding: 12px; background: ${bgColor}; color: white; border-radius: 4px; margin-bottom: 8px; opacity: ${opacity};">
            <div style="font-weight: 500;">
              ${statusIcon} ${event.start} - ${event.end}: "${event.calendar_event}"
            </div>
            ${hasSlot ? `
              <div style="margin-top: 4px; opacity: 0.9; font-size: 13px;">
                → Slot: "${event.applied_slot.label || event.applied_slot.id}" (Priority: ${event.matched_binding.priority})
              </div>
            ` : `
              <div style="margin-top: 4px; opacity: 0.9; font-size: 13px;">
                ⚠️ No matching binding - Event ignored
              </div>
            `}
          </div>
        `;
      })
      .join('');

    const gapsHtml = gaps.length > 0 ? `
      <div style="margin-top: 16px; padding: 12px; background: var(--warning-color); color: white; border-radius: 4px;">
        <strong>⚠️ Coverage Gaps (${gaps.length})</strong>
        ${gaps.map(gap => `
          <div style="margin-top: 4px; font-size: 13px;">
            ${gap.start} - ${gap.end} (${gap.duration_hours}h): No matching events/bindings
          </div>
        `).join('')}
      </div>
    ` : '<div style="margin-top: 16px; color: var(--success-color);">✅ Full day coverage - No gaps</div>';

    return `
      <ha-card>
        <div class="card-content">
          <h2>📅 Today's Timeline (${date})</h2>
          <div style="margin-bottom: 16px; padding: 12px; background: var(--primary-background-color); border-radius: 4px;">
            <strong>Coverage: ${coverage_percentage}%</strong>
            <div style="margin-top: 8px; height: 8px; background: var(--divider-color); border-radius: 4px; overflow: hidden;">
              <div style="width: ${coverage_percentage}%; height: 100%; background: var(--success-color);"></div>
            </div>
          </div>

          <h3>Events & Slots Applied (${events.length})</h3>
          ${events.length > 0 ? eventsHtml : '<p style="color: var(--secondary-text-color); font-style: italic;">No events today</p>'}

          ${gapsHtml}
        </div>
      </ha-card>
    `;
  }

  disconnectedCallback() {
    if (this._subscription) {
      this._subscription.then(unsub => unsub()).catch(err => console.error('Error unsubscribing:', err));
      this._subscription = null;
    }
  }
}

customElements.define('climate-control-panel', ClimateControlPanel);
