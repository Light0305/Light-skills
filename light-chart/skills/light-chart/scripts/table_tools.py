"""Native LaTeX scientific tables with explicit numeric ranking.

Original implementation, informed by the user's table corpus: grouped headers,
quiet rules, precision consistency, missing cells and selective emphasis.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np
from matplotlib.patches import Rectangle


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    width: float
    fmt: str = '.2f'
    better: Optional[str] = None
    display_key: Optional[str] = None
    align: str = 'right'


def best_cells(rows, columns, *, atol=0):
    """Rank raw numeric values, never rounded strings. Ties retain all winners.

    Numerical best is not statistical significance. atol must be explicitly
    nonzero when treating near-values as ties is scientifically appropriate.
    """
    if not np.isfinite(atol) or atol < 0: raise ValueError('atol must be nonnegative')
    winners = set()
    for j, col in enumerate(columns):
        if col.better is None: continue
        if col.better not in {'min','max'}: raise ValueError('better must be min, max or None')
        vals=[]
        for row in rows:
            v=row[col.key]
            vals.append(np.nan if v is None else float(v))
        a=np.asarray(vals)
        if np.isinf(a).any(): raise ValueError('Infinite table values are not supported')
        valid=np.isfinite(a)
        if not valid.any(): continue
        target=np.min(a[valid]) if col.better=='min' else np.max(a[valid])
        winners.update((int(i),j) for i in np.flatnonzero(valid & np.isclose(a,target,rtol=0,atol=atol)))
    return winners


def latex_escape(value):
    """Escape literal content, not caller-supplied TeX instructions."""
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
      '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
      '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
      '±': r'\(\pm\)', '↑': r'\(\uparrow\)', '↓': r'\(\downarrow\)',
      '—': r'\textemdash{}', '−': '-'}
    return ''.join(replacements.get(char, char) for char in str(value))


def to_latex(rows, columns, *, spanners=(), section_starts=(), rank=False,
             tie_atol=0, missing='—'):
    """Return a booktabs tabular fragment, without a float, caption or image.

    The document controls placement, caption, font and table numbering. Literal
    cell/header text is escaped. Raw numeric keys determine ranking; formatted
    display strings never determine ties. Column.width is a plotting hint only
    and does not force LaTeX widths or shrink the complete table.
    """
    if not rows or not columns: raise ValueError('Table requires rows and columns')
    if len({c.key for c in columns}) != len(columns): raise ValueError('Column keys must be unique')
    if any(c.align not in {'left','right','center'} for c in columns): raise ValueError('Invalid alignment')
    if any(not all(c.key in row for c in columns) for row in rows): raise ValueError('Missing column key')
    if any(i < 0 or i >= len(rows) for i in section_starts): raise ValueError('Invalid row index')
    ordered=sorted(spanners,key=lambda s:s[1]);occupied=set()
    for label,start,stop in ordered:
        if not label or not 0<=start<stop<=len(columns) or occupied.intersection(range(start,stop)):
            raise ValueError('Invalid or overlapping column spanners')
        occupied.update(range(start,stop))
    winners=best_cells(rows,columns,atol=tie_atol) if rank else set()
    spec=''.join({'left':'l','right':'r','center':'c'}[c.align] for c in columns)
    lines=[r'% Requires \usepackage{booktabs}',r'\begin{tabular}{@{}'+spec+r'@{}}',r'\toprule']
    endrow = r' \\'
    if ordered:
        by_start={start:(label,stop) for label,start,stop in ordered}
        cells=[];j=0
        while j<len(columns):
            if j in by_start:
                label,stop=by_start[j]
                cells.append(r'\multicolumn{'+str(stop-j)+r'}{c}{'+latex_escape(label)+'}')
                j=stop
            else:cells.append('');j+=1
        lines.append(' & '.join(cells)+endrow)
        lines.append(' '.join(r'\cmidrule(lr){'+f'{start+1}-{stop}'+'}' for _,start,stop in ordered))
    lines.extend([' & '.join(latex_escape(c.label) for c in columns)+endrow,r'\midrule'])
    for i,row in enumerate(rows):
        if i in section_starts and i:lines.append(r'\addlinespace')
        cells=[]
        for j,col in enumerate(columns):
            v=row[col.key]
            if v is None or (isinstance(v,(float,np.floating)) and np.isnan(v)):
                text=missing
            else:
                if isinstance(v,(int,float,np.number)) and not np.isfinite(v):
                    raise ValueError('Infinite table values are not supported')
                if col.display_key is not None:
                    if col.display_key not in row:raise ValueError('Missing explicit display field')
                    text=str(row[col.display_key])
                else:text=format(v,col.fmt) if isinstance(v,(int,float,np.number)) else str(v)
            cell=latex_escape(text)
            if (i,j) in winners:cell=r'\textbf{'+cell+'}'
            cells.append(cell)
        lines.append(' & '.join(cells)+endrow)
    lines.extend([r'\bottomrule',r'\end{tabular}'])
    return '\n'.join(lines)+'\n'


def scientific_table(ax, rows, columns, *, spanners=(), section_starts=(),
                     emphasis_rows=(), fontsize=7.5, header_fontsize=None,
                     highlight='#E5F0F3', ink='#252B32', rank=False,
                     missing='—', tie_atol=0):
    """Draw a table on one axes, spanners=(label, start_col, stop_col_exclusive).

    Widths are declared fractions. No inferred metric direction, imputation,
    significance, sorting, automatic shrink-to-fit or silent row truncation.
    Returned cells expose artists for actual rendered-bbox checks.
    """
    if not rows or not columns: raise ValueError('Table requires rows and columns')
    if len({c.key for c in columns})!=len(columns): raise ValueError('Column keys must be unique')
    widths=np.asarray([c.width for c in columns],float)
    if not np.isfinite(widths).all() or (widths<=0).any() or not np.isclose(widths.sum(),1):
        raise ValueError('Positive column widths must sum to 1')
    if any(c.align not in {'left','right','center'} for c in columns): raise ValueError('Invalid alignment')
    if any(not all(c.key in row for c in columns) for row in rows): raise ValueError('Missing column key')
    if any(i < 0 or i >= len(rows) for i in [*section_starts,*emphasis_rows]): raise ValueError('Invalid row index')
    occupied=set()
    for label,start,stop in spanners:
        if not label or not 0<=start<stop<=len(columns) or occupied.intersection(range(start,stop)):
            raise ValueError('Invalid or overlapping column spanners')
        occupied.update(range(start,stop))
    winners=best_cells(rows,columns,atol=tie_atol) if rank else set()
    edges=np.r_[0,np.cumsum(widths)]
    header=2.15 if spanners else 1.25
    total=len(rows)+header+.25
    ax.set(xlim=(0,1),ylim=(total,0));ax.axis('off')
    header_fontsize=fontsize if header_fontsize is None else header_fontsize
    ax.hlines(.05,0,1,color=ink,lw=.8)
    for label,start,stop in spanners:
        ax.text((edges[start]+edges[stop])/2,.47,label,ha='center',va='center',fontsize=header_fontsize,color=ink)
        ax.hlines(.87,edges[start]+.009,edges[stop]-.009,color='#8A929A',lw=.4)
    hy=1.35 if spanners else .55
    def xanchor(j,align):
        if align=='left': return edges[j]+.012
        if align=='right': return edges[j+1]-.012
        return (edges[j]+edges[j+1])/2
    for j,col in enumerate(columns):
        ax.text(xanchor(j,col.align),hy,col.label,ha=col.align,va='center',fontsize=header_fontsize,color=ink)
    ax.hlines(header-.25,0,1,color=ink,lw=.55)
    cells=[]
    for i,row in enumerate(rows):
        y=header+i+.25
        if i in emphasis_rows:
            ax.add_patch(Rectangle((0,y-.47),1,.94,facecolor=highlight,edgecolor='none',zorder=-1))
        if i in section_starts and i:
            ax.hlines(y-.5,0,1,color='#A8AFB6',lw=.4)
        for j,col in enumerate(columns):
            v=row[col.key]
            if v is None or (isinstance(v,(float,np.floating)) and np.isnan(v)):
                label=missing
            elif col.display_key is not None:
                if col.display_key not in row: raise ValueError('Missing explicit display field')
                label=str(row[col.display_key])
            elif isinstance(v,(int,float,np.number)):
                if not np.isfinite(v): raise ValueError('Infinite table values are not supported')
                label=format(v,col.fmt)
            else: label=str(v)
            artist=ax.text(xanchor(j,col.align),y,label,ha=col.align,va='center',
                fontsize=fontsize,color=ink,fontweight='bold' if (i,j) in winners else 'normal')
            cells.append({'row':i,'column':j,'text':label,'best':(i,j) in winners,'artist':artist})
    ax.hlines(total-.04,0,1,color=ink,lw=.8)
    return cells


def require_table_fit(ax, cells, *, padding_pt=1):
    """Fail if a rendered cell exceeds its declared axes or overlaps another.

    Includes header text as well as body cells. This does not replace final-size
    visual checks or judge whether the chosen columns belong together.
    """
    fig=ax.figure;fig.canvas.draw();renderer=fig.canvas.get_renderer()
    pad=padding_pt*fig.dpi/72
    texts=[t for t in ax.texts if t.get_visible() and t.get_text()]
    boxes=[t.get_window_extent(renderer) for t in texts]
    canvas=ax.get_window_extent(renderer)
    for t,b in zip(texts,boxes):
        if b.x0<canvas.x0 or b.x1>canvas.x1 or b.y0<canvas.y0 or b.y1>canvas.y1:
            raise ValueError(f'Table text exceeds table rectangle: {t.get_text()}')
    for i,b in enumerate(boxes):
        for j in range(i+1,len(boxes)):
            c=boxes[j]
            if b.x0-pad<c.x1 and b.x1+pad>c.x0 and b.y0-pad<c.y1 and b.y1+pad>c.y0:
                raise ValueError(f'Table text collision: {texts[i].get_text()} / {texts[j].get_text()}')
    return True
