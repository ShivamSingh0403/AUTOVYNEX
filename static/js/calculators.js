/**
 * AUTOVYNEX — Automotive Engineering Calculators
 * 1. Fuel Cost Calculator
 * 2. Car Valuation Estimator (Documented Sample Depreciation Model)
 * 3. 5-Year Total Cost of Ownership (TCO) Calculator
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- 1. Fuel Cost Calculator ---
  const fuelForm = document.getElementById('fuel-calc-form');
  if (fuelForm) {
    const dailyDistanceInput = document.getElementById('fuel-daily-km');
    const mileageInput = document.getElementById('fuel-mileage');
    const fuelPriceInput = document.getElementById('fuel-price-per-l');

    function updateFuelCalc() {
      const dailyKm = parseFloat(dailyDistanceInput.value) || 0;
      const mileage = parseFloat(mileageInput.value) || 1;
      const fuelPrice = parseFloat(fuelPriceInput.value) || 0;

      const dailyLitres = dailyKm / mileage;
      const dailyCost = dailyLitres * fuelPrice;
      const monthlyCost = dailyCost * 30;
      const annualCost = dailyCost * 365;

      const dailyOut = document.getElementById('fuel-out-daily');
      const monthlyOut = document.getElementById('fuel-out-monthly');
      const annualOut = document.getElementById('fuel-out-annual');
      const costPerKmOut = document.getElementById('fuel-out-per-km');

      if (dailyOut) dailyOut.textContent = `₹${Math.round(dailyCost).toLocaleString('en-IN')}`;
      if (monthlyOut) monthlyOut.textContent = `₹${Math.round(monthlyCost).toLocaleString('en-IN')}`;
      if (annualOut) annualOut.textContent = `₹${Math.round(annualCost).toLocaleString('en-IN')}`;
      if (costPerKmOut) costPerKmOut.textContent = `₹${(dailyCost / (dailyKm || 1)).toFixed(2)} / km`;
    }

    dailyDistanceInput.addEventListener('input', updateFuelCalc);
    mileageInput.addEventListener('input', updateFuelCalc);
    fuelPriceInput.addEventListener('input', updateFuelCalc);
    updateFuelCalc();
  }

  // --- 2. Car Valuation Estimator ---
  const valuationForm = document.getElementById('car-valuation-form');
  if (valuationForm) {
    valuationForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const originalPrice = parseFloat(document.getElementById('val-original-price').value) || 1000000;
      const regYear = parseInt(document.getElementById('val-reg-year').value) || 2021;
      const odometerKm = parseFloat(document.getElementById('val-odometer').value) || 35000;
      const owners = parseInt(document.getElementById('val-owners').value) || 1;
      const condition = parseFloat(document.getElementById('val-condition').value) || 0.95;

      const currentYear = 2026;
      const age = Math.max(0, currentYear - regYear);

      let baseDepreciation = 0;
      if (age === 0) baseDepreciation = 0.08;
      else if (age === 1) baseDepreciation = 0.16;
      else if (age === 2) baseDepreciation = 0.26;
      else if (age === 3) baseDepreciation = 0.36;
      else if (age === 4) baseDepreciation = 0.45;
      else if (age === 5) baseDepreciation = 0.53;
      else baseDepreciation = Math.min(0.82, 0.53 + (age - 5) * 0.06);

      const expectedKm = Math.max(1, age) * 12000;
      const kmDiff = odometerKm - expectedKm;
      const mileageAdjustment = (kmDiff / 10000) * 0.02;

      const ownersAdjustment = (owners - 1) * 0.05;

      const totalDeprecFactor = Math.min(0.88, Math.max(0.1, baseDepreciation + mileageAdjustment + ownersAdjustment));
      let estimatedValue = originalPrice * (1 - totalDeprecFactor) * condition;
      
      const fairLow = Math.round(estimatedValue * 0.95);
      const fairHigh = Math.round(estimatedValue * 1.05);

      const resBox = document.getElementById('valuation-results');
      if (resBox) {
        resBox.style.display = 'block';
        document.getElementById('val-estimate-main').textContent = `₹${Math.round(estimatedValue).toLocaleString('en-IN')}`;
        document.getElementById('val-estimate-range').textContent = `₹${fairLow.toLocaleString('en-IN')} - ₹${fairHigh.toLocaleString('en-IN')}`;
        document.getElementById('val-deprec-percent').textContent = `${Math.round(totalDeprecFactor * 100)}%`;
        resBox.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }

  // --- 3. Ownership Cost (TCO) Calculator ---
  const tcoForm = document.getElementById('tco-calc-form');
  if (tcoForm) {
    function calculateTCO() {
      const carPrice = parseFloat(document.getElementById('tco-car-price').value) || 1200000;
      const annualKm = parseFloat(document.getElementById('tco-annual-km').value) || 15000;
      const fuelEfficiency = parseFloat(document.getElementById('tco-mileage').value) || 16;
      const fuelRate = parseFloat(document.getElementById('tco-fuel-rate').value) || 102;
      const annualInsurance = parseFloat(document.getElementById('tco-insurance').value) || 25000;
      const annualService = parseFloat(document.getElementById('tco-service').value) || 12000;

      const total5YrKm = annualKm * 5;
      const totalFuelCost = (total5YrKm / fuelEfficiency) * fuelRate;
      const totalInsurance = annualInsurance * 5 * 0.92;
      const totalService = annualService * 5 * 1.1;
      const tyreReplacement = total5YrKm > 40000 ? 32000 : 0;
      const depreciationLoss = carPrice * 0.52;
      const grandTotal5Yr = carPrice + totalFuelCost + totalInsurance + totalService + tyreReplacement - (carPrice - depreciationLoss);
      const costPerKm = grandTotal5Yr / (total5YrKm || 1);

      document.getElementById('tco-out-5yr-fuel').textContent = `₹${Math.round(totalFuelCost).toLocaleString('en-IN')}`;
      document.getElementById('tco-out-5yr-service').textContent = `₹${Math.round(totalService).toLocaleString('en-IN')}`;
      document.getElementById('tco-out-5yr-total').textContent = `₹${Math.round(grandTotal5Yr).toLocaleString('en-IN')}`;
      document.getElementById('tco-out-per-km').textContent = `₹${costPerKm.toFixed(2)} / km`;
    }

    const tcoInputs = tcoForm.querySelectorAll('input');
    tcoInputs.forEach(input => input.addEventListener('input', calculateTCO));
    calculateTCO();
  }
});
