from __future__ import annotations
import secrets
from datetime import UTC,datetime
from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Header,HTTPException,status
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.modules.assets.models import AssetRecord,OrganizationRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord,HardwareSnapshotRecord,ComponentObservationRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.incidents.models import IncidentRecord,EndpointHistoryEntryRecord
router=APIRouter(prefix="/admin",tags=["admin"])
def require_admin(token:Annotated[str|None,Header(alias="X-AssetGuard-Admin-Token")]=None)->None:
 if not token or not secrets.compare_digest(token,get_settings().admin_shared_secret):raise HTTPException(401,"Invalid administrator credentials.")
class AssetCreate(BaseModel):
 inventory_number:str=Field(min_length=1,max_length=128);name:str=Field(min_length=1,max_length=255);asset_type:Literal["Desktop","Laptop","Other"];status:str=Field(default="ACTIVE",max_length=32);room:str|None=None;notes:str|None=None
class AssetView(BaseModel):
 id:UUID;inventory_number:str;name:str;asset_type:str;status:str;room:str|None;endpoint_id:UUID|None=None
@router.get("/assets",dependencies=[Depends(require_admin)])
def list_assets(session:Annotated[Session,Depends(get_session)]):
 return [AssetView(id=a.id,inventory_number=a.inventory_number,name=a.name,asset_type=a.asset_type,status=a.status,room=a.room,endpoint_id=session.scalar(select(ManagedEndpointRecord.id).where(ManagedEndpointRecord.asset_id==a.id))) for a in session.scalars(select(AssetRecord).order_by(AssetRecord.inventory_number))]
@router.post("/assets",dependencies=[Depends(require_admin)],status_code=status.HTTP_201_CREATED)
def create_asset(body:AssetCreate,session:Annotated[Session,Depends(get_session)]):
 org=session.scalar(select(OrganizationRecord).order_by(OrganizationRecord.created_at))
 if not org:org=OrganizationRecord(name="Default Organization",created_at=datetime.now(UTC));session.add(org);session.flush()
 if session.scalar(select(AssetRecord).where(AssetRecord.organization_id==org.id,AssetRecord.inventory_number==body.inventory_number)):raise HTTPException(409,"Inventory number already exists.")
 now=datetime.now(UTC);a=AssetRecord(organization_id=org.id,inventory_number=body.inventory_number,name=body.name,asset_type=body.asset_type,status=body.status,room=body.room,notes=body.notes,created_at=now,updated_at=now);session.add(a);session.commit();session.refresh(a);return AssetView(id=a.id,inventory_number=a.inventory_number,name=a.name,asset_type=a.asset_type,status=a.status,room=a.room)
@router.post("/endpoints/{endpoint_id}/asset/{asset_id}",dependencies=[Depends(require_admin)])
def link_endpoint(endpoint_id:UUID,asset_id:UUID,session:Annotated[Session,Depends(get_session)]):
 e=session.get(ManagedEndpointRecord,endpoint_id);a=session.get(AssetRecord,asset_id)
 if not e or not a:raise HTTPException(404,"Asset or endpoint was not found.")
 e.asset_id=a.id;e.updated_at=datetime.now(UTC);session.commit();return {"status":"linked"}
@router.get("/assets/{asset_id}",dependencies=[Depends(require_admin)])
def asset_detail(asset_id:UUID,session:Annotated[Session,Depends(get_session)]):
 a=session.get(AssetRecord,asset_id)
 if not a:raise HTTPException(404,"Asset was not found.")
 e=session.scalar(select(ManagedEndpointRecord).where(ManagedEndpointRecord.asset_id==a.id));r={"id":str(a.id),"inventory_number":a.inventory_number,"name":a.name,"endpoint":None,"current_snapshot_id":None,"baseline_snapshot_id":None,"current_hardware":[],"baseline_hardware":[],"changes":[],"incidents":[],"history":[]}
 if not e:return r
 snaps=list(session.scalars(select(HardwareSnapshotRecord).where(HardwareSnapshotRecord.managed_endpoint_id==e.id).order_by(HardwareSnapshotRecord.captured_at.desc())));cur=snaps[0] if snaps else None;b=session.scalar(select(BaselineRecord).where(BaselineRecord.managed_endpoint_id==e.id,BaselineRecord.status=="ACTIVE"));bs=session.get(HardwareSnapshotRecord,b.hardware_snapshot_id) if b else None
 def comps(s):return [] if not s else [{"type":x.component_type,"model":x.model,"serial":x.serial_number,"capacity":x.capacity,"slot":x.slot,"confidence":x.confidence} for x in session.scalars(select(ComponentObservationRecord).where(ComponentObservationRecord.hardware_snapshot_id==s.id))]
 r.update({"endpoint":{"id":str(e.id),"hostname":e.hostname,"status":e.status},"current_snapshot_id":str(cur.id) if cur else None,"baseline_snapshot_id":str(bs.id) if bs else None,"current_hardware":comps(cur),"baseline_hardware":comps(bs),"changes":[{"id":str(x.id),"type":x.event_type,"component_type":x.component_type,"confidence":x.confidence,"evidence":x.evidence} for x in session.scalars(select(ChangeEventRecord).where(ChangeEventRecord.managed_endpoint_id==e.id))],"incidents":[{"id":str(x.id),"title":x.title,"status":x.status,"severity":x.severity} for x in session.scalars(select(IncidentRecord).where(IncidentRecord.managed_endpoint_id==e.id))],"history":[{"type":x.event_type,"occurred_at":x.occurred_at,"message":x.message} for x in session.scalars(select(EndpointHistoryEntryRecord).where(EndpointHistoryEntryRecord.managed_endpoint_id==e.id).order_by(EndpointHistoryEntryRecord.occurred_at.desc()))]});return r
