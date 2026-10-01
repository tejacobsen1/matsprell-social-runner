"""Standalone Matsprell image-animation worker. No credentials belong in this file."""
import os,json,tempfile,urllib.request,urllib.parse,subprocess,time,argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import imageio_ffmpeg

def render(job,image_path,font_path,out):
 movie=job['kind']=='reel';w,h=1080,1920 if movie else 1350
 image=Image.open(image_path).convert('RGB');image=ImageOps.fit(image,(w,h),centering=(.5,.5))
 font=ImageFont.truetype(str(font_path),58);brandfont=ImageFont.truetype(str(font_path),44);smallfont=ImageFont.truetype(str(font_path),34)
 overlay=Image.new('RGBA',(w,h),(0,0,0,0));draw=ImageDraw.Draw(overlay)
 title=job['title'];lines=[];current=''
 for word in title.split():
  trial=(current+' '+word).strip()
  if draw.textlength(trial,font=font)>860 and current:lines.append(current);current=word
  else:current=trial
 if current:lines.append(current)
 # Fit actual recipe titles; no cut-off text.
 while len(lines)>4:
  font=ImageFont.truetype(str(font_path),font.size-4);lines=[];current=''
  for word in title.split():
   trial=(current+' '+word).strip()
   if draw.textlength(trial,font=font)>860 and current:lines.append(current);current=word
   else:current=trial
  if current:lines.append(current)
 lineheight=int(font.size*1.22);boxheight=len(lines)*lineheight+54;y=int(h*.72)-boxheight//2
 draw.rounded_rectangle((75,y,1005,y+boxheight),radius=24,fill=(41,19,47,240))
 for i,line in enumerate(lines):draw.text((105,y+22+i*lineheight),line,font=font,fill='#ffea96')
 draw.text((105,y+boxheight+20),'Oppskrift via lenken i bio' if movie else 'Kjente favoritter. Nye sprell.',font=smallfont,fill='white',stroke_width=2,stroke_fill='#29132f')
 draw.rounded_rectangle((75,int(h*.10),355,int(h*.10)+74),radius=20,fill=(41,19,47,220));draw.text((97,int(h*.10)+8),'matsprell',font=brandfont,fill='#d0ff65')
 if not movie:Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB').save(out,quality=94);return
 base=Path(out).parent/'base.jpg';over=Path(out).parent/'overlay.png';image.save(base,quality=96);overlay.save(over)
 # Slow food close-up, intact ingredients, readable title throughout; 9-second vertical H.264.
 ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
 filters="[0:v]scale=2160:3840,zoompan=z='1.04+0.12*on/269':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=270:s=1080x1920:fps=30[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
 subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(base),'-loop','1','-i',str(over),'-filter_complex',filters,'-map','[v]','-t','9','-r','30','-c:v','libx264','-preset','veryfast','-crf','23','-movflags','+faststart',str(out)],check=True,timeout=180)

def run():
 origin=os.environ['MATSPRELL_ORIGIN'].rstrip('/');token=os.environ['SOCIAL_RUNNER_TOKEN'];assert origin.startswith('https://') and len(token)>=32
 def request(path,method='POST',body=b'',extra=None):
  req=urllib.request.Request(origin+path,data=body,method=method,headers={'Authorization':'Bearer '+token,**(extra or {})})
  with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
 request('/api/social/tick')
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for _ in range(4):
   data=request('/api/social/render');job=data.get('job')
   if not job:break
   # Only media hosted by Matsprell is accepted; credentials never accompany asset requests.
   for url in (job['image'],job['font']):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ['www.matsprell.no','matsprell.no']:raise RuntimeError('Unexpected source host')
   image=td/'image';font=td/'font.ttf';urllib.request.urlretrieve(job['image'],image);urllib.request.urlretrieve(job['font'],font)
   output=td/('output.mp4' if job['kind']=='reel' else 'output.jpg');render(job,image,font,output)
   request('/api/social/render','PUT',output.read_bytes(),{'X-Render-ID':job['id'],'Content-Type':'video/mp4' if job['kind']=='reel' else 'image/jpeg'})
 for _ in range(4):
  request('/api/social/tick');time.sleep(4)
 print('Matsprell check completed. See admin for per-channel status.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sample-image');p.add_argument('--sample-font');p.add_argument('--sample-output');args=p.parse_args()
 if args.sample_image:render({'kind':'reel','title':'Tandoori i pita'},args.sample_image,args.sample_font,args.sample_output)
 else:run()
