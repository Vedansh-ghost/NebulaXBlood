import hashlib, hmac, json, os, secrets, subprocess, time
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'nebula.db'}")
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False)
    role = Column(String(32), default="customer", nullable=False)
    password_hash = Column(String(128), nullable=True)
    created_at = Column(Integer, nullable=False)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    kind = Column(String(16), default="game", nullable=False)
    ram_mb = Column(Integer, default=1024)
    cpu_percent = Column(Integer, default=100)
    disk_mb = Column(Integer, default=10240)
    price_minor = Column(Integer, default=0)
    image = Column(String(255), default="itzg/minecraft-server")
    active = Column(Boolean, default=True)

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    kind = Column(String(16), default="game", nullable=False)
    agent_token_hash = Column(String(128), nullable=False)
    status = Column(String(32), default="offline")
    enabled = Column(Boolean, default=True, nullable=False)
    price_per_gb_minor = Column(Integer, default=3000, nullable=False)
    maintenance_message = Column(String(500), nullable=True)
    maintenance_until = Column(Integer, nullable=True)
    capacity_gb = Column(Integer, default=0, nullable=False)
    last_seen = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False)

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    price_per_gb_minor: Optional[int] = Field(None, ge=0)
    enabled: Optional[bool] = None
    status: Optional[str] = None
    maintenance_message: Optional[str] = None
    maintenance_until: Optional[int] = None
    capacity_gb: Optional[int] = Field(None, ge=0)

class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    kind = Column(String(16), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=True)
    status = Column(String(32), default="queued")
    external_id = Column(String(64), unique=True, nullable=False)
    hostname = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    plan_id = Column(Integer, nullable=False)
    status = Column(String(32), default="pending")
    payment_ref = Column(String(255), nullable=True)
    created_at = Column(Integer, nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    type = Column(String(64), nullable=False)
    server_id = Column(Integer, nullable=True)
    node_id = Column(Integer, nullable=True)
    payload = Column(Text, nullable=False)
    status = Column(String(32), default="queued")
    result = Column(Text, nullable=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(120), primary_key=True)
    value = Column(Text, nullable=False)

Base.metadata.create_all(engine)

def migrate_node_columns():
    # Upgrade existing v2 databases without requiring a destructive reset.
    additions = {
        "enabled": "BOOLEAN DEFAULT TRUE",
        "price_per_gb_minor": "INTEGER DEFAULT 3000",
        "maintenance_message": "VARCHAR(500)",
        "maintenance_until": "INTEGER",
        "capacity_gb": "INTEGER DEFAULT 0",
    }
    from sqlalchemy import inspect
    inspector = inspect(engine)
    try:
        existing = {c["name"] for c in inspector.get_columns("nodes")}
        with engine.begin() as conn:
            for name, typ in additions.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE nodes ADD COLUMN {name} {typ}"))
    except Exception as exc:
        print("node migration deferred:", exc)

migrate_node_columns()

# Bootstrap the local node on first startup when an installer supplied a token.
# This keeps a fresh single-VPS installation self-contained; additional nodes use /api/nodes.
try:
    bootstrap_node = os.getenv("NEBULA_NODE_NAME")
    bootstrap_token = os.getenv("NEBULA_AGENT_TOKEN")
    if bootstrap_node and bootstrap_token:
        with SessionLocal() as s:
            node = s.scalar(select(Node).where(Node.name == bootstrap_node))
            if not node:
                s.add(Node(name=bootstrap_node, address=os.getenv("NEBULA_NODE_ADDRESS", "local"), kind="game", agent_token_hash=token_hash(bootstrap_token), created_at=int(time.time())))
                s.commit()
except Exception as exc:
    print("node bootstrap deferred:", exc)

app = FastAPI(title="NebulaXBlood Core", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db():
    return SessionLocal()

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def require_admin(x_nebula_admin: Optional[str] = Header(default=None)):
    expected = os.getenv("NEBULA_ADMIN_TOKEN")
    if expected and not hmac.compare_digest(x_nebula_admin or "", expected):
        raise HTTPException(401, "Admin authentication required")

def require_agent(x_nebula_agent: Optional[str] = Header(default=None), x_nebula_node: Optional[str] = Header(default=None)) -> Node:
    if not x_nebula_agent or not x_nebula_node:
        raise HTTPException(401, "Agent authentication required")
    with db() as s:
        node = s.scalar(select(Node).where(Node.name == x_nebula_node))
        if not node or not hmac.compare_digest(node.agent_token_hash, token_hash(x_nebula_agent)):
            raise HTTPException(401, "Invalid node credentials")
        node.status = "online"; node.last_seen = int(time.time()); s.commit()
        return node

class UserIn(BaseModel):
    email: str
    role: str = "customer"

class PlanIn(BaseModel):
    name: str
    kind: str = "game"
    ram_mb: int = Field(1024, ge=128)
    cpu_percent: int = Field(100, ge=1)
    disk_mb: int = Field(10240, ge=128)
    price_minor: int = Field(0, ge=0)
    image: str = "itzg/minecraft-server"
    active: bool = True

class NodeIn(BaseModel):
    name: str
    address: str
    kind: str = "game"
    price_per_gb_minor: int = Field(3000, ge=0)
    capacity_gb: int = Field(0, ge=0)

class OrderIn(BaseModel):
    user_id: int
    plan_id: int
    node_id: Optional[int] = None
    ram_gb: Optional[int] = Field(None, ge=1)
    subdomain: Optional[str] = None
    subdomain_price_minor: int = Field(0, ge=0)
    payment_ref: str = "manual-demo"

class ProvisionIn(BaseModel):
    name: str
    kind: str = "game"
    user_id: int
    plan_id: int
    node_id: Optional[int] = None
    hostname: Optional[str] = None

class JobResult(BaseModel):
    status: str
    result: dict = {}

@app.get("/api/health")
def health():
    return {"ok": True, "service": "nebula-core", "version": "2.0.0", "time": int(time.time())}

@app.get("/api/version")
def version(): return {"version": "2.0.0", "release": "Nebula Foundation v2"}

@app.get("/api/plans")
def plans():
    with db() as s:
        rows=[]
        for p in s.scalars(select(Plan).where(Plan.active.is_(True)).order_by(Plan.price_minor)):
            rows.append({k:getattr(p,k) for k in ("id","name","kind","ram_mb","cpu_percent","disk_mb","price_minor","image","active")})
        return rows

@app.post("/api/plans", dependencies=[Depends(require_admin)])
def create_plan(p: PlanIn):
    with db() as s:
        if s.scalar(select(Plan).where(Plan.name == p.name)): raise HTTPException(409, "Plan already exists")
        row = Plan(**p.model_dump()); s.add(row); s.commit(); s.refresh(row)
        return {k:v for k,v in row.__dict__.items() if not k.startswith("_")}

@app.post("/api/users")
def create_user(u: UserIn):
    with db() as s:
        if s.scalar(select(User).where(User.email == u.email)): raise HTTPException(409, "User already exists")
        row = User(email=u.email, role=u.role, created_at=int(time.time())); s.add(row); s.commit(); s.refresh(row)
        return {k:v for k,v in row.__dict__.items() if not k.startswith("_")}

@app.post("/api/nodes", dependencies=[Depends(require_admin)])
def create_node(n: NodeIn):
    token = secrets.token_urlsafe(32)
    with db() as s:
        if s.scalar(select(Node).where(Node.name == n.name)): raise HTTPException(409, "Node already exists")
        row = Node(name=n.name, address=n.address, kind=n.kind, price_per_gb_minor=n.price_per_gb_minor, capacity_gb=n.capacity_gb, agent_token_hash=token_hash(token), created_at=int(time.time()))
        s.add(row); s.commit(); s.refresh(row)
        return {"node": {k:v for k,v in row.__dict__.items() if not k.startswith("_") and k != "agent_token_hash"}, "agent_token": token}

@app.get("/api/nodes", dependencies=[Depends(require_admin)])
def nodes():
    with db() as s:
        return [{k:v for k,v in n.__dict__.items() if not k.startswith("_") and k != "agent_token_hash"} for n in s.scalars(select(Node).order_by(Node.id.desc()))]

@app.patch("/api/nodes/{node_id}", dependencies=[Depends(require_admin)])
def update_node(node_id: int, patch: NodeUpdate):
    with db() as s:
        node=s.get(Node,node_id)
        if not node: raise HTTPException(404,"Node not found")
        data=patch.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != node.name and s.scalar(select(Node).where(Node.name==data["name"])):
            raise HTTPException(409,"Node name already exists")
        for k,v in data.items(): setattr(node,k,v)
        s.commit(); s.refresh(node)
        return {k:v for k,v in node.__dict__.items() if not k.startswith("_") and k != "agent_token_hash"}

@app.post("/api/nodes/{node_id}/maintenance", dependencies=[Depends(require_admin)])
def node_maintenance(node_id: int, message: str = "Scheduled maintenance", until: Optional[int] = None):
    with db() as s:
        node=s.get(Node,node_id)
        if not node: raise HTTPException(404,"Node not found")
        node.status="maintenance"; node.maintenance_message=message; node.maintenance_until=until
        s.commit(); return {"ok":True,"node_id":node_id,"status":node.status,"message":message,"until":until}

@app.delete("/api/nodes/{node_id}/maintenance", dependencies=[Depends(require_admin)])
def clear_node_maintenance(node_id: int):
    with db() as s:
        node=s.get(Node,node_id)
        if not node: raise HTTPException(404,"Node not found")
        node.status="offline" if not node.last_seen else "online"; node.maintenance_message=None; node.maintenance_until=None
        s.commit(); return {"ok":True,"node_id":node_id,"status":node.status}

@app.get("/api/payment/qr")
def payment_qr():
    with db() as s:
        row=s.get(Setting,"payment_qr_url")
        return {"enabled": bool(row and row.value), "url": row.value if row else None}

@app.put("/api/payment/qr", dependencies=[Depends(require_admin)])
def set_payment_qr(value: str):
    if not value.strip(): raise HTTPException(400,"QR URL is required")
    with db() as s:
        row=s.get(Setting,"payment_qr_url")
        if row: row.value=value.strip()
        else: s.add(Setting(key="payment_qr_url",value=value.strip()))
        s.commit(); return {"ok":True,"url":value.strip()}

@app.get("/api/servers")
def servers():
    with db() as s:
        return [{k:v for k,v in x.__dict__.items() if not k.startswith("_")} for x in s.scalars(select(Server).order_by(Server.id.desc()))]

@app.post("/api/orders")
def create_order(o: OrderIn):
    with db() as s:
        plan = s.scalar(select(Plan).where(Plan.id == o.plan_id, Plan.active.is_(True)))
        if not plan: raise HTTPException(404, "Plan not found")
        # Demo/manual payment only. Production gateway webhook should mark orders paid.
        order = Order(user_id=o.user_id, plan_id=o.plan_id, status="paid", payment_ref=o.payment_ref, created_at=int(time.time()))
        s.add(order); s.flush()
        node = None
        if o.node_id:
            node = s.get(Node, o.node_id)
            if not node or node.kind != plan.kind or not node.enabled or node.status == "maintenance":
                raise HTTPException(400, "Selected node is unavailable")
        else:
            node = s.scalar(select(Node).where(Node.kind == plan.kind, Node.status == "online", Node.enabled.is_(True)).order_by(Node.id))
        server = Server(name=f"Nebula-{order.id}", kind=plan.kind, user_id=o.user_id, plan_id=plan.id, node_id=node.id if node else None, status="queued", external_id=secrets.token_hex(8), created_at=int(time.time()))
        s.add(server); s.flush()
        if node:
            job = Job(type="provision_game" if plan.kind == "game" else "provision_vps", server_id=server.id, node_id=node.id, payload=json.dumps({"server_id":server.id,"plan_id":plan.id,"image":plan.image,"ram_mb":plan.ram_mb,"cpu_percent":plan.cpu_percent,"disk_mb":plan.disk_mb,"name":server.name}), created_at=int(time.time()), updated_at=int(time.time()))
            s.add(job)
        s.commit()
        node_price = (o.ram_gb or max(1, plan.ram_mb // 1024)) * (node.price_per_gb_minor if node else 0)
        total_minor = node_price + o.subdomain_price_minor + plan.price_minor
        return {"order_id": order.id, "server_id": server.id, "status": server.status, "job_created": bool(node), "node_id": node.id if node else None, "total_minor": total_minor, "subdomain": o.subdomain}

@app.post("/api/provision", dependencies=[Depends(require_admin)])
def provision(p: ProvisionIn):
    with db() as s:
        plan = s.get(Plan, p.plan_id)
        if not plan: raise HTTPException(404, "Plan not found")
        node = s.get(Node, p.node_id) if p.node_id else s.scalar(select(Node).where(Node.kind == p.kind).order_by(Node.id))
        server = Server(name=p.name, kind=p.kind, user_id=p.user_id, plan_id=p.plan_id, node_id=node.id if node else None, status="queued", external_id=secrets.token_hex(8), hostname=p.hostname, created_at=int(time.time()))
        s.add(server); s.flush()
        if node:
            s.add(Job(type="provision_game" if p.kind == "game" else "provision_vps", server_id=server.id, node_id=node.id, payload=json.dumps({"server_id":server.id,"plan_id":p.plan_id,"image":plan.image,"ram_mb":plan.ram_mb,"cpu_percent":plan.cpu_percent,"disk_mb":plan.disk_mb,"name":server.name}), created_at=int(time.time()), updated_at=int(time.time())))
        s.commit(); return {"server_id":server.id,"status":server.status,"node_id":server.node_id}

@app.get("/api/agent/jobs")
def agent_jobs(node: Node = Depends(require_agent)):
    with db() as s:
        job = s.scalar(select(Job).where(Job.node_id == node.id, Job.status == "queued").order_by(Job.id).limit(1))
        if not job: return {"job": None}
        job.status="running"; job.updated_at=int(time.time()); s.commit()
        return {"job": {"id":job.id,"type":job.type,"server_id":job.server_id,"payload":json.loads(job.payload)}}

@app.post("/api/agent/jobs/{job_id}/result")
def agent_job_result(job_id: int, data: JobResult, node: Node = Depends(require_agent)):
    with db() as s:
        job=s.get(Job,job_id)
        if not job or job.node_id != node.id: raise HTTPException(404,"Job not found")
        job.status=data.status; job.result=json.dumps(data.result); job.updated_at=int(time.time())
        if job.server_id:
            server=s.get(Server,job.server_id); server.status="running" if data.status == "completed" else "error"
            if isinstance(data.result,dict):
                if data.result.get("hostname"): server.hostname=data.result["hostname"]
                if data.result.get("port"): server.port=int(data.result["port"])
        s.commit(); return {"ok":True}

@app.post("/api/agent/heartbeat")
def heartbeat(node: Node = Depends(require_agent)):
    return {"ok":True,"node":node.name,"status":"online","time":int(time.time())}

@app.post("/api/payments/webhook")
async def payment_webhook(request: Request):
    body = await request.body()
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Nebula-Signature", "")
    if secret and not hmac.compare_digest(signature, hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()):
        raise HTTPException(401, "Invalid webhook signature")
    data = json.loads(body or b"{}")
    order_id = int(data.get("order_id", 0)); status = data.get("status", "")
    with db() as s:
        order=s.get(Order,order_id)
        if not order: raise HTTPException(404,"Order not found")
        order.status = "paid" if status in {"paid","success","completed"} else status
        s.commit()
    return {"ok":True,"order_id":order_id,"status":status}

@app.get("/api/settings")
def settings():
    with db() as s: return {x.key:x.value for x in s.scalars(select(Setting))}

@app.put("/api/settings/{key}", dependencies=[Depends(require_admin)])
def set_setting(key: str, value: str):
    with db() as s:
        row=s.get(Setting,key)
        if row: row.value=value
        else: s.add(Setting(key=key,value=value))
        s.commit(); return {"key":key,"value":value}
