/** Offline validation; no authoring runtime or desktop application required. */
export function validate(s) {
  const need=(ok,message)=>{if(!ok)throw new Error(message);};
  const obj=(v,label)=>{need(v!==null&&typeof v==='object'&&!Array.isArray(v),label+' must be an object');return v;};
  const list=(v,label)=>{need(Array.isArray(v),label+' must be an array');return v;};
  const text=(v,label)=>need(typeof v==='string'&&v.trim().length>0,label+' must be nonempty text');
  const num=(v)=>typeof v==='number'&&Number.isFinite(v);
  obj(s,'scene'); need(s.schema_version==='1.0','Expected schema_version 1.0');
  obj(s.canvas,'canvas'); const {width_px:w,height_px:h}=s.canvas;
  need([w,h].every(v=>num(v)&&v>0),'Invalid canvas');
  if('pixels_per_inch' in s.canvas)need(num(s.canvas.pixels_per_inch)&&s.canvas.pixels_per_inch>0,'Invalid pixels_per_inch metadata');
  if('font' in s)text(s.font,'font');
  obj(s.provenance,'provenance');
  for(const key of ['source','source_sha256','scientific_source'])text(s.provenance[key],'provenance.'+key);
  for(const key of ['corrections','limitations'])if(key in s.provenance)need(list(s.provenance[key],key).every(v=>typeof v==='string'),key+' must contain text');
  const pages=list(s.pages,'pages'); need(pages.length>0,'No pages');
  const slugs=new Set();
  function points(n,closed=false) {
    const pts=list(n.points,n.id+' points');
    const curve=n.curve??(n.type==='bezier'?'bezier':'polyline');
    need(['polyline','bezier'].includes(curve),'Unsupported curve '+n.id);
    need(pts.length>=2,'A path needs at least two points '+n.id);
    for(const q of pts)need(Array.isArray(q)&&q.length===2&&q.every(num)&&q[0]>=0&&q[1]>=0&&q[0]<=w&&q[1]<=h,'Invalid point '+n.id);
    if(curve==='bezier')need(pts.length>=4&&(pts.length-1)%3===0,'Expected 3k+1 Bezier points '+n.id);
    if(closed)need(pts.length>=4&&pts[0].every((v,i)=>v===pts.at(-1)[i]),'Node contour must close '+n.id);
  }
  for(const p of pages) {
    obj(p,'page');text(p.name,'page name');
    need(typeof p.slug==='string'&&/^[a-z0-9][a-z0-9-]*$/.test(p.slug)&&!slugs.has(p.slug),'Invalid or duplicate page slug');
    need(['faithful','science_corrected','science-corrected'].includes(p.mode),'Invalid reconstruction mode');
    slugs.add(p.slug);
    for(const key of ['nodes','paths','edges'])list(p[key],key);
    const items=[...p.nodes,...p.paths,...p.edges],ids=new Set();
    for(const n of items) {
      obj(n,'item');
      need(typeof n.id==='string'&&/^[A-Za-z][A-Za-z0-9_]*$/.test(n.id)&&!ids.has(n.id),'Invalid or duplicate ID');
      need(!/__(bend|seg)_\d+$/.test(n.id),'Reserved connector helper suffix '+n.id); ids.add(n.id);
      if('text' in n)need(typeof n.text==='string','text must be a string');
      if('radius_px' in n)need(num(n.radius_px)&&n.radius_px>=0,'Invalid radius');
      const st=obj(n.style??{},'style');
      for(const k of ['fill','fill_secondary','stroke','text_color'])if(k in st)need(typeof st[k]==='string'&&(/^#[0-9a-fA-F]{6}$/.test(st[k])||['fill','stroke'].includes(k)&&st[k]==='none'),'Invalid color '+k);
      if(st.fill_secondary)need(st.fill&&st.fill!=='none','Gradient needs primary color');
      for(const k of ['font_px','stroke_px'])if(k in st)need(num(st[k])&&(k==='font_px'?st[k]>0:st[k]>=0),'Invalid '+k);
      if('align' in st)need(Number.isInteger(st.align)&&[0,1,2].includes(st.align),'Invalid alignment');
      if('bold' in st)need(typeof st.bold==='boolean','bold must be boolean');
      if('dash_pattern' in st)need(Number.isInteger(st.dash_pattern)&&st.dash_pattern>=0,'Invalid dash_pattern');
      for(const k of ['arrow','begin_arrow'])if(k in n)need(Number.isInteger(n[k])&&n[k]>=0,'Invalid '+k);
    }
    for(const n of p.nodes) {
      need(['rect','roundrect','text','ellipse','junction','polygon','bezier'].includes(n.type),'Unknown node type');
      const b=n.bbox;need(Array.isArray(b)&&b.length===4&&b.every(num)&&b[2]>0&&b[3]>0&&b[0]>=0&&b[1]>=0&&b[0]+b[2]<=w+.01&&b[1]+b[3]<=h+.01,'Invalid bbox '+n.id);
      if(['polygon','bezier'].includes(n.type))points(n,true);
      if('subscript_start' in n)need(Number.isInteger(n.subscript_start)&&n.subscript_start>=0&&n.subscript_start<(n.text??'').length,'Invalid subscript_start');
      if('native_text_edit' in n)need(typeof n.native_text_edit==='boolean','native_text_edit must be boolean');
    }
    for(const n of [...p.paths,...p.edges])points(n);
    const nodes=new Map(p.nodes.map(n=>[n.id,n]));
    for(const e of p.edges) {
      if(e.curve==='bezier')need(['curvedConnector2','curvedConnector3'].includes(e.native_curve_approximation),'Bezier edge needs explicit native_curve_approximation');
      for(const [side,index] of [['source',0],['target',e.points.length-1]]) {
        const end=obj(e[side],side),n=nodes.get(end.node);
        need(n&&Array.isArray(end.anchor)&&end.anchor.length===2&&end.anchor.every(v=>num(v)&&v>=0&&v<=1),'Invalid endpoint '+e.id);
        const [x,y,nw,nh]=n.bbox;
        need(Math.hypot(x+nw*end.anchor[0]-e.points[index][0],y+nh*end.anchor[1]-e.points[index][1])<=.2,'Endpoint disagrees with anchor '+e.id);
      }
    }
    if('draw_order' in p)need(Array.isArray(p.draw_order)&&p.draw_order.length===ids.size&&new Set(p.draw_order).size===ids.size&&p.draw_order.every(id=>ids.has(id)),'draw_order must list all IDs once');
  }
  return {pages:pages.length,objects:pages.reduce((n,p)=>n+p.nodes.length+p.paths.length+p.edges.length,0)};
}
