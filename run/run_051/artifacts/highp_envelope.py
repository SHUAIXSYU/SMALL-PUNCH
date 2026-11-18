"""Run051-only tangent envelope of an immutable deployed piecewise D01 table.

No fitting, source modifications, Solver, Abaqus or external process calls.
The baseline table and its original slope jumps are authoritative.
"""
from bisect import bisect_right
import math
from numbers import Real

VERSION='run051-d01-highp-tangent-envelope-v1'

def number(value,name):
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(float(value)):
        raise ValueError(name+' must be a finite real number')
    return float(value)

def ramp(t):
    if t<=0:return 0.
    if t>=1:return 1.
    return t*t*t*(10+t*(-15+6*t))

def ramp_derivative(t):
    return 30*t*t*(1-t)*(1-t) if 0<t<1 else 0.

class Envelope:
    def __init__(self,rows,p_switch,amplitude=.5,width=.05,sign=1):
        self.p=[number(r[1],'plastic strain') for r in rows]
        self.s=[number(r[0],'stress') for r in rows]
        if len(self.p)<2 or self.p[0]!=0 or self.s[0]<=0:
            raise ValueError('invalid baseline start')
        if any(b<=a for a,b in zip(self.p,self.p[1:])) or any(b<=a for a,b in zip(self.s,self.s[1:])):
            raise ValueError('baseline must have strictly increasing strain and stress')
        self.switch=number(p_switch,'switch');self.a=number(amplitude,'amplitude');self.width=number(width,'width')
        if not 0<self.switch<self.p[-1] or not 0<self.a<1 or not 0<self.width<=self.p[-1]-self.switch:
            raise ValueError('invalid envelope domain or positive-hardening bounds')
        if isinstance(sign,bool) or sign not in [-1,1]:raise ValueError('sign must be -1 or +1')
        self.sign=sign
        self.slopes=[(b-a)/(d-c) for a,b,c,d in zip(self.s,self.s[1:],self.p,self.p[1:])]

    def index(self,p):
        p=number(p,'p')
        if not self.p[0]<=p<=self.p[-1]:raise ValueError('p outside frozen material-table coverage')
        return min(bisect_right(self.p,p)-1,len(self.p)-2)

    def baseline(self,p):
        i=self.index(p)
        if p==self.p[-1]:return self.s[-1]
        return self.s[i]+self.slopes[i]*(p-self.p[i])

    def primitive(self,p):
        """Integral of clipped quintic ramp from switch to p, zero below switch."""
        x=(p-self.switch)/self.width
        if x<=0:return 0.
        if x>=1:return self.width*(x-.5)
        return self.width*x**4*(2.5+x*(-3+x))

    def modulation_integral(self,p):
        if p<=self.switch:return 0.
        total=[]
        for lo,hi,h in zip(self.p,self.p[1:],self.slopes):
            a=max(lo,self.switch);b=min(hi,p)
            if b>a:total.append(h*(self.primitive(b)-self.primitive(a)))
            if hi>=p:break
        return math.fsum(total)

    def stress(self,p):
        base=self.baseline(p)
        if p<=self.switch:return base
        return base+self.sign*self.a*self.modulation_integral(p)

    def hardening(self,p):
        h=self.slopes[self.index(p)]
        return h*(1+self.sign*self.a*ramp((p-self.switch)/self.width))

    def curvature_bound(self,lo,hi):
        """Bound on one baseline segment, endpoints may include original knots."""
        if hi<=lo:raise ValueError('empty interval')
        if hi<=self.switch or lo>=self.switch+self.width:return 0.
        i=self.index((lo+hi)*.5)
        if any(lo<q<hi for q in self.p):raise ValueError('interval straddles baseline slope jump')
        t0=max(0.,(lo-self.switch)/self.width);t1=min(1.,(hi-self.switch)/self.width)
        candidates=[ramp_derivative(t0),ramp_derivative(t1)]
        if t0<=.5<=t1:candidates.append(1.875)
        return self.a*self.slopes[i]*max(candidates)/self.width

    def sample(self,relative_tolerance=1e-5):
        tol=number(relative_tolerance,'tolerance')
        if tol<=0:raise ValueError('nonpositive interpolation tolerance')
        knots=sorted(set(self.p+[self.switch,self.switch+self.width]));bounds=[];grid=[knots[0]]
        def refine(lo,hi,depth=0):
            bound=self.curvature_bound(lo,hi)*(hi-lo)**2/8
            relative=bound/self.stress(lo)
            if relative>tol:
                if depth>=30:raise RuntimeError('adaptive interpolation limit')
                mid=(lo+hi)*.5;refine(lo,mid,depth+1);refine(mid,hi,depth+1)
            else:
                grid.append(hi);bounds.append({'p0':lo,'p1':hi,'absolute_stress_bound_pa':bound,'relative_stress_bound':relative})
        for lo,hi in zip(knots,knots[1:]):refine(lo,hi)
        return [(self.stress(p),p) for p in grid],bounds

def plastic_block(raw):
    """Return exact byte prefixes/suffixes and numeric-row text of one Plastic block."""
    lines=raw.splitlines(keepends=True);starts=[i for i,s in enumerate(lines) if s.strip().lower()==b'*plastic']
    if len(starts)!=1:raise ValueError('expected exactly one plastic block')
    begin=starts[0]+1;end=next((i for i in range(begin,len(lines)) if lines[i].lstrip().startswith(b'*')),len(lines))
    rows=[];texts={}
    for line in lines[begin:end]:
        if not line.strip():continue
        parts=line.decode('ascii').split(',')
        if len(parts)!=2:raise ValueError('unexpected plastic table fields')
        stress,p=map(float,parts);rows.append((stress,p));texts[p]=line
    return b''.join(lines[:begin]),b''.join(lines[end:]),rows,texts

def table_fragment(rows,baseline_texts,switch,newline=b'\n'):
    out=[]
    for stress,p in rows:
        if p<=switch and p in baseline_texts:out.append(baseline_texts[p])
        else:out.append((format(stress,'.17g')+', '+format(p,'.17g')).encode('ascii')+newline)
    return b''.join(out)
