/**
 * AUTOVYNEX — Core JavaScript Engine
 * Handles Theme Toggling, Mobile Navigation Drawer, Universal Toast System,
 * Live Search Autocomplete, Vehicle Selector Modal, and Async Feedback.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Lucide Icons
  const refreshIcons = () => {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  };
  refreshIcons();

  // 2. Global Toast Notification System
  window.showToast = function(message, type = 'success', duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-message toast-${type}`;

    let iconName = 'check-circle';
    if (type === 'error') iconName = 'alert-circle';
    if (type === 'info') iconName = 'info';

    toast.innerHTML = `
      <i data-lucide="${iconName}" class="toast-icon"></i>
      <div style="flex:1;">${message}</div>
      <button type="button" class="toast-close-btn" aria-label="Dismiss">&times;</button>
    `;

    container.appendChild(toast);
    refreshIcons();

    const closeBtn = toast.querySelector('.toast-close-btn');
    const dismiss = () => {
      toast.classList.add('toast-hiding');
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 250);
    };

    if (closeBtn) closeBtn.addEventListener('click', dismiss);
    setTimeout(dismiss, duration);
  };

  // 3. Dark / Light Theme Management
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const storedTheme = localStorage.getItem('autovynex-theme') || 'light';
  document.documentElement.setAttribute('data-theme', storedTheme);

  const updateThemeIcon = (theme) => {
    const iconEl = document.getElementById('theme-toggle-icon');
    if (iconEl) {
      iconEl.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
      refreshIcons();
    }
  };
  updateThemeIcon(storedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('autovynex-theme', newTheme);
      updateThemeIcon(newTheme);
      window.showToast(`Switched to ${newTheme === 'dark' ? 'Dark' : 'Light'} Mode`, 'info', 2000);
    });
  }

  // 4. Mobile Navigation Drawer Management
  const mobileToggleBtn = document.getElementById('mobile-nav-toggle-btn');
  const mobileDrawer = document.getElementById('mobile-nav-drawer');
  const mobileBackdrop = document.getElementById('mobile-drawer-backdrop');
  const closeDrawerBtn = document.getElementById('close-mobile-drawer-btn');

  const openMobileDrawer = () => {
    if (mobileDrawer && mobileBackdrop) {
      mobileDrawer.classList.add('active');
      mobileBackdrop.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  };

  const closeMobileDrawer = () => {
    if (mobileDrawer && mobileBackdrop) {
      mobileDrawer.classList.remove('active');
      mobileBackdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
  };

  if (mobileToggleBtn) mobileToggleBtn.addEventListener('click', openMobileDrawer);
  if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeMobileDrawer);
  if (mobileBackdrop) mobileBackdrop.addEventListener('click', closeMobileDrawer);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMobileDrawer();
      if (vehicleModal) vehicleModal.style.display = 'none';
    }
  });

  // 5. Vehicle Selector Modal Management
  const vehicleModal = document.getElementById('vehicle-selector-modal');
  const openModalBtns = document.querySelectorAll('.open-vehicle-modal-btn');
  const closeModalBtns = document.querySelectorAll('.close-vehicle-modal-btn');

  openModalBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      closeMobileDrawer();
      if (vehicleModal) vehicleModal.style.display = 'flex';
    });
  });

  closeModalBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (vehicleModal) vehicleModal.style.display = 'none';
    });
  });

  if (vehicleModal) {
    vehicleModal.addEventListener('click', (e) => {
      if (e.target === vehicleModal) vehicleModal.style.display = 'none';
    });
  }

  // 5-Step Cascading Vehicle Modal Dropdowns (Make -> Model -> Year -> Fuel -> Variant)
  const makeSelect = document.getElementById('modal-select-make');
  const modelSelect = document.getElementById('modal-select-model');
  const yearSelect = document.getElementById('modal-select-year');
  const fuelSelect = document.getElementById('modal-select-fuel');
  const variantSelect = document.getElementById('modal-select-variant');
  const selectSubmitBtn = document.getElementById('modal-submit-vehicle');

  if (makeSelect && modelSelect) {
    // 1. Make Change -> Fetch Models
    makeSelect.addEventListener('change', async () => {
      const makeId = makeSelect.value;
      modelSelect.innerHTML = '<option value="">Loading Models...</option>';
      modelSelect.disabled = true;
      if (yearSelect) { yearSelect.innerHTML = '<option value="">Select Year...</option>'; yearSelect.disabled = true; }
      if (fuelSelect) { fuelSelect.innerHTML = '<option value="">Select Fuel Type...</option>'; fuelSelect.disabled = true; }
      if (variantSelect) { variantSelect.innerHTML = '<option value="">Select Variant...</option>'; variantSelect.disabled = true; }
      if (selectSubmitBtn) selectSubmitBtn.disabled = true;

      if (!makeId) {
        modelSelect.innerHTML = '<option value="">Select Model...</option>';
        return;
      }

      try {
        const res = await fetch(`/vehicles/api/models/?make_id=${makeId}`);
        const data = await res.json();
        let options = '<option value="">Select Model...</option>';
        data.models.forEach(m => {
          options += `<option value="${m.id}">${m.name} (${m.body_type})</option>`;
        });
        modelSelect.innerHTML = options;
        modelSelect.disabled = false;
      } catch (err) {
        console.error('Failed to load models:', err);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
      }
    });

    // 2. Model Change -> Fetch Years
    modelSelect.addEventListener('change', async () => {
      const modelId = modelSelect.value;
      if (yearSelect) { yearSelect.innerHTML = '<option value="">Loading Years...</option>'; yearSelect.disabled = true; }
      if (fuelSelect) { fuelSelect.innerHTML = '<option value="">Select Fuel Type...</option>'; fuelSelect.disabled = true; }
      if (variantSelect) { variantSelect.innerHTML = '<option value="">Select Variant...</option>'; variantSelect.disabled = true; }
      if (selectSubmitBtn) selectSubmitBtn.disabled = true;

      if (!modelId) {
        if (yearSelect) yearSelect.innerHTML = '<option value="">Select Year...</option>';
        return;
      }

      try {
        const res = await fetch(`/vehicles/api/years/?model_id=${modelId}`);
        const data = await res.json();
        let options = '<option value="">Select Manufacturing Year...</option>';
        data.years.forEach(y => {
          options += `<option value="${y}">${y}</option>`;
        });
        if (yearSelect) {
          yearSelect.innerHTML = options;
          yearSelect.disabled = false;
        }
      } catch (err) {
        console.error('Failed to load years:', err);
        if (yearSelect) yearSelect.innerHTML = '<option value="">Error loading years</option>';
      }
    });

    // 3. Year Change -> Fetch Fuel Types
    if (yearSelect) {
      yearSelect.addEventListener('change', async () => {
        const modelId = modelSelect.value;
        const year = yearSelect.value;
        if (fuelSelect) { fuelSelect.innerHTML = '<option value="">Loading Fuel Types...</option>'; fuelSelect.disabled = true; }
        if (variantSelect) { variantSelect.innerHTML = '<option value="">Select Variant...</option>'; variantSelect.disabled = true; }
        if (selectSubmitBtn) selectSubmitBtn.disabled = true;

        if (!year) {
          if (fuelSelect) fuelSelect.innerHTML = '<option value="">Select Fuel Type...</option>';
          return;
        }

        try {
          const res = await fetch(`/vehicles/api/fuels/?model_id=${modelId}&year=${year}`);
          const data = await res.json();
          let options = '<option value="">Select Fuel Type...</option>';
          data.fuels.forEach(f => {
            options += `<option value="${f}">${f}</option>`;
          });
          if (fuelSelect) {
            fuelSelect.innerHTML = options;
            fuelSelect.disabled = false;
          }
        } catch (err) {
          console.error('Failed to load fuels:', err);
          if (fuelSelect) fuelSelect.innerHTML = '<option value="">Error loading fuel types</option>';
        }
      });
    }

    // 4. Fuel Change -> Fetch Exact Variants
    if (fuelSelect && variantSelect) {
      fuelSelect.addEventListener('change', async () => {
        const modelId = modelSelect.value;
        const year = yearSelect ? yearSelect.value : '';
        const fuel = fuelSelect.value;
        variantSelect.innerHTML = '<option value="">Loading Variants...</option>';
        variantSelect.disabled = true;
        if (selectSubmitBtn) selectSubmitBtn.disabled = true;

        if (!fuel) {
          variantSelect.innerHTML = '<option value="">Select Variant...</option>';
          return;
        }

        try {
          const res = await fetch(`/vehicles/api/variants/?model_id=${modelId}&year=${year}&fuel_type=${encodeURIComponent(fuel)}`);
          const data = await res.json();
          let options = '<option value="">Select Exact Variant & Transmission...</option>';
          data.variants.forEach(v => {
            options += `<option value="${v.id}">${v.name} • ${v.transmission} (${v.engine_cc}cc, ${v.power_hp}hp)</option>`;
          });
          variantSelect.innerHTML = options;
          variantSelect.disabled = false;
        } catch (err) {
          console.error('Failed to load variants:', err);
          variantSelect.innerHTML = '<option value="">Error loading variants</option>';
        }
      });

      variantSelect.addEventListener('change', () => {
        if (selectSubmitBtn) {
          selectSubmitBtn.disabled = !variantSelect.value;
        }
      });
    }
  }

  // 6. Header Autocomplete Quick Search
  const searchInput = document.getElementById('header-search-input');
  const searchResults = document.getElementById('header-search-results');
  const searchClearBtn = document.getElementById('header-search-clear');
  let searchTimeout = null;

  if (searchInput && searchResults) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      const query = searchInput.value.trim();

      if (searchClearBtn) {
        searchClearBtn.style.display = query.length > 0 ? 'block' : 'none';
      }

      if (query.length < 2) {
        searchResults.style.display = 'none';
        searchResults.innerHTML = '';
        return;
      }

      searchTimeout = setTimeout(async () => {
        searchResults.innerHTML = '<div style="padding:16px; color:var(--text-muted); text-align:center; font-size:0.88rem;"><i data-lucide="loader" style="animation:spin 1s linear infinite; display:inline-block; vertical-align:middle; margin-right:6px;"></i> Searching parts catalog...</div>';
        searchResults.style.display = 'block';
        refreshIcons();

        try {
          const res = await fetch(`/shop/api/search/?q=${encodeURIComponent(query)}`);
          const data = await res.json();
          if (data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(item => {
              html += `
                <a href="${item.url}" class="search-result-item">
                  <div style="width:38px; height:38px; background:var(--bg-surface-subtle); border-radius:6px; display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0;">
                    ${item.image ? `<img src="${item.image}" alt="${item.name}" style="max-height:100%; max-width:100%; object-fit:contain;">` : `<i data-lucide="package" style="width:18px; color:var(--text-muted);"></i>`}
                  </div>
                  <div style="flex:1; min-width:0;">
                    <div style="font-weight:600; font-size:0.88rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.name}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${item.category} • SKU: ${item.sku}</div>
                  </div>
                  <div style="font-weight:800; color:var(--color-primary); font-size:0.95rem;">₹${Number(item.price).toLocaleString('en-IN')}</div>
                </a>
              `;
            });
            searchResults.innerHTML = html;
            searchResults.style.display = 'block';
            refreshIcons();
          } else {
            searchResults.innerHTML = '<div style="padding:18px; color:var(--text-muted); text-align:center; font-size:0.88rem;"><i data-lucide="alert-circle" style="width:20px; height:20px; margin:0 auto 6px; display:block; color:var(--text-muted);"></i>No matching spare parts found</div>';
            searchResults.style.display = 'block';
            refreshIcons();
          }
        } catch (err) {
          console.error('Search error:', err);
          searchResults.innerHTML = '<div style="padding:16px; color:var(--color-danger); text-align:center; font-size:0.85rem;">Failed to fetch search results.</div>';
        }
      }, 250);
    });

    if (searchClearBtn) {
      searchClearBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchClearBtn.style.display = 'none';
        searchResults.style.display = 'none';
        searchResults.innerHTML = '';
        searchInput.focus();
      });
    }

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = 'none';
      }
    });
  }

  // 7. Desktop User Menu Dropdown Toggle
  const userBtn = document.getElementById('user-menu-btn');
  const userDropdown = document.getElementById('user-menu-dropdown');
  if (userBtn && userDropdown) {
    userBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      userDropdown.style.display = userDropdown.style.display === 'block' ? 'none' : 'block';
    });
    document.addEventListener('click', () => {
      userDropdown.style.display = 'none';
    });
  }

  // 8. CSRF Cookie Helper
  window.getCookie = function(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  };
});
