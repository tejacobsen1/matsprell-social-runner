"""Standalone Matsprell image-animation worker. No credentials belong in this file."""
import os,json,tempfile,urllib.request,urllib.parse,subprocess,time,argparse,math,random,wave,array
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import imageio_ffmpeg

def music_bed(path,duration=9):
 # Original procedural music: no third-party recordings, royalties or API calls.
 rate=44100; samples=[0.0]*int(rate*duration); beat=60/112; rng=random.Random(731)
 def tone(start,midi,length,gain,pluck=True):
  freq=440*2**((midi-69)/12)
  for i in range(min(int(length*rate),len(samples)-int(start*rate))):
   t=i/rate; envelope=min(1,t/.008)*math.exp(-t*(5 if pluck else 2))
   samples[int(start*rate)+i]+=gain*envelope*(math.sin(2*math.pi*freq*t)+.18*math.sin(4*math.pi*freq*t))
 # Bright marimba-style motif, warm bass, restrained percussion.
 melody=[76,79,83,79,74,77,81,77,72,76,79,76,74,79,83,79]
 bass=[45,41,48,43]
 for b in range(int(duration/beat)+1):
  start=b*beat;tone(start,melody[b%16],.42,.10)
  if b%2==0:tone(start,bass[(b//4)%4],.8,.12,False)
  for j in range(int(.10*rate)):
   idx=int(start*rate)+j
   if idx>=len(samples):break
   t=j/rate
   samples[idx]+=.08*math.sin(2*math.pi*(65*t+18*(1-math.exp(-t*35))/35))*math.exp(-t*32)
  for off in (0,beat/2):
   for j in range(int(.04*rate)):
    idx=int((start+off)*rate)+j
    if idx>=len(samples):break
    samples[idx]+=.015*rng.uniform(-1,1)*math.exp(-j/rate*95)
 peak=max(abs(v) for v in samples) or 1
 pcm=array.array('h',(int(32767*.42*v/peak*min(1,i/rate/.12,(duration-i/rate)/.55)) for i,v in enumerate(samples)))
 if __import__('sys').byteorder!='little':pcm.byteswap()
 with wave.open(str(path),'wb') as out:
  out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm.tobytes())


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
 base=Path(out).parent/'base.jpg';over=Path(out).parent/'overlay.png';ending=Path(out).parent/'promo.png';music=Path(out).parent/'music.wav'
 image.save(base,quality=96);overlay.save(over)
 # Last two seconds: branded promotion, centrally placed inside Reel safe areas.
 promo=Image.new('RGBA',(w,h),(41,19,47,0));d=ImageDraw.Draw(promo)
 d.rectangle((0,0,w,h),fill=(41,19,47,182))
 d.rounded_rectangle((80,650,1000,1280),radius=42,fill=(41,19,47,248),outline=(195,145,218,230),width=3)
 def centered(text,y,size,color):
  f=ImageFont.truetype(str(font_path),size);d.text(((w-d.textlength(text,font=f))/2,y),text,font=f,fill=color)
 centered('matsprell',710,98,'#ffea96')
 centered('Kjente favoritter',850,48,'white');centered('Nye sprell',917,48,'white')
 d.rounded_rectangle((150,1040,930,1165),radius=30,fill='#d0ff65')
 centered('matsprell.no',1058,72,'#29132f');centered('Gratis oppskrifter',1200,36,'white')
 promo.save(ending);music_bed(music)
 ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
 filters="[0:v]scale=2160:3840,zoompan=z='1.04+0.12*on/269':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=270:s=1080x1920:fps=30[bg];[bg][1:v]overlay=0:0:shortest=1[food];[food][2:v]overlay=0:0:enable='gte(t,7)',format=yuv420p[v]"
 subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(base),'-loop','1','-i',str(over),'-loop','1','-i',str(ending),'-i',str(music),'-filter_complex',filters,'-map','[v]','-map','3:a','-t','9','-r','30','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','128k','-ar','44100','-ac','2','-movflags','+faststart',str(out)],check=True,timeout=180)

def run():
 origin=os.environ['MATSPRELL_ORIGIN'].rstrip('/');token=os.environ['SOCIAL_RUNNER_TOKEN'];assert origin.startswith('https://') and len(token)>=32
 agent={'User-Agent':'MatsprellSocialRunner/1.0 (+https://www.matsprell.no)'}
 def request(path,method='POST',body=b'',extra=None):
  req=urllib.request.Request(origin+path,data=body,method=method,headers={**agent,'Authorization':'Bearer '+token,**(extra or {})})
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
   image=td/'image';font=td/'font.ttf'
   for url,target in [(job['image'],image),(job['font'],font)]:
    with urllib.request.urlopen(urllib.request.Request(url,headers=agent),timeout=90) as source:target.write_bytes(source.read())
   output=td/('output.mp4' if job['kind']=='reel' else 'output.jpg');render(job,image,font,output)
   request('/api/social/render','PUT',output.read_bytes(),{'X-Render-ID':job['id'],'Content-Type':'video/mp4' if job['kind']=='reel' else 'image/jpeg'})
 for _ in range(4):
  request('/api/social/tick');time.sleep(4)
 print('Matsprell check completed. See admin for per-channel status.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sample-image');p.add_argument('--sample-font');p.add_argument('--sample-output');args=p.parse_args()
 if args.sample_image:render({'kind':'reel','title':'Tandoori i pita'},args.sample_image,args.sample_font,args.sample_output)
 else:run()
