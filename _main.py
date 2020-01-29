import main
import json
from aiohttp import web
from multiprocessing import Process,Pipe
import datetime
import os

routes = web.RouteTableDef()

def fold(x):
    DATA_FOLDER = "data/articles"
    return DATA_FOLDER+"/"+x+".json"

@routes.post('/kdb/add')
async def add(req,_id = 0):
    req = await req.json()
    req = req["data"]
    if _id == 0:
        req["id"] = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    else:
        req["id"] = _id
    try :
        os.mkdir("data/articles") 
    except FileExistsError:
        pass
    Process(target=main.create_text_matrix,args=((req["tags"],req["brief"],req["content"]),req["title"]+"_"+str(req["id"]))).start()
    main._upd_global(req["title"]+"_"+str(req["id"]))
    with open(fold(req["title"]+"_"+str(req["id"])),'w',encoding='utf-8') as f:
        json.dump(req,f)
    if _id == 0:
        return web.json_response({"error":"no"})
    

@routes.post('/kdb/change')
async def change(reqw):
    req = await reqw.json()
    req = req["data"]
    await delete(reqw)
    await add(reqw,req["id"])
    return web.json_response({"error":"no"})
    

@routes.post('/kdb/delete')
async def delete(req):
    req = await req.json()
    req = req["data"]
    try:
        os.remove(fold(main._global()["d"][req["id"]]))
    except KeyError:
        return web.json_response({"error":"no such id"})
    except FileNotFoundError:
        return web.json_response({"error":"no such id"})
    if main.delete_ind(req["id"]) != 0:
        return web.json_response({"error":"no such id"})
    return web.json_response({"error":"no"})
    

@routes.post('/kdb/count')
async def count(req):
    return web.json_response({"number":len(main._global()["l"]),"error":"no"})
    
@routes.post('/kdb/get')
async def get(req):
    #
    #CHECK AUTHORITY
    #
    req = await req.json()
    req = req["data"]
    try:
        with open(fold(main._global()["d"][req["id"]]),'r') as f:
            ans = json.load(f)
    except FileNotFoundError:
        return ({'json':{},"error":"no such file"})
    except KeyError:
        return ({'json':{},"error":"no such file"})
    return web.json_response({"json":ans,"error":"no"})

@routes.post('/kdb/gets')
async def gets(req):
    req = await req.json()
    req = req["data"]
    ans =  []
    artic_lis = main._global()["l"]
    for u in range(req["page"]*req["pageSize"],req["page"]*req["pageSize"]+req["pageSize"]):
        if (u<len(artic_lis)):
            with open(fold(artic_lis[u]),'r') as f:
                st = json.load(f)
                #AUTHORITY
                ans.append(st)
                
    return web.json_response({"articles":ans,"error":"no"})

@routes.post('/kdb/search')
async def search(req):
    req = await req.json()
    req = req["data"]
    pi = Pipe()
    proc = Process(target=main.get_article,args=(req["string"],pi[1]))
    proc.start()
    proc.join()
    ans = pi[0].recv()
    pi[0].close()
    if type(ans) == type(int):
        return web.json_response({"article":{},"error":"not found"})
    try:
        res =  []
        for u in range(req["page"]*req["pageSize"],req["page"]*req["pageSize"]+req["pageSize"]):
            if (u<len(ans)):
                with open(fold(ans[u]),'r') as f:
                    st = json.load(f)
                    #AUTHORITY
                    res.append(st)
        return web.json_response({"data":res,"error":"no"})
    except FileNotFoundError:
        return web.json_response({"article":{},"error":"not found"})
    except KeyError:
        return web.json_response({"article":{},"error":"not found"})

@routes.post('/kdb/csearch')
async def search(req):
    req = await req.json()
    req = req["data"]
    pi = Pipe()
    proc = Process(target=main.get_article,args=(req["string"],pi[1]))
    proc.start()
    proc.join()
    ans = pi[0].recv()
    pi[0].close()
    if type(ans) == type(int):
        return web.json_response({"article":{},"error":"not found"})
    return  web.json_response({"number":len(ans),"error":"no"})
    
@routes.post('/kdb/check')
async def check(req):
    req = await req.json()
    req = req["data"]
    pi = Pipe()
    proc = Process(target=main.get_article,args=(req["title"]+". "+req["body"],pi[1]))
    proc.start()
    proc.join()
    ans = pi[0].recv()
    pi[0].close()
    if type(ans) == type(int):
        return web.json_response({"url":Nan,"error":"not found"})
    url = "helpfesk.innopolis.university/knowledge-base/article/"+ans[0].split("_")[-1]
    return  web.json_response({"url":url,"error":"no"})
    
    
    
app = web.Application()
app.add_routes(routes)
web.run_app(app,port = 8030)
