from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3, secrets, time

ROOT=Path(__file__).resolve().parent
DB=ROOT/'nebula.db'
app=FastAPI(title='NebulaXBlood Core', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, role TEXT DEFAULT 'customer', created_at INTEGER);
    CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY, name TEXT UNIQUE, kind TEXT, ram_mb INTEGER, cpu_percent INTEGER, disk_mb INTEGER, price_minor INTEGER, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS nodes(id INTEGER PRIMARY KEY, name TEXT UNIQUE, address TEXT, status TEXT DEFAULT 'offline', kind TEXT DEFAULT 'game', created_at INTEGER);
    CREATE TABLE IF NOT EXISTS servers(id INTEGER PRIMARY KEY, name TEXT, kind TEXT, user_id INTEGER, plan_id INTEGER, node_id INTEGER, status TEXT DEFAULT 'provisioning', external_id TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, plan_id INTEGER, status TEXT DEFAULT 'pending', payment_ref TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    '''); c.commit(); c.close()
init()
class User(BaseModel): email:str; role:str='customer'
class Plan(BaseModel): name:str; kind:str='game'; ram_mb:int=1024; cpu_percent:int=100; disk_mb:int=10240; price_minor:int=0; active:bool=True
class Node(BaseModel): name:str; address:str; kind:str='game'
class Provision(BaseModel): name:str; kind:str='game'; user_id:int; plan_id:int; node_id:int|None=None
class Order(BaseModel): user_id:int; plan_id:int; payment_ref:str='demo-paid'

@app.get('/api/health')
def health(): return {'ok':True,'service':'nebula-core','time':int(time.time())}
@app.get('/api/plans')
def plans():
    c=db(); rows=c.execute('SELECT * FROM plans WHERE active=1 ORDER BY price_minor').fetchall(); c.close(); return [dict(r) for r in rows]
@app.post('/api/plans')
def create_plan(p:Plan):
    c=db()
    try:
        cur=c.execute('INSERT INTO plans(name,kind,ram_mb,cpu_percent,disk_mb,price_minor,active) VALUES(?,?,?,?,?,?,?)',(p.name,p.kind,p.ram_mb,p.cpu_percent,p.disk_mb,p.price_minor,int(p.active))); c.commit()
    except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Plan already exists')
    row=c.execute('SELECT * FROM plans WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return dict(row)
@app.post('/api/users')
def create_user(u:User):
    c=db()
    try: cur=c.execute('INSERT INTO users(email,role,created_at) VALUES(?,?,?)',(u.email,u.role,int(time.time()))); c.commit()
    except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'User already exists')
    row=c.execute('SELECT * FROM users WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return dict(row)
@app.post('/api/nodes')
def create_node(n:Node):
    c=db()
    try: cur=c.execute('INSERT INTO nodes(name,address,kind,status,created_at) VALUES(?,?,?,?,?)',(n.name,n.address,n.kind,'offline',int(time.time()))); c.commit()
    except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Node already exists')
    row=c.execute('SELECT * FROM nodes WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return dict(row)
@app.get('/api/nodes')
def nodes():
    c=db(); rows=c.execute('SELECT * FROM nodes').fetchall(); c.close(); return [dict(r) for r in rows]
@app.get('/api/servers')
def servers():
    c=db(); rows=c.execute('SELECT s.*,p.name plan_name,n.name node_name FROM servers s LEFT JOIN plans p ON p.id=s.plan_id LEFT JOIN nodes n ON n.id=s.node_id ORDER BY s.id DESC').fetchall(); c.close(); return [dict(r) for r in rows]
@app.post('/api/orders')
def create_order(o:Order):
    c=db(); plan=c.execute('SELECT * FROM plans WHERE id=? AND active=1',(o.plan_id,)).fetchone()
    if not plan: c.close(); raise HTTPException(404,'Plan not found')
    cur=c.execute('INSERT INTO orders(user_id,plan_id,status,payment_ref,created_at) VALUES(?,?,?,?,?)',(o.user_id,o.plan_id,'paid',o.payment_ref,int(time.time()))); c.commit(); oid=cur.lastrowid
    # MVP: immediately create a provisioning record. Real deployment will call the agent queue.
    node=c.execute("SELECT * FROM nodes WHERE kind=? ORDER BY id LIMIT 1",(plan['kind'],)).fetchone()
    cur=c.execute('INSERT INTO servers(name,kind,user_id,plan_id,node_id,status,external_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(f"Nebula-{oid}",plan['kind'],o.user_id,o.plan_id,node['id'] if node else None,'provisioning',secrets.token_hex(8),int(time.time()))); c.commit()
    row=c.execute('SELECT * FROM servers WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return {'order_id':oid,'server':dict(row)}
@app.post('/api/provision')
def provision(p:Provision):
    c=db(); node=p.node_id
    if node is None:
        r=c.execute('SELECT id FROM nodes WHERE kind=? ORDER BY id LIMIT 1',(p.kind,)).fetchone(); node=r['id'] if r else None
    cur=c.execute('INSERT INTO servers(name,kind,user_id,plan_id,node_id,status,external_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(p.name,p.kind,p.user_id,p.plan_id,node,'provisioning',secrets.token_hex(8),int(time.time()))); c.commit(); row=c.execute('SELECT * FROM servers WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return dict(row)
@app.get('/api/settings')
def settings():
    c=db(); rows=c.execute('SELECT key,value FROM settings').fetchall(); c.close(); return {r['key']:r['value'] for r in rows}
@app.put('/api/settings/{key}')
def set_setting(key:str, value:str):
    c=db(); c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value)); c.commit(); c.close(); return {'key':key,'value':value}
