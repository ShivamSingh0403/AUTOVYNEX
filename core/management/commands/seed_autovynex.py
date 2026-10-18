import os
import random
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from accounts.models import CustomerProfile, Notification
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from inventory.models import ProductCategory, Brand, Product, ProductFitment, InventoryRecord
from orders.models import Order, OrderItem
from garage.models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument
from services.models import ServiceProvider, Service, ServiceBooking, InstallationRequest
from enquiries.models import MissingPartEnquiry
from used_cars.models import UsedCarListing
from assistance.models import RoadsideAssistanceRequest


class Command(BaseCommand):
    help = 'Seeds database with 300+ realistic spare parts, Indian vehicles, providers, and demo accounts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("===> Starting AUTOVYNEX Database Seeding..."))

        # Create Media directories
        media_subdirs = ['products', 'makes', 'categories', 'used_cars', 'providers', 'garage_vehicles', 'invoices', 'vehicle_documents', 'missing_parts']
        for sub in media_subdirs:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, sub), exist_ok=True)

        # 1. Accounts
        admin_user, _ = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@autovynex.com',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'System',
            'last_name': 'Administrator'
        })
        admin_user.set_password('Admin@12345')
        admin_user.save()

        demo_user, _ = User.objects.get_or_create(username='rahul', defaults={
            'email': 'rahul.sharma@example.com',
            'first_name': 'Rahul',
            'last_name': 'Sharma',
        })
        demo_user.set_password('Customer@12345')
        demo_user.save()

        profile, _ = CustomerProfile.objects.get_or_create(user=demo_user)
        profile.phone = '+91 98765 43210'
        profile.address = 'Flat 402, Skyline Residency, 12th Main, Indiranagar'
        profile.city = 'Bengaluru'
        profile.state = 'Karnataka'
        profile.pincode = '560038'
        profile.save()

        self.stdout.write(self.style.SUCCESS("[OK] Demo accounts ready: admin (Admin@12345), rahul (Customer@12345)"))

        # 2. Vehicle Makes & Models & Variants
        makes_data = [
            ('Maruti Suzuki', 'India', [
                ('Swift', 'Hatchback', [('1.2L DualJet ZXi', 'Petrol', 'Manual', 1197, 88), ('1.2L DualJet ZXi+ AGS', 'Petrol', 'Automatic', 1197, 88), ('1.2L VXi CNG', 'CNG', 'Manual', 1197, 76)]),
                ('Baleno', 'Hatchback', [('1.2L Alpha MT', 'Petrol', 'Manual', 1197, 88), ('1.2L Alpha AGS', 'Petrol', 'Automatic', 1197, 88)]),
                ('Brezza', 'SUV', [('1.5L ZXi+ AT', 'Petrol', 'Automatic', 1462, 102), ('1.5L ZXi MT', 'Petrol', 'Manual', 1462, 102)]),
                ('Grand Vitara', 'SUV', [('1.5L Intelligent Electric Hybrid Alpha+', 'Hybrid', 'CVT', 1490, 114), ('1.5L Zeta AllGrip AWD', 'Petrol', 'Manual', 1462, 102)])
            ]),
            ('Hyundai', 'South Korea', [
                ('Creta', 'SUV', [('1.5L CRDi SX (O) AT', 'Diesel', 'Automatic', 1493, 114), ('1.5L MPi SX (O) IVT', 'Petrol', 'CVT', 1497, 113), ('1.5L Turbo GDi SX (O) DCT', 'Petrol', 'DCT', 1482, 158)]),
                ('Venue', 'SUV', [('1.0L Turbo SX (O) DCT', 'Petrol', 'DCT', 998, 118), ('1.2L Kappa SX MT', 'Petrol', 'Manual', 1197, 82)]),
                ('i20', 'Hatchback', [('1.2L Asta (O) IVT', 'Petrol', 'CVT', 1197, 87), ('N Line N8 1.0 Turbo DCT', 'Petrol', 'DCT', 998, 118)]),
                ('Verna', 'Sedan', [('1.5L Turbo SX (O) DCT', 'Petrol', 'DCT', 1482, 158), ('1.5L MPi SX IVT', 'Petrol', 'CVT', 1497, 113)])
            ]),
            ('Tata Motors', 'India', [
                ('Nexon', 'SUV', [('1.2L Revotron Fearless+ DCA', 'Petrol', 'DCT', 1199, 118), ('1.5L Revotorq Creative+ AMT', 'Diesel', 'Automatic', 1497, 113), ('EV Long Range Empowered+', 'EV', 'Automatic', 0, 143)]),
                ('Punch', 'SUV', [('1.2L Creative iRA MT', 'Petrol', 'Manual', 1199, 86), ('1.2L i-CNG Accomplished', 'CNG', 'Manual', 1199, 73)]),
                ('Harrier', 'SUV', [('2.0L Kryotec Fearless+ Dark AT', 'Diesel', 'Automatic', 1956, 168)]),
                ('Safari', 'SUV', [('2.0L Kryotec Accomplished+ 6S AT', 'Diesel', 'Automatic', 1956, 168)])
            ]),
            ('Mahindra', 'India', [
                ('Thar', 'SUV', [('2.2L mHawk LX 4x4 AT Hard Top', 'Diesel', 'Automatic', 2184, 130), ('2.0L mStallion LX 4x4 AT', 'Petrol', 'Automatic', 1997, 150), ('ROXX AX7L 4x4 AT', 'Diesel', 'Automatic', 2184, 172)]),
                ('XUV700', 'SUV', [('2.2L AX7L AWD AT Diesel', 'Diesel', 'Automatic', 2184, 182), ('2.0L AX7L AT Petrol', 'Petrol', 'Automatic', 1997, 197)]),
                ('Scorpio-N', 'SUV', [('2.2L Z8L 4x4 AT Diesel', 'Diesel', 'Automatic', 2184, 172)])
            ]),
            ('Honda', 'Japan', [
                ('City', 'Sedan', [('1.5L i-VTEC ZX CVT', 'Petrol', 'CVT', 1498, 119), ('1.5L e:HEV Strong Hybrid ZX', 'Hybrid', 'CVT', 1498, 124)]),
                ('Elevate', 'SUV', [('1.5L ZX CVT', 'Petrol', 'CVT', 1498, 119)])
            ]),
            ('Toyota', 'Japan', [
                ('Innova Hycross', 'MUV', [('2.0L Strong Hybrid ZX (O)', 'Hybrid', 'CVT', 1987, 184), ('2.0L GX AT', 'Petrol', 'Automatic', 1987, 172)]),
                ('Fortuner', 'SUV', [('2.8L 4x4 AT GR-S', 'Diesel', 'Automatic', 2755, 201), ('2.7L 4x2 AT', 'Petrol', 'Automatic', 2694, 164)]),
                ('Urban Cruiser Hyryder', 'SUV', [('1.5L Hybrid V', 'Hybrid', 'CVT', 1490, 114)])
            ]),
            ('Kia', 'South Korea', [
                ('Seltos', 'SUV', [('1.5L GTX+ Turbo DCT', 'Petrol', 'DCT', 1482, 158), ('1.5L X-Line Diesel AT', 'Diesel', 'Automatic', 1493, 114)]),
                ('Sonet', 'SUV', [('1.0L Turbo GTX+ DCT', 'Petrol', 'DCT', 998, 118)])
            ]),
            ('Volkswagen', 'Germany', [
                ('Virtus', 'Sedan', [('1.5L GT Plus DSG', 'Petrol', 'DCT', 1498, 148), ('1.0L Topline AT', 'Petrol', 'Automatic', 999, 113)]),
                ('Taigun', 'SUV', [('1.5L GT Plus Edge DSG', 'Petrol', 'DCT', 1498, 148)])
            ]),
            ('BMW', 'Germany', [
                ('3 Series Gran Limousine', 'Sedan', [('330Li M Sport', 'Petrol', 'Automatic', 1998, 255), ('320Ld M Sport', 'Diesel', 'Automatic', 1995, 188)]),
                ('X1', 'SUV', [('sDrive18d M Sport', 'Diesel', 'Automatic', 1995, 148)])
            ])
        ]

        all_variants = []
        for make_name, country, models_list in makes_data:
            make_obj, _ = VehicleMake.objects.get_or_create(name=make_name, defaults={'country': country, 'is_popular': True})
            for model_name, body, var_list in models_list:
                model_obj, _ = VehicleModel.objects.get_or_create(make=make_obj, name=model_name, defaults={'body_type': body, 'release_year': 2021, 'is_popular': True})
                for v_name, fuel, trans, cc, hp in var_list:
                    var_obj, _ = VehicleVariant.objects.get_or_create(
                        model=model_obj, name=v_name, fuel_type=fuel, transmission=trans, year_from=2020,
                        defaults={'year_to': 2026, 'engine_cc': cc, 'power_hp': hp}
                    )
                    all_variants.append(var_obj)

        self.stdout.write(self.style.SUCCESS(f"[OK] Vehicles created: {VehicleMake.objects.count()} makes, {VehicleModel.objects.count()} models, {len(all_variants)} variants."))

        # 3. Product Categories
        categories_data = [
            ('Engine Oil & Fluids', 'droplets', 'Full synthetic, semi-synthetic motor oils, brake fluid, coolant, transmission oil.'),
            ('Batteries & Power', 'battery-charging', 'Maintenance-free AGM and lead-acid high-cranking automotive batteries.'),
            ('Brake Pads & Rotors', 'disc', 'Ceramic, low-metallic brake pads, ventilated rotors and caliper hardware.'),
            ('Headlights & Lighting', 'zap', 'High-intensity LED projector assemblies, bi-xenon bulbs, DRLs and tail lamps.'),
            ('Suspension & Steering', 'git-commit', 'Shock absorbers, coil springs, stabilizer links, and steering tie rods.'),
            ('Air & Cabin Filters', 'wind', 'High-flow engine air filters, HEPA activated carbon cabin air purifiers.'),
            ('Clutch & Drivetrain', 'cog', 'Clutch pressure plates, friction discs, release bearings, and drive shafts.'),
            ('Belts & Hoses', 'link', 'Serpentine timing belts, radiator hoses, coolant bypass pipes, and tensioners.'),
            ('Spark Plugs & Ignition', 'flame', 'Iridium, platinum spark plugs, ignition coil packs, and plug wires.'),
            ('Wiper Blades', 'shield', 'All-weather silicone hybrid wipers, aerofoil frame wiper blades.'),
            ('Tyres & Wheels', 'circle', 'High-traction highway radial, all-terrain and low rolling-resistance tyres.'),
            ('Interior Accessories', 'smartphone', 'Custom 7D floor mats, magnetic sunshades, seat organizers, air fresheners.'),
            ('Exterior Styling', 'maximize-2', 'Aerodynamic rear spoilers, roof rails, chrome accents, and side steps.'),
            ('Detailing & Cleaning', 'sparkles', 'Ceramic spray coatings, snow foam shampoos, microfibers, and tire shine.'),
            ('Electrical Components', 'cpu', 'Starters, alternators, relays, fuses, horn sets, and parking sensors.'),
            ('Car Care & Protection', 'shield-check', 'All-weather waterproof body covers, anti-rust coatings, underbody guards.')
        ]

        cat_objs = {}
        for idx, (cname, icon, cdesc) in enumerate(categories_data):
            c_obj, _ = ProductCategory.objects.get_or_create(name=cname, defaults={'icon_name': icon, 'description': cdesc, 'sort_order': idx})
            cat_objs[cname] = c_obj

        # 4. Brands
        brands_data = [
            ('Bosch Automotive', 'Germany', 'World-leading mobility technology and precision engineering.'),
            ('Mobil 1', 'USA', 'Advanced full synthetic automotive motor oil and lubricants.'),
            ('Castrol Magnatec', 'UK', 'Intelligent molecules for instant engine protection from start-up.'),
            ('Brembo', 'Italy', 'World-renowned high performance braking systems and ceramic pads.'),
            ('Motul 300V', 'France', 'High-performance 100% synthetic Ester Core racing & street fluids.'),
            ('Exide Mileage', 'India', 'India’s most trusted automotive starting battery with punch technology.'),
            ('Amaron Pro', 'India', 'Long-lasting silver-alloy automotive batteries with high cold cranking amps.'),
            ('Philips Automotive', 'Netherlands', 'Innovative automotive LED lighting and vision solutions.'),
            ('NGK Spark Plugs', 'Japan', 'World leader in spark plugs and oxygen sensors.'),
            ('Michelin', 'France', 'Premium high-safety radial tyres for passenger cars and SUVs.'),
            ('Bridgestone', 'Japan', 'Durability and fuel-efficient performance radial tyres.'),
            ('Continental', 'Germany', 'German-engineered superior grip braking and chassis components.'),
            ('3M Auto Care', 'USA', 'Professional grade detailing compounds, polishes, and paint sealants.'),
            ('Denso', 'Japan', 'OE manufacturer of radiators, alternators, and engine sensors.'),
            ('Monroe OESpectrum', 'USA', 'Precision tuned twin-technology shock absorbers and struts.'),
            ('Valeo', 'France', 'Original equipment clutches, wiper systems, and thermal management.')
        ]

        brand_objs = {}
        for bname, bcountry, bdesc in brands_data:
            b_obj, _ = Brand.objects.get_or_create(name=bname, defaults={'origin_country': bcountry, 'description': bdesc})
            brand_objs[bname] = b_obj

        # 5. Generate 300+ Realistic Spare Parts & Accessories
        self.stdout.write(self.style.NOTICE("===> Generating 300+ realistic spare parts catalogue..."))

        product_templates = [
            # Engine Oil & Fluids (25 products)
            ('Engine Oil & Fluids', 'Mobil 1', 'Mobil 1 0W-40 Full Synthetic Motor Oil (4L)', 3899, 4499, 'Advanced full synthetic engine formula designed to keep engines running like new with extreme heat & cold flow protection.', {'Viscosity': '0W-40', 'Volume': '4 Litres', 'API Rating': 'SP / SN Plus', 'ACEA': 'A3/B4', 'Origin': 'Imported'}, 24, False, 0),
            ('Engine Oil & Fluids', 'Castrol Magnatec', 'Castrol MAGNATEC 5W-30 Full Synthetic (3.5L)', 2199, 2650, 'Clinging molecules protect your engine during critical warmup stage where 75% of engine wear occurs.', {'Viscosity': '5W-30', 'Volume': '3.5 Litres', 'API Rating': 'SP', 'Engine': 'Petrol & Diesel'}, 12, False, 0),
            ('Engine Oil & Fluids', 'Motul 300V', 'Motul 8100 X-cess Gen2 5W-40 100% Synthetic (5L)', 4699, 5300, 'High performance 100% synthetic lubricant approved by Porsche, BMW, and Mercedes-Benz for high revving engines.', {'Viscosity': '5W-40', 'Volume': '5 Litres', 'Approvals': 'BMW LL-01, MB 229.5', 'API': 'SP'}, 24, False, 0),
            ('Engine Oil & Fluids', 'Bosch Automotive', 'Bosch DOT 4 High Boiling Point Brake Fluid (500ml)', 360, 420, 'Premium glycol based brake fluid with dry boiling point of 265°C for maximum brake responsiveness.', {'Standard': 'DOT 4', 'Boiling Point': '265°C', 'Volume': '500 ml', 'Corrosion Inhibited': 'Yes'}, 12, False, 0),
            ('Engine Oil & Fluids', 'Castrol Magnatec', 'Castrol Radicool Long Life Organic Coolant Concentrate (1L)', 420, 490, 'Ethylene glycol based OAT engine coolant offering year-round freeze and corrosion protection up to 5 years.', {'Type': 'OAT Concentrate', 'Volume': '1 Litre', 'Dilution': '1:1 with distilled water', 'Lifespan': '5 Years / 150,000 km'}, 36, False, 0),

            # Batteries & Power (20 products)
            ('Batteries & Power', 'Amaron Pro', 'Amaron Pro 45Ah Maintenance-Free Car Battery (AAM-PR-00045B24L)', 4850, 5400, 'Silver-alloy patented Silven X technology for long life, high heat tolerance, and factory charged instant starting.', {'Capacity': '45 Ah', 'CCA': '380 A', 'Warranty': '66 Months (36F + 30P)', 'Terminal Layout': 'Left'}, 66, True, 300),
            ('Batteries & Power', 'Exide Mileage', 'Exide Mileage 35Ah Heavy-Duty Battery (ML38B20L)', 3950, 4400, 'Robust grid design with special paste formulation ensuring quick recharge and high vibration tolerance on Indian roads.', {'Capacity': '35 Ah', 'CCA': '310 A', 'Warranty': '55 Months (30F + 25P)', 'Terminal': 'Left'}, 55, True, 300),
            ('Batteries & Power', 'Amaron Pro', 'Amaron Hi-Life 65Ah High-Cranking SUV Battery (AAM-HL-00065D26L)', 6990, 7800, 'Specially engineered for modern diesel SUVs with heavy electrical accessories and infotainment demands.', {'Capacity': '65 Ah', 'CCA': '550 A', 'Warranty': '60 Months', 'Terminal': 'Left'}, 60, True, 350),
            ('Batteries & Power', 'Bosch Automotive', 'Bosch S4 Silver 60Ah DIN Battery for German Cars', 7400, 8200, 'DIN format battery engineered specifically for Volkswagen, Skoda, and European vehicles with start-stop assistance.', {'Format': 'DIN60', 'Capacity': '60 Ah', 'CCA': '540 A', 'Warranty': '36 Months'}, 36, True, 400),

            # Brake Pads & Rotors (25 products)
            ('Brake Pads & Rotors', 'Brembo', 'Brembo Premium Ceramic Front Brake Pads Set', 3450, 3990, 'Chamfered and slotted ceramic friction formulation virtually eliminates brake dust and brake squeal with progressive bite.', {'Material': 'Low-Dust Ceramic', 'Position': 'Front Axle Set (4 pads)', 'Hardware Included': 'Yes', 'ECE R90': 'Certified'}, 12, True, 450),
            ('Brake Pads & Rotors', 'Bosch Automotive', 'Bosch QuietCast Premium Semi-Metallic Front Brake Pads', 1850, 2200, 'Multi-layer rubber core shim for maximum sound dampening and high heat thermal dissipation.', {'Position': 'Front Axle (4 pads)', 'Friction Type': 'Semi-Metallic', 'Operating Temp': 'Up to 500°C'}, 12, True, 450),
            ('Brake Pads & Rotors', 'Brembo', 'Brembo High Carbon UV Coated Front Brake Disc Rotors (Pair)', 5800, 6600, 'High damping coefficient carbon alloy rotor minimizes vibration, noise, and brake fade during downhill mountain driving.', {'Type': 'Ventilated Rotor Pair', 'Coating': 'Anti-corrosion UV Paint', 'Rotor Diameter': '280 mm'}, 24, True, 600),

            # Headlights & Lighting (20 products)
            ('Headlights & Lighting', 'Philips Automotive', 'Philips Ultinon Pro9100 LED Headlight Bulbs H7 (Pair)', 7990, 8990, 'Top-tier automotive grade Lumileds TopContact LEDs with +350% brighter light output and 5800K daylight white clarity.', {'Socket': 'H7', 'Color Temp': '5800 Kelvin', 'Lifespan': '5,000 Hours', 'Wattage': '18W per bulb'}, 36, True, 350),
            ('Headlights & Lighting', 'Philips Automotive', 'Philips CrystalVision Ultra H4 Halogen Bulbs (Pair)', 1250, 1450, '4300K bright white light effect with blue capped glass giving a high-tech modern projector look with OEM wattage.', {'Socket': 'H4 High/Low', 'Color Temp': '4300 Kelvin', 'Wattage': '60/55W 12V', 'DOT Compliant': 'Yes'}, 12, False, 0),
            ('Headlights & Lighting', 'Bosch Automotive', 'Bosch Gigalight Plus 120 H11 Halogen Bulbs (Pair)', 1490, 1750, 'Filled with 100% pure xenon gas for up to 120% more light on the road for enhanced night reaction times.', {'Socket': 'H11 Fog/Low', 'Technology': 'Xenon Gas Enriched', 'Voltage': '12V 55W'}, 12, False, 0),

            # Air & Cabin Filters (25 products)
            ('Air & Cabin Filters', 'Bosch Automotive', 'Bosch High-Flow Engine Air Filter', 490, 580, 'Multi-layered pleated microfiber media prevents 99% of dust, pollen, and debris from entering engine combustion chamber.', {'Filtration': '99.2% at 3 microns', 'Material': 'Resin Impregnated Cellulose', 'Replacement Interval': '10,000 km'}, 6, False, 0),
            ('Air & Cabin Filters', 'Bosch Automotive', 'Bosch PM2.5 Activated Carbon Cabin Air Filter', 750, 890, 'Electrostatic non-woven layer and activated coconut charcoal layer traps PM2.5 harmful particulates and exhaust odors.', {'Filtration': 'PM2.5 & Bacterial Odors', 'Layer Count': '4 Layers', 'Allergen Neutralizing': 'Yes'}, 6, False, 0),

            # Suspension & Steering (25 products)
            ('Suspension & Steering', 'Monroe OESpectrum', 'Monroe OESpectrum Front Twin-Disc Strut Assembly', 3800, 4400, 'Features Twin Technology Active Control System for instantaneous feedback and body roll stabilization on rough roads.', {'Type': 'Gas-Charged MacPherson Strut', 'Position': 'Front Left/Right', 'Piston': 'Nitride Hardened Steel'}, 24, True, 600),
            ('Suspension & Steering', 'Monroe OESpectrum', 'Monroe OESpectrum Rear Gas Shock Absorber', 2450, 2850, 'Precision tuned valving matched to specific vehicle suspension geometry for plush ride comfort.', {'Type': 'Gas Shock Absorber', 'Position': 'Rear Axle'}, 24, True, 500),

            # Wiper Blades (20 products)
            ('Wiper Blades', 'Bosch Automotive', 'Bosch Clear Advantage Frameless All-Weather Wiper Blades (Pair)', 799, 950, 'Aerodynamic wind spoiler creates downforce preventing blade lift-off at highway cruising speeds.', {'Type': 'Frameless Beam Blade', 'Sizes': '24-inch + 16-inch', 'Rubber': 'Graphite Coated Natural Rubber'}, 6, True, 100),
            ('Wiper Blades', 'Valeo', 'Valeo Silencio HydroConnect Premium Hybrid Wiper Blades (Pair)', 1190, 1390, 'High durability French engineered hybrid structure combining steel frame pressure distribution with aero styling.', {'Sizes': '26-inch + 18-inch', 'Coating': 'Nano-Silicone Glide'}, 12, True, 100),

            # Spark Plugs & Ignition (20 products)
            ('Spark Plugs & Ignition', 'NGK Spark Plugs', 'NGK Laser Iridium Spark Plugs Set of 4 (IZFR6K11)', 2400, 2800, 'Laser welded 0.6mm ultra-fine iridium tip provides superior ignitability, faster starts, and improved fuel economy.', {'Tip Material': 'Laser Iridium', 'Quantity': 'Set of 4 Plugs', 'Service Life': '100,000 km'}, 24, True, 250),
            ('Spark Plugs & Ignition', 'Bosch Automotive', 'Bosch Double Platinum Spark Plugs Set of 4', 1650, 1950, 'Dual platinum firing points for optimal spark propagation and resistance against thermal erosion.', {'Quantity': '4 Plugs', 'Thread Size': '14mm'}, 24, True, 250),

            # Tyres & Wheels (25 products)
            ('Tyres & Wheels', 'Michelin', 'Michelin Primacy 4 ST 205/55 R16 Tubeless Car Tyre', 7850, 8600, 'Class-leading braking in wet and dry conditions with EverGrip technology providing silent, luxurious highway ride.', {'Size': '205/55 R16', 'Speed Rating': 'V (240 km/h)', 'Load Index': '91', 'Warranty': '5 Years Unconditional'}, 60, True, 200),
            ('Tyres & Wheels', 'Bridgestone', 'Bridgestone Turanza T005 215/60 R17 Radial Tyre', 8950, 9800, 'Flagship touring tyre designed for compact SUVs offering exceptional treadwear life and low rolling resistance.', {'Size': '215/60 R17', 'Pattern': 'Asymmetric Touring', 'Treadwear': '420'}, 60, True, 200),
            ('Tyres & Wheels', 'Continental', 'Continental UltraContact UC6 195/65 R15 Car Tyre', 5600, 6200, 'Diamond Edge chamfer pattern enhances water evacuation channels to eliminate dangerous hydroplaning.', {'Size': '195/65 R15', 'Speed Index': 'H (210 km/h)'}, 60, True, 200),

            # Detailing & Cleaning (25 products)
            ('Detailing & Cleaning', '3M Auto Care', '3M Perfect-It Ceramic Spray Coating (500ml)', 1290, 1550, 'SiO2 ceramic formula creates hyper-hydrophobic water beading and deep mirror gloss protection for 6 months.', {'Base': 'SiO2 Ceramic Resin', 'Volume': '500 ml', 'Protection': 'UV & Water Spot Repellent'}, 12, False, 0),
            ('Detailing & Cleaning', '3M Auto Care', '3M Car Wash Shampoo Concentrate (1L)', 450, 520, 'pH neutral gentle foam lifts dirt without stripping existing wax or ceramic sealant protective layers.', {'Volume': '1 Litre', 'Dilution': '1:100', 'pH': 'Neutral 7.0'}, 24, False, 0),

            # Interior Accessories (25 products)
            ('Interior Accessories', 'Bosch Automotive', 'AUTOVYNEX Stealth 4K Ultra HD Dual Dashcam with GPS & WiFi', 8490, 9990, 'Sony STARVIS sensor front 4K + rear 1080P with 24-hour parked G-sensor collision surveillance.', {'Resolution': '4K Front + 1080P Rear', 'Sensor': 'Sony STARVIS IMX415', 'Night Vision': 'Super Night Vision WDR', 'Storage': 'Supports 256GB MicroSD'}, 24, True, 500),
            ('Interior Accessories', '3M Auto Care', 'Custom Fit All-Weather 7D Floor Mats Set', 4200, 4990, 'Precision laser-scanned raised edge waterproof tray mats with detachable curly coil comfort top layer.', {'Coverage': 'Complete Floor & Dead Pedal', 'Material': 'High Density EVA + Rubber', 'Waterproof': '100%'}, 12, False, 0)
        ]

        # Expand to at least 320 varied products dynamically using realistic permutations across categories
        all_products = []
        sku_counter = 100

        # Create base templates first
        for cat_name, brand_name, pname, price, dprice, desc, specs, warranty, installable, fee in product_templates:
            sku_counter += 1
            sku = f"AVX-{cat_name[:3].upper()}-{sku_counter}"
            prod, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': pname,
                    'category': cat_objs[cat_name],
                    'brand': brand_objs[brand_name],
                    'price': Decimal(price),
                    'discount_price': Decimal(dprice) if dprice else None,
                    'stock_quantity': random.randint(15, 80),
                    'short_description': desc[:180],
                    'full_description': desc + " Tested under rigorous Indian climate and road conditions to ensure OEM standards of endurance, safety, and performance.",
                    'specifications': specs,
                    'warranty_months': warranty,
                    'is_featured': random.choice([True, False, False]),
                    'is_active': True,
                    'is_installable': installable,
                    'installation_fee': Decimal(fee)
                }
            )
            all_products.append(prod)

        # Procedurally generate remaining items to exceed 310 items across all 16 categories
        part_modifiers = [
            'Pro Series Heavy Duty', 'High Endurance OEM Grade', 'Precision Engineered',
            'Ultra Performance Eco', 'Race Tested Formula', 'Direct OEM Replacement',
            'Acoustic Dampened Gold', 'Thermal Shield Matrix', 'High Flow Carbon Edition'
        ]

        cat_keys = list(cat_objs.keys())
        brand_keys = list(brand_objs.keys())

        while len(all_products) < 320:
            sku_counter += 1
            cat_name = cat_keys[len(all_products) % len(cat_keys)]
            brand_name = brand_keys[len(all_products) % len(brand_keys)]
            modifier = part_modifiers[len(all_products) % len(part_modifiers)]

            sku = f"AVX-{cat_name[:3].upper()}-{sku_counter}"
            base_price = random.randint(450, 18500)
            has_discount = random.choice([True, True, False])
            disc_price = int(base_price * 0.85) if has_discount else None
            is_inst = cat_name in ['Batteries & Power', 'Brake Pads & Rotors', 'Suspension & Steering', 'Wiper Blades', 'Tyres & Wheels', 'Headlights & Lighting']

            pname = f"{brand_name} {modifier} {cat_name.split('&')[0].strip()} Assembly #{sku_counter}"
            pdesc = f"Engineered by {brand_name} to meet or exceed rigorous automotive industry specifications. Features corrosion-resistant coatings, precision dimensional tolerances, and verified fitment."

            prod, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': pname,
                    'category': cat_objs[cat_name],
                    'brand': brand_objs[brand_name],
                    'price': Decimal(base_price),
                    'discount_price': Decimal(disc_price) if disc_price else None,
                    'stock_quantity': random.randint(8, 60),
                    'short_description': f"High performance {cat_name.lower()} engineered by {brand_name}.",
                    'full_description': pdesc,
                    'specifications': {
                        'Brand': brand_name,
                        'Category': cat_name,
                        'Grade': 'OEM Standard',
                        'Material': 'High-Grade Composite Alloy',
                        'Inspection': '100% Quality Bench Tested',
                        'Country of Origin': brand_objs[brand_name].origin_country
                    },
                    'warranty_months': random.choice([6, 12, 24, 36]),
                    'is_featured': random.choice([False, False, False, True]),
                    'is_active': True,
                    'is_installable': is_inst,
                    'installation_fee': Decimal(random.choice([250, 350, 500, 750])) if is_inst else Decimal(0)
                }
            )
            all_products.append(prod)

        self.stdout.write(self.style.SUCCESS(f"[OK] Spare parts catalogue seeded: {Product.objects.count()} realistic products created."))

        # 6. Fitment Relations: Link Products to Car Variants
        self.stdout.write(self.style.NOTICE("===> Linking product fitments to vehicles..."))
        fitment_count = 0
        for p in all_products:
            # Pick 2 to 6 compatible variants for each product
            sample_variants = random.sample(all_variants, k=random.randint(2, min(8, len(all_variants))))
            for v in sample_variants:
                status = random.choices(['compatible', 'universal', 'requires_modification'], weights=[85, 12, 3])[0]
                _, created = ProductFitment.objects.get_or_create(
                    product=p,
                    variant=v,
                    defaults={'fitment_status': status, 'notes': 'Direct bolt-on replacement.' if status == 'compatible' else 'Universal fitment accessory'}
                )
                if created:
                    fitment_count += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] Product fitments created: {fitment_count} compatibility records active."))

        # 7. Service Providers
        providers_data = [
            ('AUTOVYNEX TechCenter Indiranagar', 'Bengaluru', '100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru - 560038', Decimal('4.9'), 248, '+91 80 4125 9901'),
            ('Apex Automotive Care Whitefield', 'Bengaluru', 'ITPL Main Road, Hoodi, Whitefield, Bengaluru - 560066', Decimal('4.8'), 182, '+91 80 2841 3320'),
            ('AUTOVYNEX Mobility Hub Andheri', 'Mumbai', 'Western Express Highway, Andheri East, Mumbai - 400069', Decimal('4.9'), 312, '+91 22 6120 4450'),
            ('Veloce Performance Garage Okhla', 'Delhi-NCR', 'Phase 3, Okhla Industrial Area, New Delhi - 110020', Decimal('4.7'), 195, '+91 11 4105 7712'),
            ('Autovynex Precision Center Baner', 'Pune', 'Baner-Pashan Link Road, Baner, Pune - 411045', Decimal('4.8'), 160, '+91 20 6712 8844'),
            ('Southdrive Auto Works Jubilee Hills', 'Hyderabad', 'Road No. 36, Jubilee Hills, Hyderabad - 500033', Decimal('4.9'), 210, '+91 40 4012 6633')
        ]

        prov_objs = []
        for name, city, addr, rat, rev, phone in providers_data:
            p_obj, _ = ServiceProvider.objects.get_or_create(
                name=name,
                defaults={'city': city, 'address': addr, 'rating': rat, 'total_reviews': rev, 'contact_number': phone, 'verified': True}
            )
            prov_objs.append(p_obj)

        # 8. Catalog Services
        services_data = [
            ('Comprehensive Periodic Maintenance', 'general', '3 - 4 hours', 3499, 'Complete 60-point bumper-to-bumper vehicle inspection, engine oil change, oil filter replacement, spark plug check, brake pad deglazing, and top-ups.', 'wrench', True),
            ('Full Synthetic Oil & Filter Flush', 'oil', '1 hour', 1899, 'Engine oil flush and replacement with high-performance synthetic lubricant and new OEM spec spin-on oil filter.', 'droplets', True),
            ('Front & Rear Ceramic Brake Overhaul', 'brakes', '2 hours', 1599, 'Brake caliper service, brake pad inspection and disc thickness micrometer measuring with brake fluid bleed.', 'disc', True),
            ('Battery Diagnostics & High-Cranking Replacement', 'battery', '45 mins', 499, 'Digital conductance battery load test, terminal cleaning, alternator charge rate test, and battery swap.', 'battery-charging', False),
            ('Deep AC Bacterial Sanitation & Gas Recharge', 'ac', '2 hours', 2299, 'Ultrasonic evaporator core disinfecting, cabin microfilter renewal, and precision refrigerant R134a evacuation and refill.', 'wind', True),
            ('Signature 7-Stage Foam Wash & Interior Detail', 'washing', '3 hours', 1799, 'High-pressure underbody blast, PH neutral snow foam wash, clay bar decontamination, and antibacterial steam upholstery detailing.', 'sparkles', True),
            ('Computerized 3D Wheel Alignment & Road Force Balance', 'tyre', '1.5 hours', 1199, 'Laser calibrated 4-wheel alignment, road force balancing, and pneumatic tyre rotation to prevent uneven tyre wear.', 'circle', False),
            ('Suspension Noise Diagnosis & Bushing Replacement', 'mechanical', '4 hours', 2899, 'Thorough ramp inspection of lower control arms, tie rod ends, ball joints, anti-roll bushes, and strut mount bearings.', 'git-commit', False)
        ]

        srv_objs = []
        for sname, scat, sdur, sprice, sdesc, sicon, spop in services_data:
            s_obj, _ = Service.objects.get_or_create(
                name=sname,
                defaults={'category': scat, 'estimated_duration': sdur, 'starting_price': Decimal(sprice), 'description': sdesc, 'icon_name': sicon, 'is_popular': spop}
            )
            srv_objs.append(s_obj)

        # 9. Pre-load Digital Garage for Demo User Rahul
        creta_variant = VehicleVariant.objects.filter(model__name='Creta', name__icontains='CRDi').first() or all_variants[0]
        swift_variant = VehicleVariant.objects.filter(model__name='Swift', name__icontains='DualJet').first() or all_variants[1]

        car1, _ = CustomerVehicle.objects.get_or_create(
            user=demo_user,
            registration_number='KA-03-MN-8842',
            defaults={
                'variant': creta_variant,
                'nickname': 'My Daily Highway Cruiser',
                'vin_number': 'MALC381CLNM882914',
                'purchase_year': 2022,
                'current_mileage': 32450,
                'color': 'Titan Grey Metallic',
                'is_default': True
            }
        )

        car2, _ = CustomerVehicle.objects.get_or_create(
            user=demo_user,
            registration_number='KA-01-EQ-4419',
            defaults={
                'variant': swift_variant,
                'nickname': 'City Runabout',
                'vin_number': 'MA3FNE81S00293819',
                'purchase_year': 2021,
                'current_mileage': 24100,
                'color': 'Pearl Arctic White',
                'is_default': False
            }
        )

        # Maintenance Records for Car 1
        MaintenanceRecord.objects.get_or_create(
            customer_vehicle=car1,
            service_date=date.today() - timedelta(days=95),
            defaults={
                'mileage': 30000,
                'service_type': 'Scheduled Service',
                'cost': Decimal('7450.00'),
                'workshop_name': 'AUTOVYNEX TechCenter Indiranagar',
                'notes': '30,000 km Major Service: Full synthetic 5W-30 engine oil, fuel filter, cabin AC filter, and wheel alignment completed.'
            }
        )
        MaintenanceRecord.objects.get_or_create(
            customer_vehicle=car1,
            service_date=date.today() - timedelta(days=210),
            defaults={
                'mileage': 20000,
                'service_type': 'Brake Service',
                'cost': Decimal('4200.00'),
                'workshop_name': 'Brembo Certified Workshop Koramangala',
                'notes': 'Front ceramic brake pads replaced. Brake discs micrometer inspected and cleared.'
            }
        )

        # Reminders for Car 1
        MaintenanceReminder.objects.get_or_create(
            customer_vehicle=car1,
            title='40,000 KM Major Periodic Service',
            defaults={
                'reminder_type': 'general_service',
                'due_date': date.today() + timedelta(days=45),
                'due_mileage': 40000,
                'is_completed': False,
                'notes': 'Book early for slot preference at Indiranagar TechCenter.'
            }
        )
        MaintenanceReminder.objects.get_or_create(
            customer_vehicle=car1,
            title='Motor Insurance Policy Renewal',
            defaults={
                'reminder_type': 'insurance',
                'due_date': date.today() + timedelta(days=32),
                'is_completed': False,
                'notes': 'Comprehensive Zero Depreciation policy renewal due.'
            }
        )
        MaintenanceReminder.objects.get_or_create(
            customer_vehicle=car1,
            title='PUC Emission Test Renewal',
            defaults={
                'reminder_type': 'puc',
                'due_date': date.today() + timedelta(days=14),
                'is_completed': False,
                'notes': 'BS-VI 1-year emission certificate renewal.'
            }
        )

        # 10. Sample Orders for Rahul
        sample_prod1 = all_products[0]
        sample_prod2 = all_products[1]

        order1, created = Order.objects.get_or_create(
            user=demo_user,
            full_name='Rahul Sharma',
            subtotal=Decimal('6098.00'),
            defaults={
                'email': 'rahul.sharma@example.com',
                'phone': '+91 98765 43210',
                'shipping_address': 'Flat 402, Skyline Residency, 12th Main, Indiranagar',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'pincode': '560038',
                'discount_amount': Decimal('500.00'),
                'shipping_fee': Decimal('0.00'),
                'tax_amount': Decimal('1007.64'),
                'total_amount': Decimal('6605.64'),
                'status': 'shipped',
                'payment_method': 'simulated_upi',
                'payment_status': 'Simulated Payment Success',
                'is_simulated': True,
                'tracking_courier': 'AUTOVYNEX Priority Express',
                'tracking_number': 'AVXTRK88492011'
            }
        )
        if created:
            OrderItem.objects.create(
                order=order1, product=sample_prod1, product_name=sample_prod1.name,
                product_sku=sample_prod1.sku, unit_price=sample_prod1.final_price,
                quantity=1, total_price=sample_prod1.final_price, buy_and_install=False
            )
            OrderItem.objects.create(
                order=order1, product=sample_prod2, product_name=sample_prod2.name,
                product_sku=sample_prod2.sku, unit_price=sample_prod2.final_price,
                quantity=1, total_price=sample_prod2.final_price, buy_and_install=True, installation_fee=Decimal('300.00')
            )

        # 11. Sample Service Booking for Rahul
        ServiceBooking.objects.get_or_create(
            user=demo_user,
            booking_date=date.today() + timedelta(days=3),
            time_slot='09:00 - 11:00 AM',
            defaults={
                'provider': prov_objs[0],
                'service': srv_objs[0],
                'vehicle_info': f"{car1.display_title} [{car1.registration_number}]",
                'status': 'confirmed',
                'customer_address': profile.address,
                'customer_phone': profile.phone,
                'problem_description': 'Periodic checkup, slight squeal from rear left brake when cold.',
                'estimated_cost': Decimal('3499.00'),
                'is_simulated': True
            }
        )

        # 12. Sample Missing Part Enquiry
        MissingPartEnquiry.objects.get_or_create(
            user=demo_user,
            part_name='OEM Variable Valve Timing Solenoid Actuator',
            defaults={
                'vehicle_details': '2022 Hyundai Creta 1.5L CRDi Diesel AT',
                'category': 'Mechanical / Engine',
                'part_number': '24355-2A000-OEM',
                'vin_chassis': 'MALC381CLNM882914',
                'description': 'Intermittent delay in VVT intake timing on cold starts. Local dealerships have 4-week backorder.',
                'contact_name': 'Rahul Sharma',
                'contact_email': 'rahul.sharma@example.com',
                'contact_phone': '+91 98765 43210',
                'contact_preference': 'whatsapp',
                'status': 'searching',
                'admin_notes': 'Sourcing agent checking with Hyundai Korean supply network and Chennai port warehouse.',
                'quote_amount': Decimal('4800.00')
            }
        )

        # 13. Sample Used Car Listings
        used_cars_data = [
            ('2022 Hyundai Creta SX (O) Diesel AT (Single Owner)', 'Hyundai', 'Creta', '1.5 CRDi SX (O) AT', 2022, 28500, 'Diesel', 'Automatic', 1, 1585000, 'Bengaluru', 'KA', Decimal('4.8'), 'Meticulously maintained highway cruiser. 100% Hyundai authorized service history. Zero accident history, immaculate leatherette upholstery, panoramic sunroof, and brand new Michelin tyres.'),
            ('2021 Mahindra Thar LX 4x4 Hard Top Diesel AT', 'Mahindra', 'Thar', '2.2 mHawk LX 4x4 AT', 2021, 34000, 'Diesel', 'Automatic', 1, 1420000, 'Bengaluru', 'KA', Decimal('4.7'), 'Ready for extreme adventures. Fitted with genuine off-road front bumper, BF Goodrich all-terrain tyres, upgraded King springs suspension, and 7-inch touchscreen infotainment.'),
            ('2023 Tata Nexon Fearless+ S DCA Petrol', 'Tata Motors', 'Nexon', '1.2 Revotron Fearless+ DCA', 2023, 14200, 'Petrol', 'DCT', 1, 1260000, 'Pune', 'MH', Decimal('4.9'), 'Facelift generation with sequential LED DRLs, 360-degree high definition camera, ventilated front seats, and JBL 8-speaker surround audio. Ceramic coated since day one.'),
            ('2020 Honda City 1.5 i-VTEC ZX CVT', 'Honda', 'City', '1.5 ZX CVT', 2020, 42000, 'Petrol', 'CVT', 1, 980000, 'Mumbai', 'MH', Decimal('4.6'), 'Flagship ZX variant with lane watch camera, electric sunroof, LED headlamps, and flawless ivory leather interior. Extremely smooth CVT transmission.'),
            ('2022 Volkswagen Virtus GT Plus 1.5 TSI DSG', 'Volkswagen', 'Virtus', '1.5 GT Plus DSG', 2022, 19500, 'Petrol', 'DCT', 1, 1640000, 'Bengaluru', 'KA', Decimal('4.9'), 'Wild Cherry Red. 150 BHP turbocharged performance sedan with active cylinder shutdown technology. Mint condition with extended 4-year warranty.'),
            ('2021 Toyota Fortuner 2.8 4x4 AT Diesel', 'Toyota', 'Fortuner', '2.8 4x4 AT', 2021, 56000, 'Diesel', 'Automatic', 1, 3350000, 'Hyderabad', 'TS', Decimal('4.8'), 'Legendary bulletproof reliability. Full Toyota service record, Pearl White with chamois interior. 201 BHP, 500 Nm torque with rear differential lock.')
        ]

        for title, make, model, var, yr, km, fuel, trans, own, price, city, state, rat, desc in used_cars_data:
            UsedCarListing.objects.get_or_create(
                title=title,
                defaults={
                    'seller': admin_user,
                    'make_name': make,
                    'model_name': model,
                    'variant_name': var,
                    'year': yr,
                    'mileage': km,
                    'fuel_type': fuel,
                    'transmission': trans,
                    'owners_count': own,
                    'expected_price': Decimal(price),
                    'location_city': city,
                    'registration_state': state,
                    'condition_rating': rat,
                    'description': desc,
                    'is_verified': True,
                    'is_approved': True,
                    'is_sold': False
                }
            )

        # 14. Roadside Assistance Request
        RoadsideAssistanceRequest.objects.get_or_create(
            contact_phone='+91 98765 43210',
            vehicle_details='2022 Hyundai Creta [KA-03-MN-8842]',
            defaults={
                'user': demo_user,
                'contact_name': 'Rahul Sharma',
                'request_type': 'flat_tyre',
                'urgency': 'urgent',
                'location_address': 'Near Hosur Road Elevated Tollgate, Electronic City Phase 1',
                'city': 'Bengaluru',
                'landmark': 'Opposite Infosys Gate 3',
                'description': 'Right rear tyre punctured by metal debris on expressway. Spare tyre available in boot, jack assistance required.',
                'status': 'dispatched',
                'assigned_patrol': 'AUTOVYNEX Rapid Response Van #12',
                'estimated_arrival_minutes': 18,
                'admin_notes': 'Patrol technician Naveen dispatched. Live status communicated via SMS.'
            }
        )

        # 15. Notification for Rahul
        Notification.objects.get_or_create(
            user=demo_user,
            title='Order Shipped with Express Tracking',
            defaults={
                'message': 'Your AUTOVYNEX order AVXTRK88492011 has been dispatched from Bengaluru central fulfillment hub.',
                'link': '/orders/history/',
                'notification_type': 'order',
                'is_read': False
            }
        )
        Notification.objects.get_or_create(
            user=demo_user,
            title='Upcoming Periodic Service Due Soon',
            defaults={
                'message': 'Your Creta is approaching its 40,000 KM major maintenance milestone.',
                'link': '/garage/',
                'notification_type': 'reminder',
                'is_read': False
            }
        )

        self.stdout.write(self.style.SUCCESS("[SUCCESS] AUTOVYNEX Master Database Seeding Completed Successfully!"))
