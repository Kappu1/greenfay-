# GreenFay Farm Foods — Potato Contract Farming Management Platform (Phase 2)

A comprehensive, production-grade web application for potato contract-farming operations.

## Features Overview

### 1. Master Data Management
- **Seasons Master**: Date-bounded seasons (e.g., 2025–26) with active status flags.
- **Villages Master**: Village, district, state registry with uniqueness checks.
- **Varieties Master**: Seed potato varieties (LR, Fry Sona, Chipsona, CH-3, TB32, Santana, Innovator, GF1) with default packets/acre and expected buyback yields.
- **Destinations Master**: Delivery points (Plant, Cold Store) with addresses.
- **Seed Suppliers Master**: Seed sources (Green Fay Farm Foods, etc.).
- **Seed Rate Master**: Season- and variety-specific packet pricing with effective date tracking and auto-lookup.
- **Buyback Rate Master**: Multi-dimensional buyback pricing by variety, season, contract month, and destination.
- **Bardana Types Master**: Bag types and capacity (e.g., 50 KG storage bag).
- **Transporters Master**: Fleet and transporter directory.
- **Mandi Tax & Vikas Sulk Rate Master**: Statutory rate schedules with date ranges and maximum liability caps.

### 2. Farmer Management & Farmer 360°
- Comprehensive farmer registry with code auto-generation (`FAR-000001`).
- Duplicate detection warning by name, village, and mobile number.
- Pagination, search, and status filters.
- **Farmer 360° Profile**: Tabbed view summarizing:
  - Total bookings and acres committed.
  - Seed value, payments received, and outstanding balance status (Completed / Partial / Not Paid).
  - Bardana bags issued and pending.
  - Contract commitments, actual deliveries, and pending bags.
  - Complete operational history (Bookings, Commitments, Seed Issues, Payments, Bardana, Dispatches, Audit).

### 3. Bookings & Multi-Variety Commitments
- Booking agreements (`BKG-000001`) with season, agreement number, receipt number, and booking type.
- **Dynamic Multi-Variety Lines**: Add multiple potato varieties per booking with acres, seed mode, planned seed packets, and expected buyback yield.
- **Month-wise Contract Commitments**: Commit delivery bags across months (e.g., Jan, Feb, Mar) with variety mapping, destination, and buyback rate.
- Status tracking: Draft, Active, Completed, Cancelled.

### 4. Seed Distribution & Payments
- Seed issues linked to farmer, booking, and variety lines with auto-lookup from Seed Rate Master.
- Price snapshots stored on issues to ensure immutable historical accounting.
- Transaction-based payments with payment mode (Cash, Bank Transfer, UPI, Cheque, Adjustment) and reference numbers.
- Live balance tracking and payment status classification.
- Cancellation workflow with reason and audit logging.

### 5. Bardana (Bag) Management
- Bag issues linked to farmer and booking with challan and vehicle reference.
- Dynamic balance calculation per booking: `Pending = Contracted Bags - Issued Bags`.
- Cancellation workflow with reason.

### 6. Procurement & Potato Dispatch
- **Two-Level Dispatch**: Truck header (truck number, transporter, gatepass, 9R, destination, actual weight, Mandi weight) + multi-line farmer varieties.
- **Automated Mandi Tax & Vikas Sulk**:
  - `Taxable Quintals = Mandi Weight KG / 100`
  - `Mandi Tax = min(Taxable Quintals × Mandi Rate, Mandi Cap)`
  - `Vikas Sulk = min(Taxable Quintals × Vikas Rate, Vikas Cap)`
  - Auto-selects effective rate schedule based on dispatch date.
- **Workflow States**:
  - **Draft**: Dispatches can be edited or lines added/removed. Draft dispatches **do not** affect contract balances.
  - **Finalized**: Locks the record, calculates and snapshots tax, and updates contract delivery progress.
  - **Cancelled**: Reverses dispatch lines and rolls back contract delivery balances.

### 7. Contract Due / Procurement Dashboard
- Real-time commitment fulfillment tracking.
- Calculated metrics: Received Bags, Pending Bags, Completion %, Status (Not Started, In Progress, Completed, Excess Supplied).
- Comprehensive multi-parameter filtering: Month, Variety, Farmer, Status, Destination, Season.

### 8. Report Center (XLSX & PDF Exports)
- **Excel (.xlsx) with OpenPyXL**:
  - Farmer Register
  - Booking Register
  - Month-wise Contracts
  - Seed Distribution
  - Seed Payment Outstanding
  - Bardana Issued
  - Procurement Due
  - Dispatch Register
  - Mandi Tax & Vikas Sulk Register
- **PDF Reports with ReportLab**:
  - Procurement Due Report
  - Dispatch Report
  - Seed Outstanding Report
  - Mandi Tax & Vikas Sulk Report
- **CSV**: Backward-compatible Month-wise Contract Status export.

### 9. Audit Trail
- System-wide audit log tracking user ID, user name, entity, action (CREATE, UPDATE, FINALIZE, CANCEL), timestamp, and change details.

---

## Technical Architecture

- **Backend**: FastAPI 0.115+
- **Database**: SQLite (via SQLAlchemy 2.0 ORM; fully compatible with PostgreSQL)
- **Frontend**: Server-served SPA (Single Page Application) with vanilla ES6+ JavaScript, custom GreenFay agricultural theme CSS, modal dialogs, and toast notifications.
- **Excel Generation**: `openpyxl` with styled headers, autofilters, and totals.
- **PDF Generation**: `reportlab` with corporate headers, formatted tables, and page numbering.
- **Testing**: `pytest` test suite with in-memory database isolation.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12 and 3.13)

### 2. Installation
```bash
# Clone or navigate to the project root
cd greenfay_fullstack

# Activate virtual environment
.venv\Scripts\activate   # On Windows
# source .venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Database Migration (if upgrading from V1.1)
```bash
python migrate.py
```

### 4. Start the Application
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
`http://127.0.0.1:8000`

### Demo Credentials
- **Email**: `admin@greenfay.local`
- **Password**: `admin123`

---

## Running Automated Tests

Run the full calculation and integration test suite:
```bash
pytest tests/ -v
```

All tests execute against an isolated in-memory SQLite database, verifying:
1. Statutory tax and cap calculation logic
2. Master data CRUD
3. Farmer creation with duplicate warnings
4. Multi-variety booking and commitment creation
5. Seed issue and payment calculations
6. Bardana distribution and balance calculation
7. Dispatch draft vs finalized state transitions and balance rollbacks on cancellation
8. Farmer 360° summary cards
9. XLSX and PDF report generation
10. Audit log logging
