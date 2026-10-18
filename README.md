# AUTOVYNEX — The Future of Every Drive
**Automotive Services, Spare Parts Marketplace & Vehicle Intelligence Platform**

---

## 🚗 Overview
**AUTOVYNEX** is an automotive web platform designed and built with **Django 5.2 LTS, MySQL 8.4, and Vanilla HTML5/CSS3/JavaScript**. It bridges car owners, spare-parts distributors, verified workshops, and pre-owned vehicle buyers into an ecosystem.

The system is engineered for major-project evaluation, academic review, and scalable commercial deployment.

---

## ⚡ Key Highlights & Architecture

- **True Full-Stack**: 11 modular Django applications, 26 database models, 34 customer and public pages, and a dedicated custom admin control center alongside standard Django admin.
- **Relational Compatibility Engine**: Multi-tier vehicle fitment verification (Compatible, Not Confirmed, Incompatible) between parts and specific make/model/variant combinations.
- **300+ Sample Products**: Preloaded with 320 realistic automotive items across 16 categories with Indian Rupee (₹) pricing, SKUs, and technical specifications.
- **Digital My Garage**: Customer vehicle profiles, maintenance logs, expense tracking, service reminders, and secure document vaults.
- **Service & Workshop Booking**: Real-time slot reservation across verified multi-brand car workshops with duplicate booking prevention.
- **Interactive Automotive Intelligence**:
  - Rule-based AI Automotive Assistant for symptom diagnostics.
  - Car Valuation Calculator with documented depreciation algorithm.
  - Fuel Cost & Commute Calculator.
  - 5-Year Total Cost of Ownership (TCO) Calculator.
  - Used-Car Marketplace & Side-by-Side Comparison Matrix.
  - Rare Missing-Part Sourcing Desk with photo upload.
  - 24/7 Roadside Assistance dispatch ticketing.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13 / Django 5.2 LTS |
| **Database** | MySQL 8.4 (with instant SQLite3 local fallback) |
| **Frontend** | HTML5, Vanilla CSS3 (Custom Design System), Vanilla ES6 JavaScript |
| **Typography** | Outfit & Plus Jakarta Sans via Google Fonts |
| **Icons** | Lucide Icons CDN |
| **Media & Assets**| Django Media Engine + Whitenoise Static Storage |
| **Testing** | Django Automated Test Framework (`core/tests.py`) |

---

## 📁 Modular Project Structure

```
Car Delights/
├── manage.py
├── autovynex/               # Project Root & Core Settings
│   ├── settings.py          # Unified database & security configuration
│   ├── urls.py              # Root routing & static media routes
│   └── wsgi.py
├── core/                    # Public pages, calculators, AI diagnostics, & seed script
│   ├── management/commands/seed_autovynex.py
│   ├── tests.py             # 9 Automated regression tests
│   └── views.py
├── accounts/                # User authentication, profiles, & notifications
├── vehicles/                # Vehicle catalog (Make, Model, Variant) & selector API
├── inventory/               # Spare parts, categories, search, filtering, wishlist
├── orders/                  # Cart logic, atomic checkout, & order tracking
├── garage/                  # Customer vehicle management & service history
├── services/                # Workshop directory & appointment booking
├── enquiries/               # "Can't Find Your Part?" sourcing desk
├── used_cars/               # Certified pre-owned marketplace & comparison matrix
├── assistance/              # Emergency roadside assistance ticketing
├── custom_admin/            # Internal administrator operations center
├── static/
│   ├── css/styles.css       # Complete design system & responsive styling
│   └── js/
│       ├── main.js          # Theme switcher, modals, search autocomplete
│       ├── calculators.js   # Valuation, fuel, and TCO mathematical models
│       └── ai_help.js       # Rule-based diagnostic assistant engine
├── templates/               # Modular Django templates for all 34 pages
├── media/                   # User-uploaded invoices, parts, and car photos
├── .env.example             # Configuration template
└── README.md
```

---

## 🚀 Setup & Local Execution (Windows / PowerShell)

### 1. Prerequisites
- Python 3.11+ installed and added to PATH.
- (Optional) MySQL 8.4 Server installed and running on port 3306.

### 2. Virtual Environment Setup
Open PowerShell in the project directory:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the sample environment file:
```powershell
Copy-Item .env.example .env
```
Open `.env` in any editor:
- **Default / Immediate Testing (SQLite3)**:
  `DB_ENGINE=sqlite` *(Zero database setup required, ready immediately!)*
- **Production / MySQL 8.4**:
  ```env
  DB_ENGINE=mysql
  DB_NAME=autovynex_db
  DB_USER=root
  DB_PASSWORD=your_mysql_password
  DB_HOST=127.0.0.1
  DB_PORT=3306
  ```
  *(Make sure to run `CREATE DATABASE autovynex_db CHARACTER SET utf8mb4;` in MySQL first).*

### 4. Database Migrations
Apply all schema migrations:
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Realistic Demonstration Data
Run the built-in seeding command to populate 320+ products, 48 car variants, fitments, workshops, and demo users:
```powershell
python manage.py seed_autovynex
```

### 6. Run the Automated Test Suite
Verify that all core business logic, cart math, atomic transactions, and access control pass:
```powershell
python manage.py test core
```

### 7. Start the Development Server
```powershell
python manage.py runserver 8000
```
Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 🔑 Pre-Configured Demo Credentials

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@12345` | Access to `/custom-admin/` and `/admin/` |
| **Demo Customer** | `rahul` | `Customer@12345` | Access to My Garage (Creta & Swift pre-loaded), Orders, Wishlist |

---

## 🗺️ Complete Site Directory (34 Pages + Admin)

### 🌐 Public & Customer Experience
1. **Homepage**: `/`
2. **Spare Parts Marketplace**: `/shop/`
3. **Product Details**: `/shop/product/<slug>/`
4. **Vehicle Selector**: `/vehicles/selector/`
5. **Shopping Cart**: `/orders/cart/`
6. **Checkout (Simulated)**: `/orders/checkout/`
7. **Customer Login**: `/accounts/login/`
8. **Customer Registration**: `/accounts/register/`
9. **Forgot Password**: `/accounts/forgot-password/`
10. **My Garage Dashboard**: `/garage/`
11. **Vehicle Details & Service History**: `/garage/vehicle/<id>/`
12. **Book a Workshop Service**: `/services/book/`
13. **Service Provider Directory**: `/services/`
14. **Used Car Marketplace**: `/used-cars/`
15. **Used Car Details**: `/used-cars/<id>/`
16. **Used Car Comparison Tool**: `/used-cars/compare/`
17. **Car Valuation Calculator**: `/car-valuation/`
18. **Fuel Cost Calculator**: `/fuel-calculator/`
19. **5-Year Ownership Cost (TCO) Calculator**: `/ownership-calculator/`
20. **AI Car Help Diagnostic Assistant**: `/ai-car-help/`
21. **24/7 Roadside Assistance Request**: `/assistance/`
22. **Missing Part Sourcing ("Can't Find Your Part?")**: `/enquiries/missing-part/`
23. **Promotions & Offers**: `/offers/`
24. **About AUTOVYNEX**: `/about/`
25. **Contact Us & Support**: `/contact/`
26. **Customer Control Dashboard**: `/dashboard/`
27. **Order History**: `/orders/history/`
28. **Order Details**: `/orders/order/<order_number>/`
29. **Wishlist**: `/shop/wishlist/`
30. **Notifications Inbox**: `/accounts/notifications/`
31. **Profile & Account Settings**: `/accounts/profile/`
32. **Privacy Policy**: `/privacy-policy/`
33. **Terms and Conditions**: `/terms-and-conditions/`
34. **Custom 404 Error Handler**: `templates/404.html`

### ⚙️ Administrator Portals
- **AUTOVYNEX Custom Admin Center**: `/custom-admin/`
  - Executive KPI Analytics (Orders, Revenue, Inventory, Enquiries)
  - Orders Dispatch & Tracking Manager: `/custom-admin/orders/`
  - Inventory Stock Monitor: `/custom-admin/inventory/`
  - Rare Part Sourcing Requests: `/custom-admin/enquiries/`
  - Workshop Booking Manager: `/custom-admin/services/`
  - Roadside Assistance Dispatch Desk: `/custom-admin/assistance/`
- **Django Standard Admin**: `/admin/`

---

## 🔒 Security & Best Practices

- **Role-Based Access Control**: Non-administrators attempting to enter `/custom-admin/` or `/admin/` receive an immediate permission denial.
- **Customer Data Isolation**: Users can strictly query and modify their own vehicles, service invoices, order receipts, and missing part tickets.
- **Race Condition Prevention**: Order processing uses `select_for_update()` inside `transaction.atomic()` to guarantee inventory integrity under concurrent requests.
- **Simulated Payment Compliance**: The checkout flow clearly clarifies demo status and never stores raw card or CVV details.
- **CSRF & Password Hashing**: Enforced across every dynamic form using Django's built-in CSRF token protection and PBKDF2 password hashing.

---

## 📄 License & Attribution
Designed and built for academic presentation, portfolio evaluation, and future commercial scaling.
AUTOVYNEX © 2026. All Rights Reserved.
