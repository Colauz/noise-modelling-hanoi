import warnings; warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, base64, io

df=pd.read_csv('data/raw/hanoi/measurements.csv',parse_dates=['timestamp'])
df['hour']=df.timestamp.dt.hour
df['dow']=df.timestamp.dt.dayofweek
df['dayname']=df.timestamp.dt.day_name()
df['period']=np.where((df.hour>=21)|(df.hour<6),'night','day')
df['is_constr']=df['class'].astype(str).str.contains('construction',case=False)
df['type']=np.where(df.is_constr,'Construction','Transportation/other')
# normes
QCVN_D,QCVN_N=70,55; WHO_D,WHO_N=53,45
SITES=df.site.unique(); COL={s:c for s,c in zip(SITES,['#d62728','#1f77b4','#2ca02c','#9467bd'])}

def png(fig):
    b=io.BytesIO(); fig.savefig(b,format='png',dpi=110,bbox_inches='tight'); plt.close(fig)
    return base64.b64encode(b.getvalue()).decode()

# 1. cycle horaire par site
f1,ax=plt.subplots(figsize=(11,5))
for s in SITES:
    g=df[df.site==s].groupby('hour')['noise_dB'].median()
    ax.plot(g.index,g.values,marker='o',label=s,color=COL[s],lw=2)
ax.axhline(QCVN_D,ls='--',c='red',alpha=.7,label='QCVN jour 70'); ax.axhline(QCVN_N,ls='--',c='darkred',alpha=.7,label='QCVN nuit 55')
ax.axhline(WHO_D,ls=':',c='gray',alpha=.7,label='OMS jour 53'); ax.axhline(WHO_N,ls=':',c='black',alpha=.6,label='OMS nuit 45')
ax.set_xlabel('Heure'); ax.set_ylabel('dB médian'); ax.set_title('Cycle horaire du bruit par site (sur une journée)')
ax.set_xticks(range(0,24,2)); ax.legend(fontsize=8,ncol=2); ax.grid(alpha=.3)
img1=png(f1)

# 2. day-of-week
f2,ax=plt.subplots(figsize=(11,5))
order=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for s in SITES:
    g=df[df.site==s].groupby('dayname')['noise_dB'].median().reindex(order)
    ax.plot(range(7),g.values,marker='s',label=s,color=COL[s],lw=2)
ax.axhline(QCVN_D,ls='--',c='red',alpha=.7); ax.axhline(WHO_D,ls=':',c='gray',alpha=.7)
ax.set_xticks(range(7)); ax.set_xticklabels(['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'])
ax.set_ylabel('dB médian'); ax.set_title('Profil par jour de la semaine'); ax.legend(fontsize=8); ax.grid(alpha=.3)
img2=png(f2)

# 3. transport vs construction
f3,(a1,a2)=plt.subplots(1,2,figsize=(11,5))
data=[df[df.type=='Transportation/other'].noise_dB.dropna(),df[df.is_constr].noise_dB.dropna()]
a1.boxplot(data,labels=['Transport','Construction'])
a1.axhline(QCVN_D,ls='--',c='red',alpha=.7,label='QCVN 70'); a1.set_ylabel('dB'); a1.set_title('Transport vs Construction'); a1.legend(fontsize=8); a1.grid(alpha=.3)
for i,d in enumerate(data,1): a1.text(i,d.median(),f'{d.median():.0f}',ha='center',va='bottom',fontweight='bold')
# par site
w=0.35
for i,s in enumerate(SITES):
    sub=df[df.site==s]
    a2.bar(i-w/2,sub[~sub.is_constr].noise_dB.median(),w,color='#1f77b4',label='Transport' if i==0 else '')
    cv=sub[sub.is_constr].noise_dB.median()
    a2.bar(i+w/2,cv if not np.isnan(cv) else 0,w,color='#ff7f0e',label='Construction' if i==0 else '')
a2.axhline(QCVN_D,ls='--',c='red',alpha=.7); a2.set_xticks(range(len(SITES))); a2.set_xticklabels([s.replace(' ','\n') for s in SITES],fontsize=8)
a2.set_ylabel('dB médian'); a2.set_title('Par site'); a2.legend(fontsize=8); a2.grid(alpha=.3)
img3=png(f3)

# 4. dépassements
rows=''
for s in SITES:
    for per in ['day','night']:
        sub=df[(df.site==s)&(df.period==per)]
        if len(sub)==0: continue
        lim=QCVN_D if per=='day' else QCVN_N
        exc=(sub.noise_dB>lim).mean()*100
        sev=(sub.noise_dB-lim)[sub.noise_dB>lim].mean()
        rows+=f"<tr><td>{s}</td><td>{'jour' if per=='day' else 'nuit'}</td><td>{len(sub)}</td><td>{sub.noise_dB.median():.0f}</td><td>{lim}</td><td><b>{exc:.0f}%</b></td><td>{sev:.1f} dB</td></tr>"
# peak periods
peak=df.groupby('hour')['noise_dB'].median()
peakh=peak.idxmax(); quieth=peak.idxmin()

f4,ax=plt.subplots(figsize=(11,4.5))
pe=df.groupby('hour').apply(lambda g:(g.noise_dB>np.where((g.hour>=21)|(g.hour<6),QCVN_N,QCVN_D)).mean()*100)
ax.bar(pe.index,pe.values,color=['darkred' if v>50 else 'orange' if v>0 else 'green' for v in pe.values])
ax.set_xlabel('Heure'); ax.set_ylabel('% mesures > QCVN'); ax.set_title('Fréquence de dépassement QCVN par heure'); ax.set_xticks(range(0,24,2)); ax.grid(alpha=.3)
img4=png(f4)

glob_exc=(df.noise_dB>np.where(df.period=='night',QCVN_N,QCVN_D)).mean()*100
html=f"""<!DOCTYPE html><html><head><meta charset=utf-8><title>Analyse bruit Hanoï</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:20px auto;padding:0 16px;color:#222}}
h1{{border-bottom:3px solid #d62728}}h2{{margin-top:34px;color:#333}}img{{width:100%;border:1px solid #ddd;border-radius:6px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}td,th{{border:1px solid #ccc;padding:6px 10px;text-align:center;font-size:14px}}th{{background:#f3f3f3}}
.kpi{{display:inline-block;background:#fbeaea;border-radius:8px;padding:12px 18px;margin:6px;font-size:15px}}</style></head><body>
<h1>Analyse du bruit urbain — Hanoï ({len(df)} mesures, 3 sites)</h1>
<div class=kpi><b>{glob_exc:.0f}%</b> des mesures dépassent QCVN 26:2010</div>
<div class=kpi>Pic à <b>{peakh}h</b> · plus calme à <b>{quieth}h</b></div>
<div class=kpi>dB médian global <b>{df.noise_dB.median():.0f}</b> (min {df.noise_dB.min():.0f} / max {df.noise_dB.max():.0f})</div>
<h2>1. Cycle horaire par site (vs normes QCVN & OMS)</h2><img src="data:image/png;base64,{img1}">
<h2>2. Profil par jour de la semaine</h2><img src="data:image/png;base64,{img2}">
<h2>3. Transport vs Construction</h2><img src="data:image/png;base64,{img3}">
<h2>4. Dépassements : fréquence par heure</h2><img src="data:image/png;base64,{img4}">
<h2>Tableau des dépassements QCVN 26:2010 par site</h2>
<table><tr><th>Site</th><th>Période</th><th>n</th><th>dB médian</th><th>Limite</th><th>% dépassement</th><th>Sévérité moy.</th></tr>{rows}</table>
<p style=color:#888;font-size:13px>QCVN 26:2010/BTNMT : 70 dB jour (6-21h) / 55 dB nuit. OMS : 53/45 dB. Généré automatiquement.</p>
</body></html>"""
open('outputs/maps/hanoi_analyse_bruit.html','w').write(html)
print('rapport écrit: outputs/maps/hanoi_analyse_bruit.html')
print(f'dépassement global QCVN: {glob_exc:.0f}%  | pic {peakh}h, calme {quieth}h')
