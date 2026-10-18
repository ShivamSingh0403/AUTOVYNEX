/**
 * AUTOVYNEX — AI Car Help Diagnostic Engine
 * Clearly labeled rule-based diagnostic assistant ready for future LLM integration.
 */

document.addEventListener('DOMContentLoaded', () => {
  const symptomButtons = document.querySelectorAll('.symptom-preset-btn');
  const customQueryInput = document.getElementById('ai-custom-query');
  const analyzeBtn = document.getElementById('ai-analyze-btn');
  const chatHistory = document.getElementById('ai-chat-thread');

  const KNOWLEDGE_BASE = {
    'engine_light': {
      title: 'Check Engine Warning Light Illuminated',
      urgency: 'Urgent / Moderate',
      badgeClass: 'badge-unconfirmed',
      possibleCauses: [
        'Faulty Oxygen (O2) Sensor or Mass Airflow (MAF) sensor',
        'Loose or cracked fuel filler cap causing EVAP pressure loss',
        'Catalytic converter efficiency below threshold',
        'Ignition coil or spark plug misfire on one of the cylinders'
      ],
      safeChecks: [
        'Check if the gas cap is tightly clicked shut.',
        'Note whether the light is steady or flashing. (Flashing = immediate misfire, stop driving!)',
        'Inspect engine oil dipstick level and engine coolant reservoir when the car is cool.'
      ],
      urgentWarning: 'If the Check Engine Light is FLASHING or accompanied by heavy shuddering/loss of power, pull over safely immediately to prevent catalytic converter destruction.',
      recommendation: 'Connect an OBD-II scanner to read active trouble codes (DTCs). Schedule a comprehensive diagnostic check with an AUTOVYNEX verified partner.',
      bookingCategory: 'general'
    },
    'battery_dead': {
      title: 'Engine Cranks Slowly or Will Not Start',
      urgency: 'Moderate / Action Required',
      badgeClass: 'badge-unconfirmed',
      possibleCauses: [
        'Lead-acid battery discharge or dead cell (exceeded 3-4 year lifespan)',
        'Corroded or loose battery terminal clamps',
        'Alternator failure failing to recharge battery while running',
        'Parasitic electrical draw from an accessory or dashcam'
      ],
      safeChecks: [
        'Check for white or green powdery corrosion on the positive/negative terminals.',
        'Turn on headlights: if they are dim and turn off during crank attempt, battery charge is depleted.',
        'Attempt a safe jump start using high-grade jumper cables or a portable booster.'
      ],
      urgentWarning: 'Never attempt to jump start a battery that is bloated, leaking acid, or emitting a rotten egg smell.',
      recommendation: 'Conduct a digital battery load & CCA test. Replace battery if health test reports below 60%.',
      bookingCategory: 'battery'
    },
    'brake_noise': {
      title: 'Unusual Squealing, Grinding, or Scraping Brakes',
      urgency: 'Critical Safety Item',
      badgeClass: 'badge-incompatible',
      possibleCauses: [
        'Worn brake pads reaching built-in acoustic wear indicators (squeal)',
        'Severe metal-on-metal contact between backing plate and brake disc (grinding)',
        'Glazed brake rotors or trapped road grit/pebbles in calliper',
        'Warped brake discs causing pulsation through the brake pedal'
      ],
      safeChecks: [
        'Visually inspect brake pad thickness through alloy wheel spokes (minimum safe thickness is 3mm).',
        'Check brake fluid reservoir level under the hood.',
        'Notice if the vehicle pulls to one side when applying brakes.'
      ],
      urgentWarning: 'A grinding metal sound means friction material is completely gone. Braking distances are severely compromised. Do not drive at high speeds!',
      recommendation: 'Replace front/rear brake pads and inspect brake discs for resurfacing or replacement.',
      bookingCategory: 'brakes'
    },
    'overheating': {
      title: 'Engine Temperature Gauge in Red / Steam from Hood',
      urgency: 'Critical Immediate Hazard',
      badgeClass: 'badge-incompatible',
      possibleCauses: [
        'Radiator coolant leak (split hose, cracked radiator, or water pump seal)',
        'Failed thermostat valve stuck in closed position',
        'Radiator cooling fan motor or relay failure',
        'Blown cylinder head gasket'
      ],
      safeChecks: [
        'Immediately pull over safely, turn on heater to max (helps bleed engine heat), and turn off engine.',
        'DO NOT OPEN THE RADIATOR CAP WHILE ENGINE IS HOT! Pressurized boiling coolant will cause severe burns.',
        'Look beneath the car for coolant puddles (pink, green, or blue fluid).'
      ],
      urgentWarning: 'Continuing to drive an overheating engine will warp the cylinder head and cause catastrophic engine seizure costing lakhs.',
      recommendation: 'Do not continue driving. Request an AUTOVYNEX flatbed tow directly to a workshop.',
      bookingCategory: 'mechanical'
    },
    'tyre_pressure': {
      title: 'Tyre Pressure Monitoring (TPMS) Warning or Soft Tyre',
      urgency: 'Moderate / Immediate Attention',
      badgeClass: 'badge-verified',
      possibleCauses: [
        'Slow puncture caused by nail or screw in tyre tread',
        'Leaking tyre bead or damaged valve stem',
        'Significant ambient temperature drop causing pressure reduction (approx 1 PSI per 10°F)',
        'Rim bent from hitting a deep pothole'
      ],
      safeChecks: [
        'Visually check all four tyres for bulging sidewalls, punctures, or uneven tread.',
        'Use an accurate digital pressure gauge when tyres are cold.',
        'Consult the manufacturer recommended tyre pressure sticker on the driver side door B-pillar.'
      ],
      urgentWarning: 'Never drive on a tyre with zero pressure; doing so permanently destroys the tyre sidewall structure and damages the alloy rim.',
      recommendation: 'Visit an AUTOVYNEX tyre care center for puncture repair or wheel balancing & alignment.',
      bookingCategory: 'tyre'
    }
  };

  function renderDiagnosis(data) {
    if (!chatHistory) return;
    const responseCard = document.createElement('div');
    responseCard.className = 'card';
    responseCard.style.marginTop = '20px';
    responseCard.style.borderColor = 'var(--color-primary-light)';
    responseCard.style.background = 'var(--bg-surface-elevated)';

    responseCard.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <h3 style="font-size:1.25rem; color:var(--text-main);">${data.title}</h3>
        <span class="badge ${data.badgeClass}">${data.urgency}</span>
      </div>
      
      <div class="demo-academic-badge" style="margin-bottom:16px;">
        <i data-lucide="info" style="width:14px; height:14px;"></i>
        <span>Notice:</span> Rule-based diagnostic estimation. Not a definitive mechanical guarantee.
      </div>

      <div style="margin-bottom:16px;">
        <h4 style="font-size:0.95rem; margin-bottom:6px; color:var(--color-primary);">Probable Explanations:</h4>
        <ul style="padding-left:20px; font-size:0.92rem; color:var(--text-muted); line-height:1.6;">
          ${data.possibleCauses.map(c => `<li>${c}</li>`).join('')}
        </ul>
      </div>

      <div style="margin-bottom:16px;">
        <h4 style="font-size:0.95rem; margin-bottom:6px; color:#10b981;">Safe Basic Checks You Can Perform:</h4>
        <ul style="padding-left:20px; font-size:0.92rem; color:var(--text-muted); line-height:1.6;">
          ${data.safeChecks.map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>

      <div class="alert-banner alert-warning" style="margin-bottom:16px;">
        <i data-lucide="alert-triangle"></i>
        <div><strong>Safety Critical:</strong> ${data.urgentWarning}</div>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; padding-top:16px; border-top:1px solid var(--border-subtle);">
        <div style="font-size:0.88rem; color:var(--text-muted); max-width:400px;">
          <strong>Recommendation:</strong> ${data.recommendation}
        </div>
        <a href="/services/book/?category=${data.bookingCategory}" class="btn btn-primary btn-sm">
          <i data-lucide="calendar"></i> Book Qualified Inspection
        </a>
      </div>
    `;

    chatHistory.appendChild(responseCard);
    if (typeof lucide !== 'undefined') lucide.createIcons();
    responseCard.scrollIntoView({ behavior: 'smooth' });
  }

  symptomButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const symptomKey = btn.getAttribute('data-symptom');
      if (KNOWLEDGE_BASE[symptomKey]) {
        renderDiagnosis(KNOWLEDGE_BASE[symptomKey]);
      }
    });
  });

  if (analyzeBtn && customQueryInput) {
    analyzeBtn.addEventListener('click', () => {
      const query = customQueryInput.value.toLowerCase().trim();
      if (!query) return;

      let matched = null;
      if (query.includes('brake') || query.includes('squeak') || query.includes('grind') || query.includes('stopping')) {
        matched = KNOWLEDGE_BASE['brake_noise'];
      } else if (query.includes('battery') || query.includes('start') || query.includes('crank') || query.includes('dead')) {
        matched = KNOWLEDGE_BASE['battery_dead'];
      } else if (query.includes('heat') || query.includes('hot') || query.includes('steam') || query.includes('coolant')) {
        matched = KNOWLEDGE_BASE['overheating'];
      } else if (query.includes('tyre') || query.includes('tire') || query.includes('puncture') || query.includes('air')) {
        matched = KNOWLEDGE_BASE['tyre_pressure'];
      } else {
        matched = KNOWLEDGE_BASE['engine_light'];
      }

      renderDiagnosis(matched);
      customQueryInput.value = '';
    });
  }
});
