from typing import Optional, List
from pydantic import BaseModel


class JobParameter(BaseModel):
    name: str
    value: str
    type: str  # string, integer, float, boolean


class JobMetadata(BaseModel):
    status: str  # Unknown, Scheduled, Running, Completed, Failed, Error, Canceled
    count: int
    maxDurationInSeconds: Optional[float] = None
    avgDurationInSeconds: Optional[float] = None


class JobTargetConfig(BaseModel):
    targetType: str  # Workspace, Cluster, VirtualWorkspace
    targetID: str
    resumeTarget: bool
    databaseName: Optional[str] = None


class JobSchedule(BaseModel):
    mode: str  # Recurring, Once
    startAt: Optional[str] = None  # ISO datetime
    executionIntervalInMinutes: Optional[int] = None


class JobExecutionConfig(BaseModel):
    notebookPath: str
    createSnapshot: bool
    runtimeName: Optional[str] = None


class JobCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[List[JobParameter]] = None
    executionConfig: JobExecutionConfig
    schedule: JobSchedule
    targetConfig: Optional[JobTargetConfig] = None


class Job(BaseModel):
    jobID: str
    name: Optional[str] = None
    description: Optional[str] = None
    targetConfig: Optional[JobTargetConfig] = None
    executionConfig: JobExecutionConfig
    schedule: JobSchedule
    enqueuedBy: str
    createdAt: str
    terminatedAt: Optional[str] = None
    completedExecutionsCount: int
    jobMetadata: List[JobMetadata]
