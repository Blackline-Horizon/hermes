from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, MetaData, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY

# Specify the schema
metadata = MetaData(schema='report')

Base = declarative_base(metadata=metadata)

class Report(Base):
    __tablename__ = "report"

    id = Column(Integer, primary_key=True)
    username = Column(String, index=True)
    title = Column(String, nullable=False)
    date_start = Column(DateTime, nullable = False)
    date_end = Column(DateTime, nullable = False)
    industry = Column(ARRAY(String), nullable = False)
    continents = Column(ARRAY(String), nullable = False)
    devices = Column(ARRAY(String), nullable = False)
    resolutions = Column(ARRAY(String), nullable = False)
    alerts = Column(ARRAY(String), nullable = False)
    pdf_id = Column(Integer, ForeignKey("pdf_files.id"), unique=True)

    pdf = relationship("PDFFile", back_populates="report", cascade="all, delete-orphan", single_parent=True)

class PDFFile(Base):
    __tablename__ = "pdf_files"

    id = Column(Integer, primary_key=True, index=True)
    pdf_data = Column(LargeBinary, nullable=False)

    report = relationship("Report", back_populates="pdf", uselist=False)
