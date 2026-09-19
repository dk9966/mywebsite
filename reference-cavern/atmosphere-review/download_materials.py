import json, pathlib, subprocess, concurrent.futures
root=pathlib.Path(__file__).resolve().parent.parent
jobs=[]
for f,asset in [('rock-06-files','rock_06'),('metal-files','blue_metal_plate')]:
 j=json.loads((root/'atmosphere-review'/f'{f}.json').read_text())
 for kind in ['Diffuse','Rough','Displacement','nor_gl']:
  url=j[kind]['2k']['jpg']['url'];out=root/'textures'/asset/url.rsplit('/',1)[1]
  jobs.append((url,str(out)))
def download(job):
 url,out=job
 subprocess.run(['curl','-L','--fail','--silent','--max-time','60',url,'-o',out],check=True)
 return pathlib.Path(out).name,pathlib.Path(out).stat().st_size
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:
 for r in e.map(download,jobs):print(r,flush=True)
