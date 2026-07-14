import datetime
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class HCP(Base):
    __tablename__ = 'hcps'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    clinic_name = Column(String(150), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    last_interaction_date = Column(String(50), nullable=True)
    
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey('hcps.id'), nullable=False)
    date = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)  # In-Person, Video Call, Email, Phone
    topics = Column(String(255), nullable=False)   # Comma-separated list of topics
    sentiment = Column(String(50), nullable=False) # Positive, Neutral, Negative
    notes = Column(Text, nullable=False)
    follow_up_date = Column(String(50), nullable=True)
    next_step = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    hcp = relationship("HCP", back_populates="interactions")

# Determine engine & session maker
engine = None
SessionLocal = None

def init_db_connection():
    global engine, SessionLocal
    mysql_url = settings.DATABASE_URL
    sqlite_url = settings.SQLITE_FALLBACK_URL
    
    # Try MySQL first
    try:
        logger.info("Attempting to connect to MySQL database...")
        # We try to connect without database name first to create it if not exists, or direct connection
        # To avoid failure if database doesn't exist, we try to create it.
        # But pymysql connection URL parsing is needed:
        if "mysql" in mysql_url:
            try:
                from sqlalchemy_utils import database_exists, create_database
                if not database_exists(mysql_url):
                    create_database(mysql_url)
            except Exception:
                logger.info("sqlalchemy_utils not available or database check failed; proceeding with simple connection.")
        
        # Simple test connection
        engine = create_engine(mysql_url, pool_pre_ping=True)
        # Force a connection check
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Successfully connected to MySQL database!")
    except Exception as e:
        logger.warning(f"Failed to connect to MySQL database: {e}")
        logger.info("Falling back to local SQLite database...")
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize on import
init_db_connection()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_data(db):
    # Check if empty
    if db.query(HCP).count() > 0:
        return
        
    logger.info("Seeding database with mock HCP profiles and interaction logs...")
    
    # Create mock HCPs
    hcps = [
        HCP(
            name="Dr. Sarah Jenkins", 
            specialty="Cardiology", 
            clinic_name="Metro Heart Clinic", 
            email="sarah.jenkins@metroheart.com", 
            phone="+1-555-0192",
            last_interaction_date="2026-07-05"
        ),
        HCP(
            name="Dr. Robert Chen", 
            specialty="Oncology", 
            clinic_name="City Cancer Center", 
            email="r.chen@citycancer.org", 
            phone="+1-555-0143",
            last_interaction_date="2026-06-28"
        ),
        HCP(
            name="Dr. Emily Taylor", 
            specialty="Pediatrics", 
            clinic_name="Children's Health Hospital", 
            email="etaylor@childrenshealth.org", 
            phone="+1-555-0177",
            last_interaction_date="2026-07-10"
        ),
        HCP(
            name="Dr. David Patel", 
            specialty="Neurology", 
            clinic_name="Brain & Spine Institute", 
            email="dpatel@brainspine.com", 
            phone="+1-555-0158",
            last_interaction_date="2026-07-02"
        ),
        HCP(
            name="Dr. Lisa Cooper", 
            specialty="Endocrinology", 
            clinic_name="Diabetes Care Center", 
            email="lisa.cooper@diabetescenter.com", 
            phone="+1-555-0112",
            last_interaction_date="2026-06-15"
        )
    ]
    
    db.add_all(hcps)
    db.commit()
    
    # Add some mock interaction history
    interactions = [
        Interaction(
            hcp_id=hcps[0].id,
            date="2026-07-05",
            channel="In-Person",
            topics="CardioSphere-10mg, Clinical Trial Results",
            sentiment="Positive",
            notes="Dr. Jenkins was very enthusiastic about the new clinical trial data for CardioSphere. She noted a 15% improvement in patient outcome. She requested sample packs and product brochures.",
            follow_up_date="2026-07-20",
            next_step="Deliver CardioSphere sample packs and brochures to her clinic."
        ),
        Interaction(
            hcp_id=hcps[1].id,
            date="2026-06-28",
            channel="Video Call",
            topics="OncoShield-X, Patient Patient Enrollment",
            sentiment="Neutral",
            notes="Discussed patient enrollment for the new OncoShield-X phase 3 trial. Dr. Chen raised questions regarding side-effect profile and patient eligibility criteria. He wants to review safety data sheets.",
            follow_up_date="2026-07-15",
            next_step="Email safety data sheets and patient consent forms."
        ),
        Interaction(
            hcp_id=hcps[2].id,
            date="2026-07-10",
            channel="Phone",
            topics="PediaMelt Iron, Side Effects",
            sentiment="Positive",
            notes="Dr. Taylor reported that pediatric patients are tolerating PediaMelt Iron drops very well due to the strawberry taste. No GI complaints reported. She plans to increase prescribing for minor anemia.",
            follow_up_date="2026-08-01",
            next_step="Call to check stock level in local hospital pharmacy."
        )
    ]
    
    db.add_all(interactions)
    db.commit()
    logger.info("Database seeding completed!")

def create_tables():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
