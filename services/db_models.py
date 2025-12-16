from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Date, DateTime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Association Table for Many-to-Many Tags
task_tags = Table('task_tags', Base.metadata,
    Column('task_id', String, ForeignKey('tasks.id', ondelete="CASCADE")),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete="CASCADE"))
)

class DBInboxItem(Base):
    __tablename__ = 'inbox_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class DBTag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class DBGoal(Base):
    __tablename__ = 'goals'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default='active')

    projects = relationship("DBProject", back_populates="goal")

class DBProject(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(String, ForeignKey('goals.id', ondelete="SET NULL"))
    name = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default='active')

    goal = relationship("DBGoal", back_populates="projects")
    # Cascade all delete-orphan ensures if Project is deleted, tasks go with it
    tasks = relationship("DBTask", back_populates="project", cascade="all, delete-orphan")
    resources = relationship("DBResource", back_populates="project", cascade="all, delete-orphan")
    reference_items = relationship("DBReferenceItem", back_populates="project", cascade="all, delete-orphan")

class DBTask(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"))
    name = Column(String, nullable=False)
    is_completed = Column(Boolean, default=False)
    deadline = Column(Date, nullable=True)
    duration = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    project = relationship("DBProject", back_populates="tasks")
    tags = relationship("DBTag", secondary=task_tags)

class DBResource(Base):
    __tablename__ = 'project_resources'
    id = Column(String, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    store = Column(String, default='General')
    is_acquired = Column(Boolean, default=False)
    link = Column(String, nullable=True)

    project = relationship("DBProject", back_populates="resources")

class DBReferenceItem(Base):
    __tablename__ = 'reference_items'
    id = Column(String, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"))
    name = Column(String, nullable=False)
    description = Column(String)

    project = relationship("DBProject", back_populates="reference_items")