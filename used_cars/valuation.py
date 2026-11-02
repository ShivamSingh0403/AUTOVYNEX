"""
AUTOVYNEX Rule-Based Resale Valuation Engine
Transparent, configurable, and honest vehicle valuation calculator.
"""

from decimal import Decimal
import json
from django.db.models import Avg


# Standard benchmark ex-showroom / base invoice estimates for popular Indian models
MODEL_BENCHMARKS = {
    'maruti suzuki': {
        'swift': 820000,
        'baleno': 920000,
        'brezza': 1250000,
        'grand vitara': 1650000,
        'ertiga': 1150000,
        'dzire': 870000,
        'wagon r': 680000,
        'alto': 480000,
        'fronx': 1050000,
        'jimny': 1400000,
    },
    'hyundai': {
        'creta': 1600000,
        'i20': 950000,
        'venue': 1150000,
        'verna': 1500000,
        'tucson': 3200000,
        'alcazar': 1950000,
        'aura': 830000,
        'grand i10 nios': 750000,
        'exter': 880000,
    },
    'tata': {
        'nexon': 1300000,
        'punch': 850000,
        'harrier': 2100000,
        'safari': 2400000,
        'altroz': 880000,
        'tiago': 660000,
        'tigor': 780000,
        'curvv': 1600000,
    },
    'mahindra': {
        'thar': 1600000,
        'scorpio-n': 1950000,
        'xuv700': 2300000,
        'bolero': 1050000,
        'xuv300': 1150000,
        'xuv 3xo': 1100000,
    },
    'toyota': {
        'fortuner': 3800000,
        'innova crysta': 2500000,
        'innova hycross': 2800000,
        'glanza': 920000,
        'urban cruiser hyryder': 1700000,
        'camry': 4600000,
        'hilux': 3600000,
    },
    'honda': {
        'city': 1550000,
        'amaze': 870000,
        'elevate': 1450000,
    },
    'volkswagen': {
        'virtus': 1650000,
        'taigun': 1750000,
        'tiguan': 3600000,
    },
    'skoda': {
        'slavia': 1650000,
        'kushaq': 1750000,
        'kodiaq': 3900000,
        'superb': 4200000,
    },
    'kia': {
        'seltos': 1650000,
        'sonet': 1200000,
        'carens': 1450000,
        'ev6': 6500000,
    },
    'bmw': {
        '3 series': 5500000,
        '5 series': 7200000,
        'x1': 5100000,
        'x3': 6800000,
        'x5': 9800000,
    },
    'mercedes-benz': {
        'c-class': 6200000,
        'e-class': 8200000,
        'gla': 5200000,
        'glc': 7600000,
    }
}


def estimate_resale_value(
    make_name: str,
    model_name: str,
    year: int,
    variant_name: str = '',
    fuel_type: str = 'Petrol',
    transmission: str = 'Manual',
    mileage: int = 35000,
    owners_count: int = 1,
    condition: str = 'good',
    city: str = 'Bengaluru',
    user_orig_price: float = None,
    current_year: int = 2026
) -> dict:
    """
    Transparent, rule-based vehicle valuation logic with supporting marketplace context.
    """
    from .models import UsedCarListing

    make_clean = (make_name or '').strip().lower()
    model_clean = (model_name or '').strip().lower()

    # 1. Base Price Benchmark Resolution
    base_benchmark = None
    if user_orig_price and float(user_orig_price) > 50000:
        base_benchmark = float(user_orig_price)
        base_source = f"User provided original price: ₹{base_benchmark:,.0f}"
    else:
        # Search benchmark catalog
        make_dict = MODEL_BENCHMARKS.get(make_clean, {})
        for k, v in make_dict.items():
            if k in model_clean or model_clean in k:
                base_benchmark = v
                break

        if not base_benchmark:
            # Fallback based on typical Indian automotive segment
            if any(w in model_clean for w in ['suv', 'thar', 'fortuner', 'harrier', 'safari', 'xuv']):
                base_benchmark = 1600000
            elif any(w in model_clean for w in ['sedan', 'city', 'verna', 'virtus', 'slavia']):
                base_benchmark = 1350000
            elif any(w in model_clean for w in ['hatch', 'swift', 'i10', 'i20', 'tiago', 'baleno']):
                base_benchmark = 850000
            else:
                base_benchmark = 1100000
        base_source = f"Estimated OEM benchmark invoice baseline: ₹{base_benchmark:,.0f}"

    # 2. Age-Based Standard Depreciation
    age = max(0, current_year - int(year))
    if age == 0:
        age_dep = 0.08  # Brand new or showroom demo
    elif age == 1:
        age_dep = 0.16
    elif age == 2:
        age_dep = 0.25
    elif age == 3:
        age_dep = 0.33
    elif age == 4:
        age_dep = 0.41
    elif age == 5:
        age_dep = 0.49
    elif age == 6:
        age_dep = 0.56
    elif age == 7:
        age_dep = 0.62
    else:
        age_dep = min(0.78, 0.62 + (age - 7) * 0.03)

    # 3. Mileage Factor (Standard Indian usage is ~12,000 km per year)
    expected_km = max(10000, age * 12000)
    mileage_diff = mileage - expected_km
    if expected_km > 0:
        mileage_ratio = mileage_diff / float(expected_km)
    else:
        mileage_ratio = 0.0

    if mileage_ratio > 0:
        mileage_impact = -min(12.0, mileage_ratio * 9.0)
    else:
        mileage_impact = min(6.0, abs(mileage_ratio) * 6.0)

    # 4. Ownership History Factor
    owners_val = max(1, int(owners_count or 1))
    if owners_val == 1:
        owner_impact = 0.0
        owner_desc = "Single owner vehicle (standard market benchmark)"
    elif owners_val == 2:
        owner_impact = -6.0
        owner_desc = "Second owner vehicle (moderate resale deduction)"
    elif owners_val == 3:
        owner_impact = -13.0
        owner_desc = "Third owner vehicle (higher market resistance)"
    else:
        owner_impact = -20.0
        owner_desc = f"{owners_val}+ previous owners (substantial multi-owner deduction)"

    # 5. Condition Multiplier
    cond_clean = (condition or 'good').lower()
    if cond_clean == 'excellent':
        condition_impact = +4.5
        condition_desc = "Showroom condition, immaculate bodywork & complete service records"
    elif cond_clean == 'very_good':
        condition_impact = +2.0
        condition_desc = "Very good condition, pristine powertrain and minor cosmetic signs"
    elif cond_clean == 'good':
        condition_impact = 0.0
        condition_desc = "Good road-worthy condition with normal age-appropriate wear"
    elif cond_clean == 'fair':
        condition_impact = -8.0
        condition_desc = "Fair condition with visible scratches, minor dents or wear on consumables"
    else:
        condition_impact = -18.0
        condition_desc = "Requires mechanical repairs, body restoration or major service"

    # 6. Fuel Type & Powertrain Factor
    fuel_clean = (fuel_type or 'Petrol').lower()
    trans_clean = (transmission or 'Manual').lower()
    powertrain_impact = 0.0
    powertrain_notes = []

    if 'automatic' in trans_clean:
        powertrain_impact += 3.0
        powertrain_notes.append("Automatic transmission premium (+3.0%)")

    city_clean = (city or '').strip().lower()
    is_ncr = any(c in city_clean for c in ['delhi', 'ncr', 'gurugram', 'noida', 'faridabad', 'ghaziabad'])

    if 'diesel' in fuel_clean:
        if is_ncr and age >= 6:
            powertrain_impact -= 9.0
            powertrain_notes.append("Delhi-NCR 10-year diesel rule depreciation (-9.0%)")
        else:
            powertrain_impact += 1.0
            powertrain_notes.append("High torque highway diesel demand (+1.0%)")
    elif 'cng' in fuel_clean:
        powertrain_impact += 2.0
        powertrain_notes.append("Economical CNG running cost bonus (+2.0%)")
    elif 'ev' in fuel_clean or 'electric' in fuel_clean:
        if age <= 3:
            powertrain_impact += 2.5
            powertrain_notes.append("EV low maintenance advantage (+2.5%)")
        else:
            powertrain_impact -= 5.0
            powertrain_notes.append("Battery age wear uncertainty (-5.0%)")

    # Net adjustment percentage
    net_factor_pct = (mileage_impact + owner_impact + condition_impact + powertrain_impact) / 100.0

    # Base calculated value
    age_adjusted_val = base_benchmark * (1.0 - age_dep)
    fair_market_val = max(30000.0, age_adjusted_val * (1.0 + net_factor_pct))

    # Calculate realistic bounds
    min_val = round(fair_market_val * 0.93, -2)
    max_val = round(fair_market_val * 1.07, -2)
    fair_market_val = round(fair_market_val, -2)

    # 7. Actual Database Supporting Context
    comparables_qs = UsedCarListing.objects.filter(
        make_name__iexact=make_name,
        model_name__icontains=model_name.split()[0] if model_name else '',
        is_approved=True
    )
    comparables_count = comparables_qs.count()
    comparables_avg = None
    if comparables_count > 0:
        avg_res = comparables_qs.aggregate(avg=Avg('expected_price'))['avg']
        if avg_res:
            comparables_avg = round(float(avg_res), -2)

    if comparables_count >= 2:
        market_context_note = (
            f"Found {comparables_count} comparable {make_name} {model_name} listings on the AUTOVYNEX "
            f"Marketplace with an average asking price of ₹{comparables_avg:,.0f}."
        )
    else:
        market_context_note = (
            f"Limited direct marketplace listings ({comparables_count}) for this exact model on AUTOVYNEX. "
            f"This estimate is computed through rule-based Indian automotive depreciation curves."
        )

    # 8. Factors Breakdown
    factors = [
        {
            'name': 'Manufacturing Year & Age',
            'impact': f"-{age_dep * 100:.0f}%",
            'detail': f"{age} years old ({year} model) benchmark depreciation",
            'type': 'negative'
        },
        {
            'name': 'Kilometres Driven',
            'impact': f"{mileage_impact:+.1f}%",
            'detail': f"{mileage:,} KM driven (Standard for age: ~{expected_km:,} KM)",
            'type': 'positive' if mileage_impact >= 0 else 'negative'
        },
        {
            'name': 'Ownership History',
            'impact': f"{owner_impact:+.1f}%",
            'detail': owner_desc,
            'type': 'neutral' if owner_impact == 0 else 'negative'
        },
        {
            'name': 'Reported Vehicle Condition',
            'impact': f"{condition_impact:+.1f}%",
            'detail': condition_desc,
            'type': 'positive' if condition_impact > 0 else ('negative' if condition_impact < 0 else 'neutral')
        },
        {
            'name': 'Powertrain & Metro Context',
            'impact': f"{powertrain_impact:+.1f}%",
            'detail': "; ".join(powertrain_notes) if powertrain_notes else f"{transmission} {fuel_type} standard baseline",
            'type': 'positive' if powertrain_impact > 0 else ('negative' if powertrain_impact < 0 else 'neutral')
        }
    ]

    limitations = [
        "This estimation is derived using transparent algorithmic depreciation benchmarks and seller-inputted variables.",
        "It does NOT constitute a certified mechanical appraisal, a legal valuation, or a guaranteed cash buyback offer from AUTOVYNEX.",
        "Physical inspection results (chassis alignment, engine compression, paint thickness, tyre tread) will influence final market transaction value.",
        "Insurance claim history and active registration status directly impact real buyer willingness to pay."
    ]

    next_steps = [
        "Schedule a comprehensive physical inspection at an AUTOVYNEX TechCenter Indiranagar or Koramangala.",
        "List your vehicle for free on the AUTOVYNEX Pre-Owned Marketplace to connect with direct verified buyers.",
        "Upload crisp exterior & interior photographs along with transparent service history to maximize buyer confidence."
    ]

    return {
        'make_name': make_name,
        'model_name': model_name,
        'year': year,
        'variant_name': variant_name,
        'fuel_type': fuel_type,
        'transmission': transmission,
        'mileage': mileage,
        'owners_count': owners_count,
        'condition': condition,
        'city': city,
        'base_source': base_source,
        'base_benchmark': base_benchmark,
        'estimated_min': min_val,
        'estimated_max': max_val,
        'fair_market_value': fair_market_val,
        'comparables_count': comparables_count,
        'comparables_avg': comparables_avg,
        'market_context_note': market_context_note,
        'factors': factors,
        'factors_json': json.dumps(factors),
        'limitations': limitations,
        'next_steps': next_steps,
    }
