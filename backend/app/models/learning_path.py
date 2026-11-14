"""Adaptive Learning Path and Activity Sequence Data Models.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class LearningPath(db.Model):
    """Personalized curriculum path organizing activities into an adaptive sequential progression."""

    __tablename__ = "learning_paths"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_topic = db.Column(db.String(255), nullable=False, index=True)
    related_document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    related_summary_id = db.Column(
        db.Integer, db.ForeignKey("summaries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status = db.Column(
        db.String(30), default="not_started", nullable=False
    )  # not_started, in_progress, completed, paused
    progress_percentage = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="learning_paths")
    document = db.relationship("Document")
    summary = db.relationship("Summary")
    activities = db.relationship(
        "LearningPathActivity",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="LearningPathActivity.sequence_number",
    )

    def calculate_progress(self) -> float:
        """Calculates dynamic completion percentage based on child activities."""
        acts = self.activities.all()
        if not acts:
            self.progress_percentage = 0.0
            return 0.0
        completed = sum(1 for a in acts if a.status == "completed")
        self.progress_percentage = round((completed / len(acts)) * 100.0, 1)
        if self.progress_percentage >= 100.0:
            self.status = "completed"
        elif completed > 0 and self.status == "not_started":
            self.status = "in_progress"
        return self.progress_percentage

    def to_dict(self, include_activities: bool = True) -> dict:
        """Serializes learning path into dictionary format."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "target_topic": self.target_topic,
            "related_document_id": self.related_document_id,
            "related_summary_id": self.related_summary_id,
            "status": self.status,
            "progress_percentage": round(self.progress_percentage, 1),
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }
        if include_activities:
            data["activities"] = [a.to_dict() for a in self.activities.all()]
        return data

    def __repr__(self):
        return f"<LearningPath id={self.id} user={self.user_id} topic='{self.target_topic}' progress={self.progress_percentage}%>"


class LearningPathActivity(db.Model):
    """Individual milestone activity belonging to an adaptive learning path."""

    __tablename__ = "learning_path_activities"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    learning_path_id = db.Column(
        db.Integer, db.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_type = db.Column(
        db.String(50), nullable=False
    )  # summary_review, takeaways_study, definitions_review, quiz_practice
    activity_title = db.Column(db.String(255), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)  # summary_id or quiz_id
    sequence_number = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(
        db.String(30), default="pending", nullable=False
    )  # pending, in_progress, completed
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    learning_path = db.relationship("LearningPath", back_populates="activities")

    def to_dict(self) -> dict:
        """Serializes activity details."""
        return {
            "id": self.id,
            "learning_path_id": self.learning_path_id,
            "activity_type": self.activity_type,
            "activity_title": self.activity_title,
            "resource_id": self.resource_id,
            "sequence_number": self.sequence_number,
            "status": self.status,
            "completed_at": to_utc_iso(self.completed_at),
        }

    def __repr__(self):
        return f"<LearningPathActivity id={self.id} path_id={self.learning_path_id} seq={self.sequence_number} status='{self.status}'>"

