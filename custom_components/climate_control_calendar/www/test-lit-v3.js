/**
 * LitElement Test - trying dynamic import from HA bundle
 */

console.log('🔍 Attempting to load Lit from Home Assistant...');

// Try different possible paths where HA might expose Lit
const possiblePaths = [
  '/frontend_latest/core-latest.js',
  '/frontend_latest/app.js',
  '/hacsfiles/frontend/lit-element.js',
  '/static/frontend/lit-element.js'
];

async function tryLoadLit() {
  console.log('Testing possible Lit paths...');

  for (const path of possiblePaths) {
    try {
      console.log(`Trying: ${path}`);
      const module = await import(path);
      console.log(`✅ Loaded from ${path}:`, Object.keys(module));

      if (module.LitElement) {
        console.log('🎉 Found LitElement!');
        return module;
      }
    } catch (err) {
      console.log(`❌ Failed ${path}:`, err.message);
    }
  }

  console.log('❌ Could not find Lit in any known location');
  return null;
}

// Try to load and create component
tryLoadLit().then(lit => {
  if (lit && lit.LitElement) {
    console.log('Creating Lit component...');

    class TestLitV3 extends lit.LitElement {
      static get properties() {
        return {
          count: { type: Number }
        };
      }

      constructor() {
        super();
        this.count = 0;
      }

      render() {
        return lit.html`
          <div style="padding: 20px;">
            <h1>🎉 LitElement Working!</h1>
            <p>Count: ${this.count}</p>
            <button @click=${() => this.count++}>Increment</button>
          </div>
        `;
      }
    }

    customElements.define('test-lit-v3', TestLitV3);
    console.log('✅ test-lit-v3 registered with real Lit!');
  } else {
    console.log('⚠️ Falling back to vanilla element');

    // Fallback to vanilla
    class TestLitV3Fallback extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = `
          <div style="padding: 20px; background: #ffc;">
            <h1>⚠️ Lit Not Found</h1>
            <p>Could not load LitElement from HA bundle</p>
            <p>Using vanilla Custom Element instead</p>
          </div>
        `;
      }
    }

    customElements.define('test-lit-v3', TestLitV3Fallback);
    console.log('✅ test-lit-v3 registered (fallback)');
  }
});
