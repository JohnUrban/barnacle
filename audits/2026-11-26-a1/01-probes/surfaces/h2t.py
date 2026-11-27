import sys,re,html
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in('script','style','svg'): s.skip+=1
        if t in('p','div','h1','h2','h3','h4','li','tr','br','section','details','summary','table','button'): s.out.append('\n')
        if t in('h1','h2','h3'): s.out.append('#'*int(t[1])+' ')
        d=dict(a)
        if t in ('div','section','p','span','details','button','a') and (d.get('id') or d.get('class')):
            if not s.skip: s.out.append('〔%s%s%s〕'%(t, ('#'+d['id']) if d.get('id') else '', ('.'+d['class'].replace(' ','.')) if d.get('class') else ''))
    def handle_endtag(s,t):
        if t in('script','style','svg'): s.skip-=1
        if t in ('td','th'): s.out.append(' | ')
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
p=P(); p.feed(open(sys.argv[1]).read())
t=''.join(p.out); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
