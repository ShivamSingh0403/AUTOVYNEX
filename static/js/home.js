/**
 * AUTOVYNEX — Homepage Interactive Engine
 * Handles 5-Stage Interactive Vehicle Selector, Product Category Filter Tabs,
 * Asynchronous Add-to-Cart with Animated Toast Feedback, Interactive Wishlist,
 * and Dynamic Maintenance Milestones.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Five-Stage Vehicle Selector Interactive Card
  const hMake = document.getElementById('home-make-select');
  const hModel = document.getElementById('home-model-select');
  const hYear = document.getElementById('home-year-select');
  const hFuel = document.getElementById('home-fuel-select');
  const hVariant = document.getElementById('home-variant-select');
  const hSubmit = document.getElementById('home-submit-btn');
  const hPreviewCard = document.getElementById('home-vehicle-preview');
  const hPreviewName = document.getElementById('home-preview-car-name');
  const hPreviewMeta = document.getElementById('home-preview-car-meta');

  let currentVariants = [];

  const filterAndPopulateVariants = () => {
    if (!hVariant) return;
    const selectedYear = hYear ? parseInt(hYear.value) : null;
    const selectedFuel = hFuel ? hFuel.value.toLowerCase() : '';

    let filtered = currentVariants;
    if (selectedYear) {
      filtered = filtered.filter(v => v.year_from <= selectedYear && v.year_to >= selectedYear);
    }
    if (selectedFuel) {
      filtered = filtered.filter(v => v.fuel_type.toLowerCase() === selectedFuel);
    }

    if (filtered.length === 0 && currentVariants.length > 0) {
      hVariant.innerHTML = '<option value="">No exact variant for this Year/Fuel (Showing all)</option>';
      filtered = currentVariants;
    } else {
      hVariant.innerHTML = '<option value="">Select Specific Variant...</option>';
    }

    filtered.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.name} • ${v.fuel_type} • ${v.transmission} (${v.year_from}-${v.year_to})`;
      opt.dataset.engine = v.engine_cc ? `${v.engine_cc}cc (${v.power_hp || ''} hp)` : '';
      opt.dataset.fuel = v.fuel_type;
      opt.dataset.name = v.name;
      hVariant.appendChild(opt);
    });

    hVariant.disabled = false;
    updatePreview();
  };

  const updatePreview = () => {
    if (!hVariant || !hPreviewCard) return;
    const selectedOpt = hVariant.selectedOptions[0];
    if (hVariant.value && selectedOpt) {
      const makeText = hMake.options[hMake.selectedIndex]?.text || '';
      const modelText = hModel.options[hModel.selectedIndex]?.text || '';
      const variantName = selectedOpt.dataset.name || selectedOpt.text;
      const fuel = selectedOpt.dataset.fuel || '';

      if (hPreviewName) {
        hPreviewName.textContent = `${makeText} ${modelText}`;
      }
      if (hPreviewMeta) {
        hPreviewMeta.textContent = `${variantName} (${fuel})`;
      }
      hPreviewCard.style.display = 'flex';
      if (hSubmit) hSubmit.disabled = false;
    } else {
      if (hPreviewCard) hPreviewCard.style.display = 'none';
      if (hSubmit) hSubmit.disabled = true;
    }
  };

  if (hMake && hModel && hVariant) {
    // 1. Manufacturer Changed
    hMake.addEventListener('change', async () => {
      const makeId = hMake.value;
      hModel.innerHTML = '<option value="">Loading Models...</option>';
      hModel.disabled = true;
      if (hYear) { hYear.innerHTML = '<option value="">Select Year...</option>'; hYear.disabled = true; }
      if (hFuel) { hFuel.innerHTML = '<option value="">Select Fuel...</option>'; hFuel.disabled = true; }
      hVariant.innerHTML = '<option value="">Select Variant...</option>';
      hVariant.disabled = true;
      if (hSubmit) hSubmit.disabled = true;
      if (hPreviewCard) hPreviewCard.style.display = 'none';

      if (!makeId) {
        hModel.innerHTML = '<option value="">Select Model...</option>';
        return;
      }

      try {
        const res = await fetch(`/vehicles/api/models/?make_id=${makeId}`);
        const data = await res.json();
        let opts = '<option value="">Select Model...</option>';
        data.models.forEach(m => {
          opts += `<option value="${m.id}">${m.name} (${m.body_type})</option>`;
        });
        hModel.innerHTML = opts;
        hModel.disabled = false;
      } catch (err) {
        hModel.innerHTML = '<option value="">Error loading models</option>';
      }
    });

    // 2. Model Changed
    hModel.addEventListener('change', async () => {
      const modelId = hModel.value;
      if (hYear) { hYear.innerHTML = '<option value="">Loading...</option>'; hYear.disabled = true; }
      if (hFuel) { hFuel.innerHTML = '<option value="">Loading...</option>'; hFuel.disabled = true; }
      hVariant.innerHTML = '<option value="">Loading Variants...</option>';
      hVariant.disabled = true;
      if (hSubmit) hSubmit.disabled = true;
      if (hPreviewCard) hPreviewCard.style.display = 'none';

      if (!modelId) {
        hVariant.innerHTML = '<option value="">Select Variant...</option>';
        return;
      }

      try {
        const res = await fetch(`/vehicles/api/variants/?model_id=${modelId}`);
        const data = await res.json();
        currentVariants = data.variants || [];

        // Extract years and fuels
        const yearsSet = new Set();
        const fuelsSet = new Set();

        currentVariants.forEach(v => {
          if (v.fuel_type) fuelsSet.add(v.fuel_type);
          if (v.year_from && v.year_to) {
            for (let y = v.year_from; y <= v.year_to; y++) {
              yearsSet.add(y);
            }
          }
        });

        // Populate Years
        if (hYear) {
          const sortedYears = Array.from(yearsSet).sort((a, b) => b - a);
          let yOpts = '<option value="">All Production Years</option>';
          sortedYears.forEach(y => { yOpts += `<option value="${y}">${y}</option>`; });
          hYear.innerHTML = yOpts;
          hYear.disabled = false;
        }

        // Populate Fuels
        if (hFuel) {
          let fOpts = '<option value="">All Fuel Types</option>';
          fuelsSet.forEach(f => { fOpts += `<option value="${f}">${f}</option>`; });
          hFuel.innerHTML = fOpts;
          hFuel.disabled = false;
        }

        filterAndPopulateVariants();
      } catch (err) {
        hVariant.innerHTML = '<option value="">Error loading variants</option>';
      }
    });

    // 3. Year / Fuel Filters Changed
    if (hYear) hYear.addEventListener('change', filterAndPopulateVariants);
    if (hFuel) hFuel.addEventListener('change', filterAndPopulateVariants);

    // 4. Variant Selected
    hVariant.addEventListener('change', updatePreview);
  }

  // 2. Featured Products Category Filter Tabs
  const filterTabs = document.querySelectorAll('.filter-tab-pill');
  const productCards = document.querySelectorAll('.product-filterable-item');
  const emptyFilterMsg = document.getElementById('category-filter-empty-msg');

  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetCategory = tab.dataset.category;
      let visibleCount = 0;

      productCards.forEach(card => {
        const cardCategory = card.dataset.category;
        if (targetCategory === 'all' || cardCategory === targetCategory) {
          card.style.display = 'flex';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      if (emptyFilterMsg) {
        emptyFilterMsg.style.display = visibleCount === 0 ? 'block' : 'none';
      }
    });
  });

  // 3. Asynchronous Add to Cart with Animated Feedback
  const addToCartForms = document.querySelectorAll('.ajax-add-to-cart-form');
  addToCartForms.forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalHtml = submitBtn ? submitBtn.innerHTML : '';

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader" style="width:16px; height:16px; animation:spin 1s linear infinite;"></i>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }

      try {
        const formData = new FormData(form);
        const actionUrl = form.getAttribute('action');

        const response = await fetch(actionUrl, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          // Update cart badge in navbar
          const cartCountBadges = document.querySelectorAll('#nav-cart-count');
          cartCountBadges.forEach(badge => {
            badge.textContent = data.cart_count;
            badge.style.display = 'inline-flex';
          });

          // Show floating toast
          if (window.showToast) {
            window.showToast(data.message || 'Product added to shopping cart!', 'success');
          }

          if (submitBtn) {
            submitBtn.innerHTML = '<i data-lucide="check" style="width:16px; height:16px;"></i> Added';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            setTimeout(() => {
              submitBtn.innerHTML = originalHtml;
              submitBtn.disabled = false;
              if (typeof lucide !== 'undefined') lucide.createIcons();
            }, 1800);
          }
        } else {
          form.submit(); // fallback to normal submit
        }
      } catch (err) {
        console.error('AJAX cart error:', err);
        form.submit(); // fallback
      }
    });
  });

  // 4. Interactive Wishlist Toggle
  const wishlistButtons = document.querySelectorAll('.product-wishlist-toggle');
  wishlistButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const productId = btn.dataset.productId;
      if (!productId) return;

      try {
        const res = await fetch(`/shop/wishlist/toggle/${productId}/`, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.getCookie('csrftoken') || ''
          }
        });

        if (res.ok) {
          const data = await res.json();
          const isAdded = data.action === 'added';
          btn.classList.toggle('active', isAdded);

          const heartIcon = btn.querySelector('i');
          if (heartIcon) {
            heartIcon.style.fill = isAdded ? '#ef4444' : 'none';
            heartIcon.style.color = isAdded ? '#ef4444' : 'currentColor';
          }

          // Update navbar wishlist count
          const wishlistBadges = document.querySelectorAll('#nav-wishlist-count');
          wishlistBadges.forEach(badge => {
            badge.textContent = data.wishlist_count;
            badge.style.display = data.wishlist_count > 0 ? 'inline-flex' : 'none';
          });

          if (window.showToast) {
            window.showToast(data.message, isAdded ? 'success' : 'info');
          }
        } else {
          window.showToast('Please sign in to save parts to your wishlist', 'info');
        }
      } catch (err) {
        window.showToast('Please sign in to save parts to your wishlist', 'info');
      }
    });
  });

  // 5. Interactive Maintenance Reminders Milestone Tabs
  const milestoneData = {
    '5000': {
      title: '5,000 KM — Initial Service & Safety Health Check',
      description: 'Essential quick inspection ensuring all moving parts have seated properly without excessive early wear.',
      items: [
        'Tire Rotation & Tread Depth Assessment',
        'Engine Oil Level & Viscosity Inspection',
        'Coolant & Windshield Fluid Top-up',
        'Brake Pad Lining & Rotor Friction Check',
        'Battery Terminal Cleaning & Voltage Test',
        'Underbody & Exhaust Suspension Mount Inspection'
      ],
      estCost: '₹899 – ₹1,499'
    },
    '10000': {
      title: '10,000 KM — Periodic Comprehensive Maintenance',
      description: 'Crucial milestone to refresh lubricant fluids, engine air filtration, and wheel alignment.',
      items: [
        'Full Synthetic Engine Oil Replacement (0W-20 / 5W-30)',
        'OEM Engine Oil Filter & Sump Washer Change',
        'Engine Air Filter & Cabin AC Filter Replacement',
        'Computerized 3D Wheel Alignment & Balancing',
        'Complete Brake Caliper Cleaning & Greasing',
        'OBD-II Diagnostic Error Code Scan'
      ],
      estCost: '₹3,499 – ₹5,999'
    },
    '20000': {
      title: '20,000 KM — Major System Service & Fluid Overhaul',
      description: 'Protective overhaul preventing moisture contamination in brake hydraulic circuits and steering system.',
      items: [
        'DOT 4 Brake Fluid Complete Pressure Flush & Bleed',
        'Engine Coolant Radiator Drain & Refill',
        'Fuel Filter Replacement (Diesel / Direct Injection)',
        'Suspension Bushing & Strut Inspection',
        'Air Conditioning Coil Disinfection & Antimicrobial Treatment',
        'Throttle Body Cleaning & Throttle Response Calibration'
      ],
      estCost: '₹6,499 – ₹9,899'
    },
    '40000': {
      title: '40,000 KM — Advanced Transmission & Ignition Overhaul',
      description: 'Comprehensive powertrain preservation for optimum fuel economy, acceleration, and transmission longevity.',
      items: [
        'Iridium / Platinum Spark Plugs Replacement',
        'Transmission Gear Oil / Automatic ATF Fluid Exchange',
        'Accessory Drive Belt (Serpentine Belt) Condition Check',
        'Engine Mount & Transmission Dampener Vibration Check',
        'Full Brake Disc Rotor Thickness Measurement & Facing',
        'Catalytic Converter & Emission Sensor Diagnostic'
      ],
      estCost: '₹11,999 – ₹16,500'
    }
  };

  const milestoneBtns = document.querySelectorAll('.milestone-tab-btn');
  const milestoneTitle = document.getElementById('milestone-title');
  const milestoneDesc = document.getElementById('milestone-desc');
  const milestoneCost = document.getElementById('milestone-cost');
  const milestoneList = document.getElementById('milestone-list');

  milestoneBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      milestoneBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const km = btn.dataset.km;
      const data = milestoneData[km];
      if (!data) return;

      if (milestoneTitle) milestoneTitle.textContent = data.title;
      if (milestoneDesc) milestoneDesc.textContent = data.description;
      if (milestoneCost) milestoneCost.textContent = data.estCost;

      if (milestoneList) {
        milestoneList.innerHTML = '';
        data.items.forEach(item => {
          const li = document.createElement('li');
          li.innerHTML = `<i data-lucide="check-circle"></i><span>${item}</span>`;
          milestoneList.appendChild(li);
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    });
  });
});
