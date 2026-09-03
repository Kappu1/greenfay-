from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    role = Column(String(50), default='admin')
    password_hash = Column(String(500), nullable=False)
    active = Column(Boolean, default=True)
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

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    booking_code = Column(String(30), unique=True, index=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    season = Column(String(30), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=True)
    booking_date = Column(Date, nullable=False)
    agreement_no = Column(String(80), index=True)
    receipt_no = Column(String(80))
    booking_type = Column(String(30), nullable=False)
    company_program = Column(String(160), default='Green Fay Farm Foods')
    total_acres = Column(Float, default=0)
    destination = Column(String(160), index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    status = Column(String(30), default='Active')
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    farmer = relationship('Farmer', back_populates='bookings')
    season_obj = relationship('Season', foreign_keys=[season_id])
    varieties = relationship('BookingVariety', back_populates='booking', cascade='all, delete-orphan')
    commitments = relationship('Commitment', back_populates='booking', cascade='all, delete-orphan')

class BookingVariety(Base):
    __tablename__ = 'booking_varieties'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    variety = Column(String(100), nullable=False, index=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True)
    acres = Column(Float, nullable=False)
    seed_type = Column(String(30), nullable=False)
    seed_source = Column(String(160))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    planned_seed_packets = Column(Float, default=0)
    expected_buyback_qty = Column(Float, default=0)
    remarks = Column(Text)
    booking = relationship('Booking', back_populates='varieties')
    variety_obj = relationship('Variety', foreign_keys=[variety_id])
    commitments = relationship('Commitment', back_populates='booking_variety')

class Commitment(Base):
    __tablename__ = 'commitments'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    contract_month = Column(String(20), nullable=False, index=True)
    contract_year = Column(Integer, nullable=False)
    contracted_bags = Column(Float, default=0)
    contracted_weight = Column(Float, default=0)
    buyback_rate = Column(Float, default=0)
    destination = Column(String(160), index=True)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    status = Column(String(30), default='Not Started')
    default_rate = Column(Float, default=0)
    rate_overridden = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    overridden_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    remarks = Column(Text)
    booking = relationship('Booking', back_populates='commitments')
    booking_variety = relationship('BookingVariety', back_populates='commitments')
    dispatch_lines = relationship('DispatchLine', back_populates='commitment')

class SeedIssue(Base):
    __tablename__ = 'seed_issues'
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    variety = Column(String(100), nullable=False)
    issue_date = Column(Date, nullable=False)
    packets = Column(Float, default=0)
    packet_weight_kg = Column(Float, default=0)
    rate_per_packet = Column(Float, default=0)
    total_value = Column(Float, default=0)
    challan_ref = Column(String(100))
    vehicle_no = Column(String(50))
    remarks = Column(Text)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active')
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    payments = relationship('SeedPayment', back_populates='seed_issue', cascade='all, delete-orphan')
    booking_variety = relationship('BookingVariety')
    supplier = relationship('Supplier')

class SeedPayment(Base):
    __tablename__ = 'seed_payments'
    id = Column(Integer, primary_key=True)
    seed_issue_id = Column(Integer, ForeignKey('seed_issues.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    mode = Column(String(50))
    reference_no = Column(String(100))
    remarks = Column(Text)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active')
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    seed_issue = relationship('SeedIssue', back_populates='payments')
    booking = relationship('Booking', foreign_keys=[booking_id])

class BardanaIssue(Base):
    __tablename__ = 'bardana_issues'
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    booking_variety_id = Column(Integer, ForeignKey('booking_varieties.id'), nullable=True)
    contract_month = Column(String(20))
    issue_date = Column(Date, nullable=False)
    bardana_type = Column(String(80), default='Potato Storage Bag')
    bardana_type_id = Column(Integer, ForeignKey('bardana_types.id'), nullable=True)
    bags_issued = Column(Float, nullable=False)
    challan_ref = Column(String(100))
    vehicle_no = Column(String(50))
    remarks = Column(Text)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Active')
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    booking_variety = relationship('BookingVariety')
    bardana_type_obj = relationship('BardanaType', foreign_keys=[bardana_type_id])

class TaxRate(Base):
    __tablename__ = 'tax_rates'
    id = Column(Integer, primary_key=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    mandi_rate_per_qtl = Column(Float, nullable=False)
    vikas_rate_per_qtl = Column(Float, nullable=False)
    mandi_cap = Column(Float)
    vikas_cap = Column(Float)
    active = Column(Boolean, default=True)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(30), default='Draft')
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    lines = relationship('DispatchLine', back_populates='dispatch', cascade='all, delete-orphan')
    transporter_obj = relationship('Transporter', foreign_keys=[transporter_id])
    destination_obj = relationship('Destination', foreign_keys=[destination_id])

class DispatchLine(Base):
    __tablename__ = 'dispatch_lines'
    id = Column(Integer, primary_key=True)
    dispatch_id = Column(Integer, ForeignKey('dispatches.id'), nullable=False)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    commitment_id = Column(Integer, ForeignKey('commitments.id'), nullable=True)
    variety = Column(String(100), nullable=False)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True)
    bags = Column(Float, default=0)
    weight_kg = Column(Float, default=0)
    remarks = Column(Text)
    status = Column(String(30), default='Active')
    
    dispatch = relationship('Dispatch', back_populates='lines')
    commitment = relationship('Commitment', back_populates='dispatch_lines')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    entity = Column(String(80), nullable=False)
    entity_id = Column(Integer)
    action = Column(String(30), nullable=False)
    details = Column(Text)
    module = Column(String(80))
    old_values = Column(Text)
    new_values = Column(Text)
    user_name = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)

# PHASE 2: MASTER DATA TABLES

class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Village(Base):
    __tablename__ = 'villages'
    id = Column(Integer, primary_key=True)
    village_name = Column(String(160), nullable=False)
    district = Column(String(120))
    state = Column(String(120), default='Punjab')
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('village_name', 'district', 'state', name='uq_village_location'),)

class Variety(Base):
    __tablename__ = 'varieties'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(30), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    default_seed_packets_per_acre = Column(Float, default=25)
    default_buyback_bags_per_acre = Column(Float, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

class Destination(Base):
    __tablename__ = 'destinations'
    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False, index=True)
    address = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    supplier_name = Column(String(160), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SeedRateMaster(Base):
    __tablename__ = 'seed_rate_masters'
    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    rate_per_packet = Column(Float, nullable=False)
    packet_weight_kg = Column(Float, default=50)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    variety = relationship('Variety')
    season = relationship('Season')

class BuybackRateMaster(Base):
    __tablename__ = 'buyback_rate_masters'
    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey('varieties.id'), nullable=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    contract_month = Column(String(20), nullable=False)
    destination_id = Column(Integer, ForeignKey('destinations.id'), nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    rate_per_bag = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    variety = relationship('Variety')
    season = relationship('Season')
    destination = relationship('Destination')

class BardanaType(Base):
    __tablename__ = 'bardana_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    bag_capacity = Column(Float, default=50)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transporter(Base):
    __tablename__ = 'transporters'
    id = Column(Integer, primary_key=True)
    transporter_name = Column(String(160), nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
