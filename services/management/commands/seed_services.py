import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from services.models import (
    ServiceCategory, Service, ServiceProvider, ProviderService,
    ProviderSchedule, ProviderUnavailableDate
)
from vehicles.models import VehicleMake


class Command(BaseCommand):
    help = "Seeds the 16 standard service categories, services, schedules, and provider offerings."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Service Categories & Catalogue...")

        categories_data = [
            ("General servicing", "wrench", "Comprehensive periodic multipoint checkup, fluid top-ups, and safety inspections.", 1),
            ("Engine diagnostics", "activity", "Advanced OBD-II digital scan, sensor calibration, and ECU fault code analysis.", 2),
            ("Engine oil replacement", "droplet", "Premium synthetic oil replacement with genuine OEM oil filter swap.", 3),
            ("Brake inspection and repair", "disc", "Brake pad replacement, disc rotor inspection, caliper servicing, and fluid flush.", 4),
            ("Battery inspection and replacement", "battery-charging", "Battery health testing, terminal cleaning, and genuine replacement.", 5),
            ("Tyre replacement", "circle", "OEM specification tyre mounting, tread depth analysis, and pressure optimization.", 6),
            ("Wheel alignment", "compass", "Computerized 3D 4-wheel alignment for optimal steering geometry and tyre longevity.", 7),
            ("Wheel balancing", "target", "Precision dynamic wheel balancing to eliminate high-speed vibrations.", 8),
            ("AC servicing", "wind", "AC refrigerant recharge, cabin pollen filter cleaning, and cooling coil anti-bacterial flush.", 9),
            ("Car washing", "sparkles", "Foam wash, underbody pressure cleaning, tyre dressing, and glass wipe down.", 10),
            ("Interior cleaning", "spray-can", "Deep upholstery steam cleaning, sanitization, leather conditioning, and stain removal.", 11),
            ("Exterior detailing", "shield", "Ceramic coating prep, multi-stage paint correction, clay bar treatment, and polymer sealant.", 12),
            ("Denting and painting", "paintbrush", "Panel beating, computerised paint matching, scratch removal, and bake booth finishing.", 13),
            ("Suspension repair", "maximize-2", "Strut replacement, bushing overhaul, shock absorber testing, and link rod renewal.", 14),
            ("Electrical repair", "zap", "Alternator, starter motor, fuse box, wiring harness, and lighting diagnostics.", 15),
            ("Emergency roadside support", "life-buoy", "24/7 on-demand breakdown assistance, battery jumpstart, flat tyre repair, and fuel delivery.", 16),
        ]

        category_map = {}
        for name, icon, desc, order in categories_data:
            cat, created = ServiceCategory.objects.update_or_create(
                name=name,
                defaults={
                    'icon_name': icon,
                    'description': desc,
                    'sort_order': order,
                    'is_active': True,
                }
            )
            category_map[name] = cat
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} category: {name}")

        services_data = [
            ("Comprehensive Periodic Service", "General servicing", "general", 180, Decimal('3499.00'), "Hatchback, Sedan, SUV", "Complete 40-point vehicle health audit, oil change, and filter renewal.", "wrench", True),
            ("OBD-II Computerized Engine Scan", "Engine diagnostics", "electrical", 60, Decimal('1299.00'), "All Models", "ECU error code extraction, live sensor stream diagnostics, and freeze-frame report.", "activity", True),
            ("Full Synthetic Oil & Filter Service", "Engine oil replacement", "oil", 60, Decimal('2499.00'), "Petrol, Diesel, Hybrid", "Castrol/Mobil 1 fully synthetic oil replacement with genuine OEM filter.", "droplet", True),
            ("Front & Rear Brake Overhaul", "Brake inspection and repair", "brakes", 120, Decimal('1899.00'), "All Models", "Brake pad replacement, rotor thickness assessment, and hydraulic bleeding.", "disc", True),
            ("Battery Health Test & Jump Start Support", "Battery inspection and replacement", "battery", 45, Decimal('499.00'), "All Models", "CCA load testing, terminal corrosion removal, alternator charging test.", "battery-charging", False),
            ("Tyre Replacement & Fitting", "Tyre replacement", "tyre", 60, Decimal('399.00'), "All Models", "Professional bead dismounting, new tyre seating, and tubeless valve replacement.", "circle", False),
            ("3D Computerized Laser Wheel Alignment", "Wheel alignment", "tyre", 45, Decimal('899.00'), "All Models", "Precision alignment of camber, caster, and toe to factory specs.", "compass", True),
            ("High-Speed Dynamic Wheel Balancing", "Wheel balancing", "tyre", 45, Decimal('699.00'), "All Models", "Counter-weight balancing for all 4 alloy wheels.", "target", False),
            ("Complete Climate Control AC Servicing", "AC servicing", "ac", 120, Decimal('2199.00'), "All Models", "R134a refrigerant evacuation, vacuum test, compressor oil, and filter cleaning.", "wind", True),
            ("Hydro-Foam Pressure Car Wash", "Car washing", "washing", 45, Decimal('649.00'), "Hatchback, Sedan, SUV", "High pressure underbody jet wash, pH-neutral foam, and interior vacuum.", "sparkles", True),
            ("Deep Sanitization Interior Detailing", "Interior cleaning", "washing", 150, Decimal('2899.00'), "All Models", "Hot-water extraction of fabric seats, steam disinfection of AC vents.", "spray-can", False),
            ("Multi-Stage Paint Correction & Gloss Wax", "Exterior detailing", "washing", 240, Decimal('4999.00'), "All Models", "Swirl mark reduction, dual-action rotary polish, and polymer hydrophobic coat.", "shield", True),
            ("Panel Dent Removal & Oven Baked Painting", "Denting and painting", "bodywork", 360, Decimal('3200.00'), "All Models", "Spot paint blending, anti-corrosive primer, and clear coat bake in sealed booth.", "paintbrush", False),
            ("Suspension Bushing & Strut Inspection", "Suspension repair", "mechanical", 150, Decimal('2499.00'), "All Models", "Suspension rattle diagnosis, shock rebound test, and link rod replacement.", "maximize-2", False),
            ("Electrical Wiring & Alternator Service", "Electrical repair", "electrical", 90, Decimal('1599.00'), "All Models", "Parasitic battery drain testing, wiring harness repair, and starter motor servicing.", "zap", False),
            ("Rapid 24/7 Roadside Assistance & Towing", "Emergency roadside support", "emergency", 45, Decimal('1499.00'), "All Models", "Flat tyre change, on-spot jumpstart, minor electrical triage, or flatbed dispatch.", "life-buoy", True),
        ]

        services_created = []
        for s_name, cat_name, legacy_cat, duration_mins, price, veh_types, desc, icon, popular in services_data:
            cat_obj = category_map.get(cat_name)
            svc, created = Service.objects.update_or_create(
                name=s_name,
                defaults={
                    'category': legacy_cat,
                    'category_ref': cat_obj,
                    'estimated_duration_minutes': duration_mins,
                    'estimated_duration': f"{duration_mins // 60}h {duration_mins % 60}m" if duration_mins >= 60 else f"{duration_mins} mins",
                    'starting_price': price,
                    'supported_vehicle_types': veh_types,
                    'description': desc,
                    'icon_name': icon,
                    'is_popular': popular,
                    'is_active': True,
                }
            )
            services_created.append(svc)

        # Wire up Providers
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        makes = list(VehicleMake.objects.all())

        providers = ServiceProvider.objects.all()
        for idx, provider in enumerate(providers):
            provider.owner = admin_user
            provider.is_demo = True
            provider.is_active = True
            provider.status = 'active'
            if not provider.state:
                provider.state = "Karnataka" if "Bengaluru" in provider.city else ("Maharashtra" if provider.city in ["Mumbai", "Pune"] else "Delhi")
            if not provider.postal_code:
                provider.postal_code = f"5600{idx+1:02d}"
            if not provider.description:
                provider.description = f"{provider.name} is a premier multi-brand workshop equipped with state-of-the-art diagnostic scanners, automated tyre changers, and climate-controlled paint booths."
            provider.save()

            if makes:
                # Assign 3-6 makes to each provider
                sample_makes = makes[idx % len(makes): (idx % len(makes)) + 4]
                if not sample_makes:
                    sample_makes = makes[:3]
                provider.supported_brands.set(sample_makes)

            # Create weekly schedules (Mon-Sat 9:00 - 18:00, Sun closed)
            for day in range(7):
                is_sunday = (day == 6)
                ProviderSchedule.objects.update_or_create(
                    provider=provider,
                    weekday=day,
                    defaults={
                        'is_closed': is_sunday,
                        'open_time': datetime.time(9, 0),
                        'close_time': datetime.time(18, 0),
                        'has_break': True,
                        'break_start': datetime.time(13, 0),
                        'break_end': datetime.time(14, 0),
                        'slot_duration_minutes': 60,
                        'max_bookings_per_slot': 2,
                    }
                )

            # Create an upcoming holiday closure (e.g. 15 days ahead)
            holiday_date = datetime.date.today() + datetime.timedelta(days=14)
            ProviderUnavailableDate.objects.get_or_create(
                provider=provider,
                date=holiday_date,
                defaults={'reason': 'Annual Workshop Equipment Calibration'}
            )

            # Link offerings (ProviderService) with custom pricing
            for s_idx, svc in enumerate(services_created):
                # Apply slight variance (+/- 10%) per provider to show realistic workshop pricing
                factor = Decimal(str(1.0 + ((idx + s_idx) % 5 - 2) * 0.05))
                provider_price = (svc.starting_price * factor).quantize(Decimal('1.00'))
                ProviderService.objects.update_or_create(
                    provider=provider,
                    service=svc,
                    defaults={
                        'price': provider_price,
                        'duration_minutes': svc.estimated_duration_minutes,
                        'is_available': True,
                        'notes': f"Genuine OEM parts guaranteed with {provider.name} standard warranty.",
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully seeded all 16 categories, services, schedules, and provider offerings!"))

