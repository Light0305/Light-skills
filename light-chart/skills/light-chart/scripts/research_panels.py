"""Data-preserving constructions needed beyond basic chart templates.

Informed by the four retained sources: evidence roles, raw-data encoding,
reference signatures, and composable implementations. No statistical tests.
"""
from __future__ import annotations
import numpy as np
from project_style import role, colormap


def paired_changes(data, *, id, condition, value, order):
    """Match long records by ID. Never silently average duplicates/drop pairs."""
    if len(order) != 2 or len(set(order)) != 2:
        raise ValueError('Two distinct conditions required')
    if not {id, condition, value} <= set(data.columns) or not len(data):
        raise ValueError('Missing fields or empty data')
    d = data[[id, condition, value]].copy()
    if d.isna().any().any() or d.duplicated([id, condition]).any():
        raise ValueError('Missing/duplicate ID-condition observations')
    if set(d[condition]) != set(order):
        raise ValueError('Condition labels do not match declared order')
    wide = d.pivot(index=id, columns=condition, values=value).reindex(columns=order)
    if wide.isna().any().any() or not np.isfinite(wide.to_numpy(float)).all():
        raise ValueError('Incomplete pairs or nonfinite measurements')
    wide['change'] = wide[order[1]] - wide[order[0]]
    return wide


def joint_density(ax, top, right, x, y, *, cax=None, gridsize=35, limits=None):
    """Hexbin count field plus marginals computed from the identical records."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.ndim != 1 or x.shape != y.shape or not len(x) or not np.isfinite([x,y]).all():
        raise ValueError('Finite equally-sized x/y vectors required')
    if len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        raise ValueError('Both coordinates need a nonzero range')
    if limits is None:
        limits = [x.min(), x.max(), y.min(), y.max()]
    if len(limits)!=4 or not np.isfinite(limits).all() or not (limits[0] <= x.min() < x.max() <= limits[1] and limits[2] <= y.min() < y.max() <= limits[3]):
        raise ValueError('Limits must cover all observations')
    hb = ax.hexbin(x, y, gridsize=gridsize, extent=limits, mincnt=1,
                   cmap=colormap(), linewidths=0, rasterized=True)
    nx,bx,_ = top.hist(x,bins=30,range=limits[:2],color=role('primary'),alpha=.65,linewidth=0)
    ny,by,_ = right.hist(y,bins=30,range=limits[2:],orientation='horizontal',color=role('primary'),alpha=.65,linewidth=0)
    ax.set(xlim=limits[:2],ylim=limits[2:]); top.set_xlim(limits[:2]); right.set_ylim(limits[2:])
    top.tick_params(axis='x',labelbottom=False,bottom=False); right.tick_params(axis='y',labelleft=False,left=False)
    top.set_ylabel('Count'); right.set_xlabel('Count')
    if cax is not None:
        ax.figure.colorbar(hb,cax=cax,label='Count / hexagon')
    return {'mappable':hb,'n':len(x),'hexbin_total':float(hb.get_array().sum()),
            'x_hist_total':int(nx.sum()),'y_hist_total':int(ny.sum()),'x_edges':bx,'y_edges':by}


def _pixel_spacing(pixel_size):
    """Normalize explicit scalar or (row, column) calibration without averaging."""
    try:
        value = np.asarray(pixel_size, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError('pixel_size must be a positive scalar or (row_spacing, col_spacing)') from exc
    if value.ndim == 0:
        value = np.repeat(value, 2)
    if value.shape != (2,) or not np.isfinite(value).all() or (value <= 0).any():
        raise ValueError('pixel_size must be a positive scalar or (row_spacing, col_spacing)')
    return value


def image_panel(ax, pixels, *, pixel_size, unit, limits, scale_bar, crop=None, cmap='gray', center_origin=None):
    """Display unchanged grayscale/RGB observations with explicit calibration.

    crop is (row_start,row_stop,col_start,col_stop), in original pixel indices.
    pixel_size is a scalar for square pixels or (row_spacing, col_spacing).
    By default the displayed crop has its top-left outer edge at local (0,0),
    preserving the original API. Explicit center_origin=(row0,col0) instead gives
    the physical centre of the first pixel of the uncropped source, with edges
    origin + (source_index - 0.5) * spacing. No coordinate origin is inferred.
    This function does not denoise, generate pixels, count cells or infer scale.
    """
    a=np.asarray(pixels)
    rgb=a.ndim==3 and a.shape[2]==3
    if (a.ndim!=2 and not rgb) or not a.size or not np.isfinite(a).all():
        raise ValueError('A finite nonempty grayscale or RGB image is required')
    spacing = _pixel_spacing(pixel_size)
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError('Explicit positive size per pixel and a unit required')
    if center_origin is not None:
        center_origin = np.asarray(center_origin, dtype=float)
        if center_origin.shape != (2,) or not np.isfinite(center_origin).all():
            raise ValueError('center_origin must contain finite (row0, col0) source-pixel centres')
    if rgb:
        if limits is not None:raise ValueError('RGB pixels retain native colors; limits must be None')
        if not ((a.dtype==np.uint8) or (a.dtype.kind=='f' and a.min()>=0 and a.max()<=1)):
            raise ValueError('RGB must be uint8 or float in [0,1]; no silent clipping')
    elif limits is None or len(limits)!=2 or not np.isfinite(limits).all() or limits[0]>=limits[1]:
        raise ValueError('Shared increasing display intensity limits required')
    if crop is None:crop=(0,a.shape[0],0,a.shape[1])
    if len(crop)!=4 or any(not isinstance(v,(int,np.integer)) for v in crop):
        raise ValueError('Crop must be four integer source-pixel indices')
    r0,r1,c0,c1=crop
    if not (0<=r0<r1<=a.shape[0] and 0<=c0<c1<=a.shape[1]):
        raise ValueError('Crop outside original pixels')
    shown=a[r0:r1,c0:c1]; height,width=np.array(shown.shape[:2])*spacing
    top,left=(0.,0.) if center_origin is None else center_origin+(np.array([r0,c0])-.5)*spacing
    if not np.isfinite(scale_bar) or not 0<scale_bar<width*.75:
        raise ValueError('Scale bar must fit inside the calibrated image')
    display={} if rgb else dict(cmap=cmap,vmin=limits[0],vmax=limits[1])
    ax.imshow(shown,extent=(left,left+width,top+height,top),interpolation='nearest',aspect='equal',**display)
    x0=left+width*.08; y0=top+height*.90
    ax.plot([x0,x0+scale_bar],[y0,y0],color='black',linewidth=3)
    ax.plot([x0,x0+scale_bar],[y0,y0],color='white',linewidth=1.8)
    ax.text(x0,y0-height*.055,f'{scale_bar:g} {unit}',color='white',fontsize=7,
            bbox={'facecolor':'black','alpha':.65,'edgecolor':'none','pad':1})
    ax.set_axis_off()
    return {'source_shape':list(a.shape),'crop':list(crop),'display_shape':list(shown.shape),
            'pixel_size':float(pixel_size) if np.asarray(pixel_size).ndim==0 else spacing.tolist(),
            'pixel_spacing':spacing.tolist(),'center_origin':None if center_origin is None else center_origin.tolist(),
            'extent':[float(left),float(left+width),float(top+height),float(top)],
            'coordinate_convention':'crop-local outer edge' if center_origin is None else 'uncropped source pixel centres',
            'unit':unit,'display_limits':None if rgb else list(limits),
            'scale_bar':float(scale_bar),'color_mode':'native RGB' if rgb else 'grayscale',
            'windowed_pixels':0 if rgb else int(((shown<limits[0])|(shown>limits[1])).sum())}


def network_panel(ax, nodes, positions, edges, *, colors=None, edge_colors=None):
    """Weighted undirected network at caller-supplied coordinates."""
    nodes=list(nodes); edges=list(edges); pos=np.asarray(positions,float)
    if not nodes or len(nodes)!=len(set(nodes)) or pos.shape!=(len(nodes),2) or not np.isfinite(pos).all():
        raise ValueError('Unique nodes and matching finite 2D positions required')
    lookup=dict(zip(nodes,pos)); weights=[]
    for source,target,weight in edges:
        if source not in lookup or target not in lookup or not np.isfinite(weight) or weight<0:
            raise ValueError('Unknown edge endpoint or invalid weight')
        weights.append(weight)
    maximum=max(weights,default=1) or 1
    edge_colors = [role('baseline')]*len(edges) if edge_colors is None else list(edge_colors)
    if len(edge_colors)!=len(edges):raise ValueError('One color per edge required')
    for (source,target,weight),edge_color in zip(edges,edge_colors):
        xy=np.array([lookup[source],lookup[target]])
        ax.plot(xy[:,0],xy[:,1],color=edge_color,linewidth=.4+2*weight/maximum,alpha=.55,zorder=1)
    colors=[role('primary')]*len(nodes) if colors is None else list(colors)
    if len(colors)!=len(nodes):raise ValueError('One color per node required')
    ax.scatter(pos[:,0],pos[:,1],s=80,c=colors,edgecolors='white',linewidths=.6,zorder=2)
    center=pos.mean(axis=0)
    for node,(x,y) in lookup.items():
        dx,dy=np.array([x,y])-center
        norm=np.hypot(dx,dy) or 1
        ax.annotate(str(node),(x,y),xytext=(10*dx/norm,10*dy/norm),textcoords='offset points',
                    ha='left' if dx>1e-8 else 'right' if dx<-1e-8 else 'center',
                    va='bottom' if dy>1e-8 else 'top' if dy<-1e-8 else 'center',fontsize=7)
    ax.margins(.30);ax.set_aspect('equal');ax.set_axis_off()
    return {'nodes':len(nodes),'edges':len(edges),'positions':pos.tolist(),'weight_limits':[min(weights,default=0),max(weights,default=0)]}
