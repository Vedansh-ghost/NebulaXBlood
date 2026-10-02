import json, os, socket, subprocess, time, urllib.request

CORE=os.getenv("NEBULA_CORE","http://127.0.0.1:8000").rstrip("/")
NODE=os.getenv("NEBULA_NODE_NAME",socket.gethostname())
TOKEN=os.getenv("NEBULA_AGENT_TOKEN","")
POLL=float(os.getenv("NEBULA_POLL_SECONDS","3"))


def call(path, method="GET", payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(CORE+path,data=data,method=method,headers={"Content-Type":"application/json","X-Nebula-Agent":TOKEN,"X-Nebula-Node":NODE})
    with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read())

def provision_game(job):
    p=job["payload"]; server_id=p["server_id"]; plan_id=p["plan_id"]
    # Core currently returns plan metadata through a future endpoint; use safe defaults for v2 game foundation.
    name=f"nebula-{server_id}"
    image=p.get("image") or os.getenv("NEBULA_DEFAULT_GAME_IMAGE","itzg/minecraft-server")
    memory=f"{int(p.get("ram_mb") or 1024)}m"
    cpus=max(0.1, float(p.get("cpu_percent") or 100)/100)
    volume=f"nebula-server-{server_id}"
    subprocess.run(["docker","volume","create",volume],check=True,capture_output=True)
    subprocess.run(["docker","rm","-f",name],check=False,capture_output=True)
    subprocess.run(["docker","run","-d","--name",name,"--restart","unless-stopped","--memory",memory,"--cpus",str(cpus),"-e","EULA=TRUE","-v",f"{volume}:/data","-p","0:25565",image],check=True,capture_output=True)
    port=subprocess.check_output(["docker","port",name,"25565/tcp"],text=True).strip().rsplit(":",1)[-1]
    return {"container":name,"port":int(port),"hostname":os.getenv("NEBULA_SERVER_DOMAIN","") or None}

def provision_vps(job):
    # v2 defines the job contract; actual VM creation is intentionally delegated to a future libvirt adapter.
    return {"adapter":"vps","status":"queued-for-virtualization-adapter"}

print(f"Nebula Agent 2.0 | node={NODE} | core={CORE}")
while True:
    try:
        call("/api/agent/heartbeat", "POST")
        response=call("/api/agent/jobs")
        job=response.get("job")
        if job:
            try:
                result=provision_game(job) if job["type"]=="provision_game" else provision_vps(job)
                call(f"/api/agent/jobs/{job['id']}/result","POST",{"status":"completed","result":result})
            except Exception as e:
                call(f"/api/agent/jobs/{job['id']}/result","POST",{"status":"failed","result":{"error":str(e)}})
    except Exception as e:
        print("agent error:",e,flush=True)
    time.sleep(POLL)
