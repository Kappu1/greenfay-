from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    role = Column(String(50), default='admin')  # admin, operator, seed, bardana, qc, accounts, viewer
    password_hash = Column(String(500), nullable=False)
    active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Farmer(Base):
    __tablename__ = 'farmers'
    id = Column(Integer, primary_key=True)
    farmer_code = Column(String(30), unique=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    relation_name = Column(String(160))
    relation_type = Column(String(40), default='Father')
    mobile = Column(String(20), index=True)
    alternate_mobile = Column(String(20))
    village = Column(String(160), index=True)
    village_id = Column(Integer, ForeignKey('villages.id'), nullable=True)
    address = Column(Text)
    district = Column(String(120))
    state = Column(String(120), default='Punjab')
    remarks = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bookings = relationship('Booking', back_populates='farmer')

    __table_args__ = (
        Index('idx_farmer_name_mobile', 'name', 'mobile'),
    )

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    booking_code = Column(String(30), unique=True, index=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False, index=True)
    season = Column(String(30), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=True, index=True)
    booking_date = Column(Date, nullable=False, index=True)
    agreement_no = Column(String(80), index=True)
    receipt_no = Column(String(80))
    booking_type = Column(String(30), nullable=False)  # With Seed, Without Seed, Mixed
    company_program = Column(String(160), default='Green Fay Farm Foods')
    total_acres = Column(Float, default=0)
    destination = Column(String(160), index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    status = Column(String(30), default='Active', index=True)  # Active, Draft, Completed, Cancelled
    version_id = Column(Integer, default=1)
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    farmer = relationship('Farmer', back_populates='bookings')
    season_obj = relationship('Season', foreign_keys=[season_id])
    varieties = relationship('BookingVariety', back_populates='booking', cascade='all, delete-orphan')
    commitments = relationship('Commitment', back_populates='booking', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('total_acres >= 0', name='ck_booking_acres_positive'),
        Index('idx_booking_season_status', 'season', 'status'),
    )

class BookingVariety(Base):
    __tablename__ = 'booking_varieties'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False, index=True)
    variety = Column(String(100), nullable=False, index=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True)
    acres = Column(Float, nullable=False)
    seed_type = Column(String(30), nullable=False)  # With Seed, Without Seed
    seed_source = Column(String(160))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    planned_seed_packets = Column(Float, default=0)
    expected_buyback_qty = Column(Float, default=0)
    remarks = Column(Text)
    booking = relationship('Booking', back_populates='varieties')
    variety_obj = relationship('Variety', foreign_keys=[variety_id])
    commitments = relationship('Commitment', back_populates='booking_variety')

    __table_args__ = (
        CheckConstraint('acres >= 0', name='ck_variety_acres_positive'),
    )

class Commitment(Base):
    __tablename__ = 'commitments'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False, index=True)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    contract_month = Column(String(20), nullable=False, index=True)
    contract_year = Column(Integer, nullable=False, index=True)
    contracted_bags = Column(Float, default=0)
    contracted_weight = Column(Float, default=0)
    buyback_rate = Column(Float, default=0)
    destination = Column(String(160), index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    status = Column(String(30), default='Not Started', index=True)  # Not Started, In Progress, Completed, Excess Supplied, Cancelled
    version_id = Column(Integer, default=1)
    default_rate = Column(Float, default=0)
    rate_overridden = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    overridden_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    remarks = Column(Text)
    booking = relationship('Booking', back_populates='commitments')
    booking_variety = relationship('BookingVariety', back_populates='commitments')
    dispatch_lines = relationship('DispatchLine', back_populates='commitment')

    __table_args__ = (
        CheckConstraint('contracted_bags >= 0', name='ck_commitment_bags_positive'),
        Index('idx_commitment_month_status', 'contract_month', 'status'),
    )

class SeedIssue(Base):
    __tablename__ = 'seed_issues'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False, index=True)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    variety = Column(String(100), nullable=False)
    issue_date = Column(Date, nullable=False, index=True)
    packets = Column(Float, default=0)
    packet_weight_kg = Column(Float, default=0)
    rate_per_packet = Column(Float, default=0)
    total_value = Column(Float, default=0)
    challan_ref = Column(String(100))
    vehicle_no = Column(String(50))
    remarks = Column(Text)
    version_id = Column(Integer, default=1)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active', index=True)  # Active, Cancelled
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    payments = relationship('SeedPayment', back_populates='seed_issue', cascade='all, delete-orphan')
    booking_variety = relationship('BookingVariety')
    supplier = relationship('Supplier')

    __table_args__ = (
        CheckConstraint('packets >= 0', name='ck_seed_packets_positive'),
    )

class SeedPayment(Base):
    __tablename__ = 'seed_payments'
    id = Column(Integer, primary_key=True)
    seed_issue_id = Column(Integer, ForeignKey('seed_issues.id'), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=True, index=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=True, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    mode = Column(String(50))  # Cash, Bank Transfer, UPI, Cheque, Adjustment
    reference_no = Column(String(100))
    remarks = Column(Text)
    version_id = Column(Integer, default=1)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active', index=True)  # Active, Cancelled
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    seed_issue = relationship('SeedIssue', back_populates='payments')
    booking = relationship('Booking', foreign_keys=[booking_id])

    __table_args__ = (
        CheckConstraint('amount > 0', name='ck_seed_payment_amount_positive'),
    )

class BardanaIssue(Base):
    __tablename__ = 'bardana_issues'
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False, index=True)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    contract_month = Column(String(20))
    issue_date = Column(Date, nullable=False, index=True)
    bardana_type = Column(String(80), default='Potato Storage Bag')
    bardana_type_id = Column(Integer, ForeignKey('bardana_types.id'), nullable=True)
    bags_issued = Column(Float, nullable=False)
    challan_ref = Column(String(100))
    vehicle_no = Column(String(50))
    remarks = Column(Text)
    version_id = Column(Integer, default=1)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active', index=True)  # Active, Cancelled
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    booking_variety = relationship('BookingVariety')
    bardana_type_obj = relationship('BardanaType', foreign_keys=[bardana_type_id])

    __table_args__ = (
        CheckConstraint('bags_issued >= 0', name='ck_bardana_bags_positive'),
    )

class TaxRate(Base):
    __tablename__ = 'tax_rates'
    id = Column(Integer, primary_key=True)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, index=True)
    mandi_rate_per_qtl = Column(Float, nullable=False)
    vikas_rate_per_qtl = Column(Float, nullable=False)
    mandi_cap = Column(Float)
    vikas_cap = Column(Float)
    active = Column(Boolean, default=True, index=True)
    remarks = Column(Text)

class Dispatch(Base):
    __tablename__ = 'dispatches'
    id = Column(Integer, primary_key=True)
    dispatch_code = Column(String(30), unique=True, index=True)
    dispatch_date = Column(Date, nullable=False, index=True)
    truck_no = Column(String(50), index=True)
    transporter = Column(String(160))
    transporter_id = Column(Integer, ForeignKey('transporters.id'), nullable=True)
    destination = Column(String(160), index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    tax_rate_id = Column(Integer, ForeignKey('tax_rates.id'), nullable=True)
    gatepass_no = Column(String(80), index=True)
    nine_r_no = Column(String(80))
    actual_weight_kg = Column(Float, default=0)
    mandi_weight_kg = Column(Float, default=0)
    mandi_rate = Column(Float, default=0)
    vikas_rate = Column(Float, default=0)
    mandi_cap = Column(Float)
    vikas_cap = Column(Float)
    mandi_tax = Column(Float, default=0)
    vikas_sulk = Column(Float, default=0)
    remarks = Column(Text)
    version_id = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Draft', index=True)  # Draft, Finalized, Cancelled
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    lines = relationship('DispatchLine', back_populates='dispatch', cascade='all, delete-orphan')
    transporter_obj = relationship('Transporter', foreign_keys=[transporter_id])
    destination_obj = relationship('Destination', foreign_keys=[destination_id])

    __table_args__ = (
        CheckConstraint('actual_weight_kg >= 0', name='ck_dispatch_actual_weight_positive'),
        CheckConstraint('mandi_weight_kg >= 0', name='ck_dispatch_mandi_weight_positive'),
        Index('idx_dispatch_date_status', 'dispatch_date', 'status'),
    )

class DispatchLine(Base):
    __tablename__ = 'dispatch_lines'
    id = Column(Integer, primary_key=True)
    dispatch_id = Column(Integer, ForeignKey('dispatches.id'), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False, index=True)
    commitment_id = Column(Integer, ForeignKey('commitments.id'), nullable=True, index=True)
    variety = Column(String(100), nullable=False)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True)
    bags = Column(Float, default=0)
    weight_kg = Column(Float, default=0)
    remarks = Column(Text)
    status = Column(String(30), default='Active', index=True)  # Active, Cancelled
    
    dispatch = relationship('Dispatch', back_populates='lines')
    commitment = relationship('Commitment', back_populates='dispatch_lines')

    __table_args__ = (
        CheckConstraint('bags >= 0', name='ck_line_bags_positive'),
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    entity = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, index=True)
    action = Column(String(30), nullable=False, index=True)  # CREATE, UPDATE, FINALIZE, CANCEL, DELETE, LOCK, UNLOCK, IMPORT, ROLLBACK
    details = Column(Text)
    module = Column(String(80), index=True)
    old_values = Column(Text)
    new_values = Column(Text)
    user_name = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# MASTER DATA TABLES

class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    active = Column(Boolean, default=True, index=True)
    status = Column(String(30), default='Open', index=True)  # Open, Closing, Locked, Archived
    locked_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    lock_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Village(Base):
    __tablename__ = 'villages'
    id = Column(Integer, primary_key=True)
    village_name = Column(String(160), nullable=False, index=True)
    district = Column(String(120))
    state = Column(String(120), default='Punjab')
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('village_name', 'district', 'state', name='uq_village_location'),)

class Variety(Base):
    __tablename__ = 'varieties'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(30), unique=True, nullable=False)
    active = Column(Boolean, default=True, index=True)
    default_seed_packets_per_acre = Column(Float, default=25)
    default_buyback_bags_per_acre = Column(Float, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

class Destination(Base):
    __tablename__ = 'destinations'
    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False, index=True)
    address = Column(Text)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    supplier_name = Column(String(160), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SeedRateMaster(Base):
    __tablename__ = 'seed_rate_masters'
    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, index=True)
    rate_per_packet = Column(Float, nullable=False)
    packet_weight_kg = Column(Float, default=50)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    variety = relationship('Variety')
    season = relationship('Season')

class BuybackRateMaster(Base):
    __tablename__ = 'buyback_rate_masters'
    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False, index=True)
    contract_month = Column(String(20), nullable=False, index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True, index=True)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, index=True)
    rate_per_bag = Column(Float, nullable=False)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    variety = relationship('Variety')
    season = relationship('Season')
    destination = relationship('Destination')

class BardanaType(Base):
    __tablename__ = 'bardana_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    bag_capacity = Column(Float, default=50)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transporter(Base):
    __tablename__ = 'transporters'
    id = Column(Integer, primary_key=True)
    transporter_name = Column(String(160), nullable=False, index=True)
    phone = Column(String(20))
    address = Column(Text)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# PHASE 3: PRODUCTION, DOCUMENTS, MIGRATION & SYSTEM TABLES

class DocumentAttachment(Base):
    __tablename__ = 'document_attachments'
    id = Column(Integer, primary_key=True)
    document_id = Column(String(64), unique=True, index=True, nullable=False)  # UUID
    entity_type = Column(String(50), nullable=False, index=True)  # Farmer, Booking, SeedIssue, SeedPayment, BardanaIssue, Dispatch
    entity_id = Column(Integer, nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # Agreement, Booking Receipt, Farmer ID, Seed Challan, Payment Proof, Bardana Challan, Gatepass, 9R, Transport Document, Other
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)

class MigrationBatch(Base):
    __tablename__ = 'migration_batches'
    id = Column(Integer, primary_key=True)
    batch_code = Column(String(40), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    source_type = Column(String(50), nullable=False)  # Booking, Without Seed, Seed Multiply, Dispatch, Custom
    uploaded_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(40), default='Uploaded', index=True)  # Uploaded, Mapping, Validating, Review Required, Ready, Importing, Completed, Failed, Rolled Back
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    warning_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    mapping_config_json = Column(Text, nullable=True)
    reconciliation_json = Column(Text, nullable=True)
    
    rows = relationship('MigrationRow', back_populates='batch', cascade='all, delete-orphan')

class MigrationRow(Base):
    __tablename__ = 'migration_rows'
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('migration_batches.id'), nullable=False, index=True)
    sheet_name = Column(String(100), nullable=True)
    row_number = Column(Integer, nullable=False)
    raw_data_json = Column(Text, nullable=False)
    normalized_data_json = Column(Text, nullable=True)
    status = Column(String(30), default='Valid', index=True)  # Valid, Warning, Error, Ignored, Imported
    warning_messages_json = Column(Text, nullable=True)
    error_messages_json = Column(Text, nullable=True)
    match_farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=True)
    match_confidence = Column(String(30), nullable=True)  # Exact, Likely Match, Possible Match, No Match
    match_decision = Column(String(30), default='Link')  # Link, Create, Ignore
    final_entity_type = Column(String(50), nullable=True)
    final_entity_id = Column(Integer, nullable=True)

    batch = relationship('MigrationBatch', back_populates='rows')

class MigrationMappingTemplate(Base):
    __tablename__ = 'migration_mapping_templates'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    mapping_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = 'system_settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
