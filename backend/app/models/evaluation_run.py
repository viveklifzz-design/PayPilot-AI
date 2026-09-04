from sqlalchemy import Column, String, Integer, Numeric, DateTime, JSON
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_name = Column(String(255), nullable=False)
    seed = Column(Integer, nullable=False, default=42)
    batch_size = Column(Integer, nullable=False, default=100)
    mode = Column(String(50), nullable=False, default="simulation")
    
    total_cases = Column(Integer, nullable=False)
    revenue_at_risk = Column(Numeric(12, 2), nullable=False)
    recoverable_revenue = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_recovered = Column(Numeric(12, 2), nullable=False, default=0.0)
    
    diagnosed_count = Column(Integer, nullable=False, default=0)
    policy_allowed_count = Column(Integer, nullable=False, default=0)
    policy_blocked_count = Column(Integer, nullable=False, default=0)
    escalated_count = Column(Integer, nullable=False, default=0)
    recovery_attempt_count = Column(Integer, nullable=False, default=0)
    recovered_count = Column(Integer, nullable=False, default=0)
    failed_recovery_count = Column(Integer, nullable=False, default=0)
    stopped_count = Column(Integer, nullable=False, default=0)
    remaining_revenue_at_risk = Column(Numeric(12, 2), nullable=False, default=0.0)

    recovery_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    recovery_success_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    precision_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    false_intervention_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    escalation_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    safe_stop_rate = Column(Numeric(5, 2), nullable=False, default=0.0)

    metrics = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
