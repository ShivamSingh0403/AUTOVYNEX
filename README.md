# AUTOVYNEX — The Future of Every Drive
**Automotive Services, Spare Parts Marketplace & Vehicle Intelligence Platform**

---

## 🚗 Overview

**AUTOVYNEX** is an automotive web platform designed and built with **Python 3.13, Django 5.2 LTS, MySQL 8.4, and Vanilla HTML5/CSS3/JavaScript**. It bridges car owners, spare-parts distributors, verified workshops, and pre-owned vehicle buyers into a unified automotive ecosystem.

The system is engineered for major-project evaluation, academic review, and scalable commercial deployment. It strictly preserves standard Django template views and Vanilla JavaScript without introducing heavy front-end frameworks like React or Next.js.

---

## ⚡ Key Highlights & Architecture

- **True Full-Stack**: 11 modular Django applications, 26 database models, 34 customer and public pages, and a dedicated custom admin control center alongside standard Django admin.
- **Relational Compatibility Engine**: Multi-tier vehicle fitment verification (Compatible, Universal, Incompatible, or Compatibility Not Verified) between parts and specific make/model/variant combinations.
- **300+ Preloaded Catalog**: Preloaded with 320 realistic automotive items across 16 categories with Indian Rupee (₹) pricing, SKUs, and technical specifications.
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
| **Backend Framework** | Python 3.13 / Django 5.2 LTS |
| **Primary Database** | MySQL 8.4 Community Server |
| **Database Driver** | `mysqlclient` 2.3.0 (C-extension driver) |
| **Local Fallback** | SQLite3 (configurable via `DB_ENGINE=sqlite` in `.env`) |
| **Frontend UI** | HTML5 Semantic markup, Vanilla CSS3 (Custom Design System tokens) |
| **Frontend Scripting**| Vanilla JavaScript (ES6+), zero external front-end framework dependencies |
| **Typography** | Google Fonts (*Outfit* and *Plus Jakarta Sans*) |
| **Icons** | Lucide Icons (CDN) |
| **Media & Assets**| Django Media Upload Engine + Whitenoise Static File Storage |
| **Testing Suite** | Django Automated Test Framework (32 Comprehensive Tests) |

---

## 📁 Modular Project Structure

```
autovynex/
├── manage.py
├── .env                     # Local credentials (git-ignored)
├── .env.example             # Configuration template with placeholder settings
├── .gitignore               # Excludes secrets, venv, cache, and uploaded files
├── autovynex/               # Project Root & Core Settings
│   ├── settings.py          # Unified database & security configuration
│   ├── urls.py              # Root routing & static media routes
│   └── wsgi.py
├── accounts/                # User authentication, CustomerProfile, & notifications
├── vehicles/                # Vehicle catalog (Make, Model, Variant) & selector API
├── inventory/               # Spare parts, categories, search, filtering, wishlist, fitment
├── orders/                  # Cart logic, atomic checkout, inventory deduction, order tracking
├── garage/                  # Customer vehicle management, maintenance records, documents
├── services/                # Workshop directory, ServiceCategory, appointment booking
├── enquiries/               # "Can't Find Your Part?" sourcing desk, image uploads, history
├── used_cars/               # Certified pre-owned marketplace, valuation records, comparison
├── assistance/              # Emergency roadside assistance ticketing (simulated)
├── core/                    # Public pages, calculators, AI diagnostics, & seed script
│   ├── management/commands/seed_autovynex.py
│   └── views.py
├── custom_admin/            # Internal administrator operations center
├── static/
│   ├── css/styles.css       # Complete design system & responsive styling
│   └── js/
│       ├── main.js          # Theme switcher, modals, search autocomplete
│       ├── calculators.js   # Valuation, fuel, and TCO mathematical models
│       └── ai_help.js       # Rule-based diagnostic assistant engine
├── templates/               # Modular Django templates for all pages
└── media/                   # User-uploaded invoices, parts, and car photos
```

---

## 🗄️ MySQL 8.4 Database Configuration & Safe Setup

### 1. Database Creation (MySQL 8.4)
Log into your MySQL Server via MySQL CLI or MySQL Workbench:
```sql
-- Connect as root or privileged administrator
mysql -u root -p

-- Create the database with full UTF-8 Unicode support
CREATE DATABASE autovynex_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- (Optional) Create a dedicated project user with permissions
CREATE USER 'autovynex_user'@'localhost' IDENTIFIED BY 'StrongPassword@2026';
GRANT ALL PRIVILEGES ON autovynex_db.* TO 'autovynex_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify creation
SHOW DATABASES;
EXIT;
```

### 2. Environment Variables Configuration
Never commit sensitive credentials. All database and security settings are loaded from `.env`.

Create `.env` by copying `.env.example`:
```powershell
Copy-Item .env.example .env
```

Configure `.env` for your environment:

#### Option A: MySQL 8.4 (Target Database)
```env
SECRET_KEY=django-insecure-autovynex-local-development-key-change-in-prod-xyz123
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database Configuration
DB_ENGINE=mysql
DB_NAME=autovynex_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

#### Option B: SQLite3 Fallback (Instant zero-config local testing)
```env
DB_ENGINE=sqlite
DB_NAME=autovynex_db.sqlite3
```

---

## 🚀 Windows PowerShell Commands

### 1. Prerequisites Check
Verify Python and pip are available in PowerShell:
```powershell
python --version
pip --version
```

### 2. Virtual Environment Setup
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install django==5.2a1 mysqlclient
```

### 3. Verify Django System Checks
Run the Django configuration check:
```powershell
python manage.py check
```

### 4. Apply Database Migrations
Safely run migrations to build all 26 relational tables:
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 5. Populate Sample Catalog (Idempotent Seed Command)
Populate 10+ vehicle makes, 40+ variants, 16 categories, 20+ brands, 320+ products, fitments, service providers, and sample demo listings:
```powershell
python manage.py seed_autovynex
```
*Note: This command is idempotent. Running it multiple times safely updates or skips existing records without duplicating.*

### 6. Create Superuser / Administrator
```powershell
python manage.py createsuperuser
```
*(Or use the pre-seeded admin credentials below).*

### 7. Run Automated Tests
Execute the complete test suite covering all 9 core applications:
```powershell
python manage.py test
```

### 8. Start Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```
Open your browser at: **`http://127.0.0.1:8000/`**

---

## 🔑 Pre-Configured Demo Credentials

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@12345` | Django Admin (`/admin/`) and Custom Operations Center (`/custom-admin/`) |
| **Demo Customer** | `rahul` | `Customer@12345` | Access to My Garage (Creta & Swift pre-loaded), Orders, Wishlist |

---

## 🔧 Database Connection Troubleshooting Guide

| Issue / Error | Root Cause | Solution |
|---|---|---|
| `OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1:3306'")` | MySQL Windows service is stopped or not running on port 3306. | Open PowerShell as Administrator and run:<br>`Get-Service -Name MySQL*`<br>`Start-Service MySQL84` (or your MySQL service name). |
| `OperationalError: (1045, "Access denied for user 'root'@'localhost'")` | Incorrect MySQL password in `.env`. | Verify password in `.env`. Reset root password or create a dedicated user: `ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';`. |
| `OperationalError: (1049, "Unknown database 'autovynex_db'")` | The database has not been created yet in MySQL. | Run `mysql -u root -p -e "CREATE DATABASE autovynex_db CHARACTER SET utf8mb4;"` in PowerShell. |
| `django.core.exceptions.ImproperlyConfigured: Error loading MySQLdb module` | `mysqlclient` C-extension is not installed or lacks C++ runtime. | Run `pip install mysqlclient`. If Microsoft C++ Build Tools are missing, install the precompiled `.whl` from Christoph Gohlke's wheels or switch `.env` to `DB_ENGINE=sqlite` for immediate work. |
| `django.db.utils.OperationalError: (1118, 'Row size too large')` | Legacy table formatting. | Ensure MySQL configuration uses `innodb_file_per_table=1` and `utf8mb4` encoding (default in MySQL 8.4). |

---

## 🛡️ Security & Upload Requirements

- **File Validation**: Strict server-side validation on file extensions (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`) and maximum file size (5MB). Disallowed file types are rejected before persistence.
- **Customer Data Isolation**: All garage vehicles, maintenance records, reminders, documents, orders, and private sourcing enquiries enforce `user=request.user` ownership checks.
- **Cart & Order Integrity**: Prices, discount deductions, sub-totals, and shipping fees are calculated server-side. Browser-supplied monetary values are strictly ignored.
- **Race Condition Prevention**: Order processing uses `select_for_update()` inside `transaction.atomic()` to guarantee inventory integrity under concurrent requests.
- **Password Protection**: Native Django PBKDF2 with SHA-256 password hashing. Plaintext passwords are never stored.
- **Simulated Demonstration**: Used-car valuation explicitly displays an academic disclaimer ("algorithmic estimate rather than guaranteed market price"), and roadside assistance ticketing is marked as simulated demo requests.

---

## 📄 License & Attribution
Designed and built for major project review, academic evaluation, and enterprise scaling.
AUTOVYNEX © 2026. All Rights Reserved.
