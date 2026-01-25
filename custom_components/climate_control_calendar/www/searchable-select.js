/**
 * Searchable Select - Lightweight searchable dropdown component
 * No external dependencies, compatible with Shadow DOM
 */

class SearchableSelect {
  constructor(selectElement, options = {}) {
    this.select = selectElement;
    this.options = {
      placeholder: options.placeholder || 'Search...',
      noResultsText: options.noResultsText || 'No results found',
      ...options
    };

    this.isOpen = false;
    this.selectedOption = null;
    this.filteredOptions = [];

    this.init();
  }

  init() {
    // Hide original select
    this.select.style.display = 'none';

    // Create custom dropdown
    this.container = document.createElement('div');
    this.container.className = 'searchable-select-container';

    // Create display input
    this.display = document.createElement('input');
    this.display.type = 'text';
    this.display.className = 'searchable-select-display';
    this.display.placeholder = this.getSelectedText() || this.options.placeholder;
    this.display.readOnly = false;

    // Create dropdown
    this.dropdown = document.createElement('div');
    this.dropdown.className = 'searchable-select-dropdown';
    this.dropdown.style.display = 'none';

    // Assemble
    this.container.appendChild(this.display);
    this.container.appendChild(this.dropdown);
    this.select.parentNode.insertBefore(this.container, this.select);

    // Populate options
    this.updateOptions();

    // Event listeners
    this.display.addEventListener('focus', () => this.open());
    this.display.addEventListener('input', (e) => this.filter(e.target.value));
    this.display.addEventListener('blur', () => {
      // Delay to allow click on option
      setTimeout(() => this.close(), 200);
    });

    // Update on select change
    this.select.addEventListener('change', () => {
      this.display.placeholder = this.getSelectedText();
      this.display.value = '';
    });
  }

  getSelectedText() {
    const selected = this.select.options[this.select.selectedIndex];
    return selected ? selected.text : '';
  }

  updateOptions() {
    this.filteredOptions = Array.from(this.select.options).map((opt, idx) => ({
      value: opt.value,
      text: opt.text,
      index: idx
    }));
    this.renderOptions();
  }

  renderOptions() {
    this.dropdown.innerHTML = '';

    if (this.filteredOptions.length === 0) {
      const noResults = document.createElement('div');
      noResults.className = 'searchable-select-option searchable-select-no-results';
      noResults.textContent = this.options.noResultsText;
      this.dropdown.appendChild(noResults);
      return;
    }

    this.filteredOptions.forEach(opt => {
      const optionEl = document.createElement('div');
      optionEl.className = 'searchable-select-option';
      optionEl.textContent = opt.text;
      optionEl.dataset.value = opt.value;
      optionEl.dataset.index = opt.index;

      if (this.select.selectedIndex === opt.index) {
        optionEl.classList.add('selected');
      }

      optionEl.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this.selectOption(opt.index);
      });

      this.dropdown.appendChild(optionEl);
    });
  }

  filter(query) {
    const lowerQuery = query.toLowerCase();
    this.filteredOptions = Array.from(this.select.options)
      .map((opt, idx) => ({
        value: opt.value,
        text: opt.text,
        index: idx
      }))
      .filter(opt => opt.text.toLowerCase().includes(lowerQuery));

    this.renderOptions();
  }

  selectOption(index) {
    this.select.selectedIndex = index;
    this.select.dispatchEvent(new Event('change', { bubbles: true }));
    this.display.value = '';
    this.display.placeholder = this.getSelectedText();
    this.close();
  }

  open() {
    this.isOpen = true;
    this.dropdown.style.display = 'block';
    this.display.value = '';
    this.filter('');
  }

  close() {
    this.isOpen = false;
    this.dropdown.style.display = 'none';
    this.display.value = '';
  }

  destroy() {
    this.container.remove();
    this.select.style.display = '';
  }
}

// CSS for SearchableSelect
const SEARCHABLE_SELECT_CSS = `
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

  /* Scrollbar styling */
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
`;
