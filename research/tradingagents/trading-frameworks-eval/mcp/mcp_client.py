import json, subprocess, sys
exe, d = sys.argv[1], sys.argv[2]
p = subprocess.Popen(exe.split() + ["-d", d], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open("mcp_stderr.log","w"), text=True)
def rpc(i, method, params=None):
    msg = {"jsonrpc":"2.0","id":i,"method":method}
    if params is not None: msg["params"]=params
    p.stdin.write(json.dumps(msg)+"\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
out = {}
out["initialize"] = rpc(1,"initialize",{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"eval","version":"0"}})
p.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"})+"\n"); p.stdin.flush()
tl = rpc(2,"tools/list",{})
out["tools"] = [(t["name"], t.get("description","")[:120]) for t in tl["result"]["tools"]]
for i,(name,args) in enumerate([("list_strategies",{}),("get_symbol_breakdown",None),("get_stop_loss_take_profit_activity",None)],3):
    if args is None:
        args = {"strategy_id": sys.argv[3] if len(sys.argv)>3 else ""}
    r = rpc(i,"tools/call",{"name":name,"arguments":args})
    out[name] = r.get("result", r.get("error"))
p.stdin.close(); p.terminate()
json.dump(out, open("mcp_session.json","w"), indent=1, default=str)
print("tools:", len(out["tools"]))
for k in ["list_strategies","get_symbol_breakdown","get_stop_loss_take_profit_activity"]:
    print("==",k, json.dumps(out[k])[:1500])
