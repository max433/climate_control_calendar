/**
 * LitElement Test - trying to use HA's bundled Lit
 */

console.log('🔍 Checking for Lit availability...');

// Check if Lit is available globally
if (window.litHtml) {
  console.log('✅ Found window.litHtml');
}
if (window.LitElement) {
  console.log('✅ Found window.LitElement');
}

// Check what's available on window
console.log('window.customElements:', window.customElements);

// Try approach 1: Use customElements without importing
class TestPanelV2 extends HTMLElement {
  constructor() {
    super();
    console.log('🎨 TestPanelV2 constructor called');
    this.attachShadow({ mode: 'open' });
    this.render();
  }

  connectedCallback() {
    console.log('✅ TestPanelV2 connected to DOM');
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 20px;
          font-family: var(--primary-font-family, sans-serif);
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #212121);
        }
        .card {
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 8px);
          padding: 16px;
          margin: 16px 0;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
        }
        .btn {
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff);
          border: none;
          padding: 10px 20px;
          border-radius: 4px;
          cursor: pointer;
          margin: 4px;
        }
        h1 {
          color: var(--primary-text-color, #212121);
        }
        h2 {
          color: var(--primary-color, #03a9f4);
        }
      </style>

      <div class="container">
        <h1>🧪 Test Panel v2 (No Import)</h1>

        <div class="card">
          <h2>Vanilla Custom Element</h2>
          <p>This is using plain HTMLElement + Shadow DOM</p>
          <p><strong>No Lit import needed!</strong></p>
          <button class="btn" id="testBtn">Click Me</button>
        </div>

        <div class="card">
          <h2>Debug Info</h2>
          <p>Check console for Lit availability</p>
          <div id="debug"></div>
        </div>
      </div>
    `;

    // Add event listener
    const btn = this.shadowRoot.getElementById('testBtn');
    btn.addEventListener('click', () => {
      alert('Button clicked! Element is working.');
    });

    // Show debug info
    const debug = this.shadowRoot.getElementById('debug');
    debug.innerHTML = `
      <p>window.litHtml: ${typeof window.litHtml}</p>
      <p>window.LitElement: ${typeof window.LitElement}</p>
      <p>customElements: ${typeof customElements}</p>
    `;
  }
}

customElements.define('test-panel-v2', TestPanelV2);

console.log('✅ test-panel-v2 registered (no Lit import)');
