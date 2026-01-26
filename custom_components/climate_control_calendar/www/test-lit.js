/**
 * LitElement Test Component for Home Assistant
 * Testing if we can use Lit without external dependencies
 */

// Try to import from HA's bundled lit (if available)
// If this fails, we'll need to find another approach
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/gh/lit/dist@3/core/lit-core.min.js';

class TestLitPanel extends LitElement {
  static get properties() {
    return {
      title: { type: String },
      count: { type: Number }
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }

      .container {
        max-width: 1200px;
        margin: 0 auto;
      }

      .card {
        background: var(--card-background-color, #fff);
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }

      .btn {
        background: var(--primary-color, #03a9f4);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        margin: 5px;
      }

      .btn:hover {
        opacity: 0.8;
      }

      .btn-secondary {
        background: var(--secondary-color, #5f6368);
      }

      .form-group {
        margin: 15px 0;
      }

      label {
        display: block;
        margin-bottom: 5px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }

      input[type="text"],
      input[type="number"],
      select {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        font-size: 14px;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
      }

      .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        background: var(--primary-color, #03a9f4);
        color: white;
        margin: 0 4px;
      }

      .badge-success {
        background: var(--success-color, #4caf50);
      }

      .badge-warning {
        background: var(--warning-color, #ff9800);
      }

      .badge-error {
        background: var(--error-color, #f44336);
      }

      .list-item {
        padding: 15px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .list-item:last-child {
        border-bottom: none;
      }

      h1 {
        color: var(--primary-text-color, #212121);
        margin-bottom: 10px;
      }

      h2 {
        color: var(--primary-color, #03a9f4);
        margin: 20px 0 10px 0;
      }
    `;
  }

  constructor() {
    super();
    this.title = 'LitElement Test Panel';
    this.count = 0;
  }

  increment() {
    this.count++;
  }

  decrement() {
    this.count--;
  }

  render() {
    return html`
      <div class="container">
        <h1>🧪 ${this.title}</h1>

        <!-- Test Card -->
        <div class="card">
          <h2>Test Counter</h2>
          <p>Count: <strong>${this.count}</strong></p>
          <button class="btn" @click=${this.increment}>➕ Increment</button>
          <button class="btn btn-secondary" @click=${this.decrement}>➖ Decrement</button>
        </div>

        <!-- Test Form -->
        <div class="card">
          <h2>Test Form</h2>
          <div class="form-group">
            <label for="testInput">Text Input</label>
            <input type="text" id="testInput" placeholder="Enter text here">
          </div>

          <div class="form-group">
            <label for="testNumber">Number Input</label>
            <input type="number" id="testNumber" placeholder="0" min="0" max="100">
          </div>

          <div class="form-group">
            <label for="testSelect">Select Dropdown</label>
            <select id="testSelect">
              <option value="">Choose an option...</option>
              <option value="1">Option 1</option>
              <option value="2">Option 2</option>
              <option value="3">Option 3</option>
            </select>
          </div>

          <button class="btn">Submit</button>
        </div>

        <!-- Test Badges -->
        <div class="card">
          <h2>Test Badges</h2>
          <span class="badge">Default</span>
          <span class="badge badge-success">Success</span>
          <span class="badge badge-warning">Warning</span>
          <span class="badge badge-error">Error</span>
        </div>

        <!-- Test List -->
        <div class="card">
          <h2>Test List</h2>
          <div class="list-item">
            <div>
              <strong>Item 1</strong>
              <span class="badge badge-success">Active</span>
            </div>
            <div>
              <button class="btn">Edit</button>
            </div>
          </div>
          <div class="list-item">
            <div>
              <strong>Item 2</strong>
              <span class="badge badge-warning">Pending</span>
            </div>
            <div>
              <button class="btn">Edit</button>
            </div>
          </div>
          <div class="list-item">
            <div>
              <strong>Item 3</strong>
              <span class="badge">Inactive</span>
            </div>
            <div>
              <button class="btn">Edit</button>
            </div>
          </div>
        </div>

        <!-- Test Info -->
        <div class="card">
          <h2>✅ LitElement Working!</h2>
          <p>If you can see this styled correctly with working buttons, LitElement is functioning properly.</p>
          <p><strong>CSS Variables:</strong> Using Home Assistant's native CSS variables for theming</p>
          <p><strong>Shadow DOM:</strong> Styles are encapsulated</p>
          <p><strong>Reactive:</strong> Click the counter buttons to test reactivity</p>
        </div>
      </div>
    `;
  }
}

customElements.define('test-lit-panel', TestLitPanel);

console.log('✅ LitElement test component registered');
