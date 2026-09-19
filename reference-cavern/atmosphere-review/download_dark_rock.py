import json,pathlib,subprocess,concurrent.futures
root=pathlib.Path(__file__).resolve().parent.parent
asset="dark_rock";out=root/"textures"/asset;out.mkdir(exist_ok=True)
j=json.loads((root/"atmosphere-review/dark-rock-files.json").read_text())
def download(kind):
 url=j[kind]["2k"]["jpg"]["url"];path=out/url.rsplit("/",1)[1]
 subprocess.run(["curl","-L","--fail","--silent","--max-time","60",url,"-o",str(path)],check=True)
 return path.name,path.stat().st_size
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:
 for r in e.map(download,["Diffuse","Rough","Displacement","nor_gl"]):print(r,flush=True)
