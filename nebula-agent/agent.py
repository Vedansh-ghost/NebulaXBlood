import os, time, socket, json, urllib.request
HOST=os.getenv('NEBULA_CORE','http://127.0.0.1:8000')
NODE=os.getenv('NEBULA_NODE_NAME',socket.gethostname())
print(f'Nebula Agent {NODE} -> {HOST}')
while True:
    try:
        req=urllib.request.Request(HOST+'/api/health',headers={'X-Nebula-Agent':NODE})
        with urllib.request.urlopen(req,timeout=3) as r: print('core:',json.loads(r.read()))
    except Exception as e: print('core unavailable:',e)
    time.sleep(10)
