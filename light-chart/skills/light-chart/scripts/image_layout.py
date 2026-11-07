"""Unchanged image pixels, linked ROIs and measured layouts with explicit scales."""
from __future__ import annotations
import hashlib
import numpy as np
from composition import compose
from research_panels import image_panel, _pixel_spacing


def image_plate(size_mm, mosaic, images, *, panels=None, **layout):
    """Build image panels plus optionally empty quantitative companions.

    images maps panel IDs to image_panel keyword arguments, including pixels,
    pixel_size, unit, limits and scale_bar. Scalar calibration retains the legacy
    square-pixel behavior; a (row_spacing,col_spacing) pair preserves anisotropy.
    equal_unit_group shares physical mm per declared unit across planes.
    equal_pixel_group retains its square-pixel acquisition meaning. Otherwise
    magnifications may differ and each image retains its own calibrated scale.
    """
    options={k:dict(v) for k,v in (panels or {}).items()}
    group_units={}
    for key,entry in images.items():
        a=np.asarray(entry['pixels']); crop=entry.get('crop',(0,a.shape[0],0,a.shape[1]))
        rows,cols=crop[1]-crop[0],crop[3]-crop[2]
        spacing=_pixel_spacing(entry['pixel_size'])
        physical_height,physical_width=np.array([rows,cols])*spacing
        p=options.setdefault(key,{})
        pixel_group=entry.get('equal_pixel_group',p.get('equal_pixel_group'))
        unit_group=entry.get('equal_unit_group',p.get('equal_unit_group'))
        if pixel_group and unit_group:
            raise ValueError('Choose equal_pixel_group or equal_unit_group, not both')
        if pixel_group and spacing[0]!=spacing[1]:
            raise ValueError('Use equal_unit_group for anisotropically calibrated planes')
        if unit_group:
            if unit_group in group_units and group_units[unit_group]!=entry['unit']:
                raise ValueError('equal_unit_group requires identical declared units; no implicit unit conversion')
            group_units[unit_group]=entry['unit']
        p.update(plot_aspect=physical_width/physical_height,image_shape=[rows,cols],kind='image')
        if pixel_group:p['equal_pixel_group']=pixel_group
        if unit_group:
            p.update(equal_unit_group=unit_group,data_span=[physical_height,physical_width])
    c=compose(size_mm,mosaic,panels=options,**layout)
    records={}
    for key,entry in images.items():
        kwargs={k:v for k,v in entry.items() if k not in ('equal_pixel_group','equal_unit_group')}
        records[key]=image_panel(c.axes[key],**kwargs)
        records[key]['source_sha256']=hashlib.sha256(np.ascontiguousarray(entry['pixels']).tobytes()).hexdigest()
    c.figure._light_chart_images=records
    return c,records


def link_roi(composition, records, parent, child, *, label, color='#E69F00'):
    """Mark exact child crop in parent coordinates; no guessed or decorative ROI."""
    from matplotlib.patches import Rectangle
    p,q=records[parent],records[child]
    ps=_pixel_spacing(p['pixel_size']);qs=_pixel_spacing(q['pixel_size'])
    if p['source_sha256']!=q['source_sha256'] or not np.array_equal(ps,qs) or p['unit']!=q['unit'] or p.get('center_origin')!=q.get('center_origin'):
        raise ValueError('Linked ROIs require identical source pixels and calibration')
    pr0,pr1,pc0,pc1=p['crop']; r0,r1,c0,c1=q['crop']
    if not(pr0<=r0<r1<=pr1 and pc0<=c0<c1<=pc1):raise ValueError('ROI must lie inside parent view')
    if p.get('center_origin') is None:
        y,x=(np.array([r0-pr0,c0-pc0])*ps).tolist()
    else:
        y,x=(np.asarray(p['center_origin'])+(np.array([r0,c0])-.5)*ps).tolist()
    ax=composition.axes[parent]
    rect=Rectangle((x,y),(c1-c0)*ps[1],(r1-r0)*ps[0],
        fill=False,edgecolor=color,linewidth=.8)
    ax.add_patch(rect)
    ax.text(x,y,label,ha='left',va='bottom',color=color,fontsize=7,
        bbox={'facecolor':'black','alpha':.6,'edgecolor':'none','pad':1})
    from project_style import role
    composition.axes[child].set_title(label,loc='left',fontsize=7.5,pad=3,color=role('ink'))
    q['linked_from']=parent; q['roi_label']=label
    return rect


def orthogonal_slice(volume, *, plane, index, spacing, origin=(0,0,0)):
    """Extract a named plane from explicit ZYX voxels without resampling.

    Select scientific channels before calling; 4D arrays are rejected rather
    than interpreted as RGB. origin is the first source voxel centre in ZYX.
    pixels is an unchanged, read-only copy. pixel_size/center_origin can be
    passed directly to image_panel; remaining fields trace axes and selection.
    """
    a=np.asarray(volume);s=np.asarray(spacing,float);o=np.asarray(origin,float)
    if np.ma.isMaskedArray(volume) and np.ma.getmaskarray(volume).any():
        raise ValueError('Masked voxels need an explicit missing-domain display, not a hidden unmasking')
    if a.ndim!=3 or not a.size or not np.isfinite(a).all():
        raise ValueError('Explicit finite 3D ZYX volume required; select any channel first')
    if s.shape!=(3,) or o.shape!=(3,) or not np.isfinite([s,o]).all() or (s<=0).any():
        raise ValueError('Finite ZYX spacing/origin with positive spacing required')
    dimensions={'xy':(0,1,2),'xz':(1,0,2),'yz':(2,0,1)}
    if not isinstance(plane,str) or plane not in dimensions:
        raise ValueError('plane must be xy, xz or yz')
    fixed,row,col=dimensions[plane]
    if isinstance(index,(bool,np.bool_)) or not isinstance(index,(int,np.integer)) or not 0<=index<a.shape[fixed]:
        raise ValueError('index must select an existing source slice')
    pixels=np.take(a,int(index),axis=fixed).copy();pixels.flags.writeable=False
    return {'pixels':pixels,'pixel_size':s[[row,col]].tolist(),'center_origin':o[[row,col]].tolist(),
            'plane':plane,'index':int(index),'coordinate':float(o[fixed]+index*s[fixed]),
            'row_axis':'zyx'[row],'col_axis':'zyx'[col],'fixed_axis':'zyx'[fixed],
            'source_shape_zyx':list(a.shape),'source_sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}
