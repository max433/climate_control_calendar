/**
 * Climate Control Calendar Panel
 * Custom element that loads the test panel HTML
 */

class ClimatePanelCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  async connectedCallback() {
    console.log('🎨 Climate Control Panel - Loading...');

    try {
      // Fetch the HTML content
      const response = await fetch('/climate_control_calendar/static/test-panel.html');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const html = await response.text();

      // Create a container div
      const container = document.createElement('div');
      container.innerHTML = html;

      // Append to shadow DOM
      this.shadowRoot.appendChild(container);

      console.log('✅ Climate Control Panel - Loaded successfully!');
    } catch (error) {
      console.error('❌ Climate Control Panel - Failed to load:', error);

      // Show error message
      this.shadowRoot.innerHTML = `
        <div style="padding: 40px; font-family: Arial; background: #1a1a1a; color: white;">
          <h1 style="color: #ff4444;">⚠️ Error Loading Panel</h1>
          <p>Failed to load Climate Control Panel.</p>
          <p><strong>Error:</strong> ${error.message}</p>
          <p style="margin-top: 20px; color: #888;">Check browser console for details.</p>
        </div>
      `;
    }
  }
}

// Define the custom element
customElements.define('climate-panel-card', ClimatePanelCard);

console.log('🚀 Climate Control Panel - Custom element registered');
