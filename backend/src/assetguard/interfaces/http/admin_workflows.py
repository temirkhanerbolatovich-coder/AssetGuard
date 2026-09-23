from __future__ import annotations
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.baselines.service import accept_snapshot_as_baseline
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord, IncidentRecord
from assetguard.modules.incidents.service import decide_incident
from assetguard.modules.snapshots.models import ComponentObservationRecord, HardwareSnapshotRecord

router=APIRouter(prefix="/admin",tags=["admin"],dependencies=[Depends(require_admin)])
class BaselineAccept(BaseModel): reason: str|None=Field(default=None,max_length=2000)
class DecisionBody(BaseModel): classification: str; comment: str|None=None; actor: str=Field(min_length=1,max_length=255)
class ResolveBody(DecisionBody): pass
def missing(): raise HTTPException(status_code=404,detail="Resource was not found.")
@router.get("/endpoints/{endpoint_id}/snapshots")
def snapshots(endpoint_id:UUID,session:Annotated[Session,Depends(get_session)]):
 return [{"id":str(x.id),"captured_at":x.captured_at,"type":x.snapshot_type,"completeness":x.completeness,"normalizer_version":x.normalizer_version} for x in session.scalars(select(HardwareSnapshotRecord).where(HardwareSnapshotRecord.managed_endpoint_id==endpoint_id).order_by(HardwareSnapshotRecord.captured_at.desc()))]
@router.get("/snapshots/{snapshot_id}")
def snapshot(snapshot_id:UUID,session:Annotated[Session,Depends(get_session)]):
 x=session.get(HardwareSnapshotRecord,snapshot_id)
 if not x: missing()
 components=list(session.scalars(select(ComponentObservationRecord).where(ComponentObservationRecord.hardware_snapshot_id==x.id)))
 return {"id":str(x.id),"endpoint_id":str(x.managed_endpoint_id),"captured_at":x.captured_at,"type":x.snapshot_type,"completeness":x.completeness,"components":[{"id":str(c.id),"type":c.component_type,"serial":c.serial_number,"model":c.model,"capacity":c.capacity,"slot":c.slot,"confidence":c.confidence} for c in components]}
@router.get("/endpoints/{endpoint_id}/baseline")
def baseline(endpoint_id:UUID,session:Annotated[Session,Depends(get_session)]):
 x=session.scalar(select(BaselineRecord).where(BaselineRecord.managed_endpoint_id==endpoint_id,BaselineRecord.status=="ACTIVE"))
 return None if not x else {"id":str(x.id),"snapshot_id":str(x.hardware_snapshot_id),"accepted_at":x.accepted_at,"reason":x.reason}
@router.post("/snapshots/{snapshot_id}/baseline")
def accept_baseline(snapshot_id:UUID,body:BaselineAccept,session:Annotated[Session,Depends(get_session)]):
 x=session.get(HardwareSnapshotRecord,snapshot_id)
 if not x: missing()
 b=accept_snapshot_as_baseline(session,x,body.reason); return {"id":str(b.id),"status":b.status,"snapshot_id":str(b.hardware_snapshot_id)}
@router.get("/changes")
def changes(session:Annotated[Session,Depends(get_session)],endpoint_id:UUID|None=None):
 q=select(ChangeEventRecord).order_by(ChangeEventRecord.detected_at.desc())
 if endpoint_id: q=q.where(ChangeEventRecord.managed_endpoint_id==endpoint_id)
 return [{"id":str(x.id),"endpoint_id":str(x.managed_endpoint_id),"type":x.event_type,"component_type":x.component_type,"confidence":x.confidence,"severity":x.severity,"status":x.status,"evidence":x.evidence,"detected_at":x.detected_at} for x in session.scalars(q)]
@router.get("/changes/{change_id}")
def change(change_id:UUID,session:Annotated[Session,Depends(get_session)]):
 x=session.get(ChangeEventRecord,change_id)
 if not x: missing()
 return {"id":str(x.id),"type":x.event_type,"component_type":x.component_type,"evidence":x.evidence,"baseline_snapshot_id":str(x.baseline_snapshot_id),"current_snapshot_id":str(x.current_snapshot_id)}
@router.get("/incidents")
def incidents(session:Annotated[Session,Depends(get_session)],endpoint_id:UUID|None=None):
 q=select(IncidentRecord).order_by(IncidentRecord.created_at.desc())
 if endpoint_id: q=q.where(IncidentRecord.managed_endpoint_id==endpoint_id)
 return [{"id":str(x.id),"endpoint_id":str(x.managed_endpoint_id),"change_event_id":str(x.change_event_id),"status":x.status,"severity":x.severity,"title":x.title,"created_at":x.created_at} for x in session.scalars(q)]
@router.get("/incidents/{incident_id}")
def incident(incident_id:UUID,session:Annotated[Session,Depends(get_session)]):
 x=session.get(IncidentRecord,incident_id)
 if not x: missing()
 return {"id":str(x.id),"status":x.status,"severity":x.severity,"title":x.title,"description":x.description,"change_event_id":str(x.change_event_id),"resolved_at":x.resolved_at}
@router.post("/incidents/{incident_id}/decision")
def decision(incident_id:UUID,body:DecisionBody,session:Annotated[Session,Depends(get_session)]):
 x=session.get(IncidentRecord,incident_id)
 if not x: missing()
 d=decide_incident(session,x,body.classification,body.actor,body.comment,False); return {"id":str(d.id),"incident_status":x.status}
@router.post("/incidents/{incident_id}/resolve")
def resolve(incident_id:UUID,body:ResolveBody,session:Annotated[Session,Depends(get_session)]):
 x=session.get(IncidentRecord,incident_id)
 if not x: missing()
 d=decide_incident(session,x,body.classification,body.actor,body.comment,True); return {"id":str(d.id),"incident_status":x.status}
@router.get("/endpoints/{endpoint_id}/history")
def history(endpoint_id:UUID,session:Annotated[Session,Depends(get_session)]):
 return [{"id":str(x.id),"type":x.event_type,"occurred_at":x.occurred_at,"entity_type":x.related_entity_type,"entity_id":str(x.related_entity_id),"message":x.message,"metadata":x.metadata_json} for x in session.scalars(select(EndpointHistoryEntryRecord).where(EndpointHistoryEntryRecord.managed_endpoint_id==endpoint_id).order_by(EndpointHistoryEntryRecord.occurred_at.desc()))]
