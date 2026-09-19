import json,pathlib,subprocess,concurrent.futures
root=pathlib.Path(__file__).resolve().parent.parent
asset='rock_face_01';out=root/'assets'/asset;out.mkdir(exist_ok=True,parents=True)
j=json.loads((root/'atmosphere-review/rock-face-files.json').read_text())['gltf']['2k']['gltf']
jobs=[(j['url'],out/'rock_face_01_2k.gltf')]+[(v['url'],out/k) for k,v in j['include'].items()]
def download(job):
 url,path=job;path.parent.mkdir(exist_ok=True,parents=True)
 subprocess.run(['curl','-L','--fail','--silent','--max-time','60',url,'-o',str(path)],check=True)
 return path.name,path.stat().st_size
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:
 for r in e.map(download,jobs):print(r,flush=True)
