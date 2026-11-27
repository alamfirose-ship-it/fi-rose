import json,re,unicodedata as u
N=lambda s:u.normalize('NFC',s)
def build(wfile, anchors, imgs):
    w=[dict(x,text=N(x['text'])) for x in json.load(open(wfile)) if x['type']=='word' and '[' not in x['text'] and ']' not in x['text']]
    caps=[];sent=[]
    def flush(sent):
        n=len(sent)
        if not n: return
        k=-(-n//5); size=-(-n//k)
        for i in range(0,n,size):
            ch=sent[i:i+size]
            caps.append({'s':ch[0]['start'],'e':ch[-1]['end'],'t':' '.join(c['text'] for c in ch).replace('...','').strip()})
    for i,x in enumerate(w):
        sent.append(x)
        nxt=w[i+1]['start'] if i+1<len(w) else None
        if re.search(r'[।!?]$',x['text']) or nxt is None or (nxt-x['end']>0.45 and len(sent)>1):
            flush(sent); sent=[]
    for a,b in zip(caps,caps[1:]): a['e']=min(a['e']+0.25,b['s'])
    caps[-1]['e']+=0.8
    scenes=[];pos=0
    for anchor,img in zip(anchors,imgs):
        if anchor is None: scenes.append({'img':img,'s':0.0});continue
        for j in range(pos+1,len(w)):
            if w[j]['text'].startswith(N(anchor)):
                scenes.append({'img':img,'s':max(w[j]['start']-0.15,0)}); pos=j; break
        else: raise SystemExit(f'anchor {anchor} not found')
    return caps,scenes
A=['j9SdSG3C9K2jGXMiTcHe','C7yXdPIq6B3FdNHIHSF6','wEHe0j3E7nwDNVGKGWyh','T1mjBa1ZZbKDQnKlm6Qc']
B=['G24KiSXvUymFKbgB94e9','qhIEs5LcU1sN5xAeY2PV','x30rgRG50fNbberIggDx','BlYfzZrq7j4Iz8zRBMNJ']
C=['eUi7MQgqlWsKQP33tFRc','X39svflN0nJtS8nO8JcS','1Qw3B73HunAm0tGW5ugX','XJKskZszWJqXNLkyBoTc']
D=['YkXBAxtDc3WXczEfkHhx','xEuJNzJW81P9wfWSpFQp','VmsLPmxdjOe56rPqUgwp','KuWPn6HHcQIlSneonhq6']
E=['ngy0KRG5UGBoqZbnLXY4','x3n2abhPeFig2ENRSD27','DNubdaCR1y80tfXYLTni','YrIroazjGj6CF74YXJtp']
F=['owJ33hXrUCgwR54EN1ar','5erXhk5zoQw6sTSjVMiz','S08Ui3y2DORGKz5Bpq3h','c4Een5b6698z1jMQKiMH']
r1a=[None,'১৯৪৫','সকাল','তাঁর','পোড়া','শহরটার','৯','ঠিক','আবারও','২০০৯','২০১০','এটা']
r1i=[A[3],A[1],A[2],B[0],B[1],C[1],C[0],C[2],C[3],B[2],B[3],A[0]]
r2a=[None,'১৮৯৬','আর','ব্রিটিশরা','ঘড়িতে','ব্রিটিশ','কাঠের','নয়টা','জাঞ্জিবারের','আর','আর','এর']
r2i=[D[1],E[1],E[2],E[3],E[0],D[0],D[2],F[1],F[0],F[2],D[3],F[3]]
for name,wf,an,im,title,mus,vo in [('reel1','GBv2nGJY04eBj8MwnatQ.words.json',r1a,r1i,'দুই পারমাণবিক বোমা থেকেই বেঁচে ফেরা মানুষ','ML25R1BA9W24qnFLSlTI','wAwSwmeLIb8w5qvKH6fr'),
                                  ('reel2','kLGElK9gwHd2vnuCfusF.words.json',r2a,r2i,'ইতিহাসের সবচেয়ে ছোট যুদ্ধ: মাত্র ৩৮ মিনিট!','IPcpSVaWxkUG22Tds9wD','5Ey4rwtzhtpiNqkEvM45')]:
    caps,sc=build(wf,an,im)
    for s in sc: s['img']=f"/workspace/in/{s['img']}.png"
    spec={'scenes':sc,'captions':caps,'title':title,'voice':f'/workspace/in/{vo}.mp3','music':f'/workspace/in/{mus}.mp3',
          'out':f'/workspace/{name}.mp4','tmp':f'/workspace/tmp_{name}','font':'/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf',
          'brand_font':'/usr/share/fonts/truetype/freefont/FreeSansBold.ttf','brand':'Fi-rose','music_vol':0.14}
    json.dump(spec,open(f'{name}.json','w'),ensure_ascii=False)
    print(name,len(caps),[round(s['s'],1) for s in sc]); print([c['t'] for c in caps])
