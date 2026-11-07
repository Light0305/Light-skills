"""Quantitative 2D/3D fields: explicit coordinates, topology and color semantics.

Derived design: nature chart types + RNAGenScape surface structure + FigMirror
3D inventory. These helpers never fit a prettier surface to research data.
"""
from dataclasses import dataclass
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm


@dataclass(frozen=True)
class GridField:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    norm: Normalize


def grid_field(x, y, z, *, limits, center=None):
    """z[y_index, x_index]; reorder descending axes and z together, retain NA.

    No resampling, clipping, normalization, smoothing or interpolation is done.
    Limits are mandatory and shared between quantitative 2D and 3D views.
    """
    x, y = np.array(x, float, copy=True), np.array(y, float, copy=True)
    z = np.array(np.ma.filled(np.ma.asarray(z, dtype=float), np.nan), copy=True)
    if x.ndim != 1 or y.ndim != 1 or min(len(x), len(y)) < 2:
        raise ValueError('x and y must be 1D coordinate vectors with at least two points')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.isinf(z).any():
        raise ValueError('Coordinates must be finite; infinity is not a missing-value encoding')
    if z.shape != (len(y), len(x)):
        raise ValueError('z must have shape (len(y), len(x)); no guessed transpose')
    for values, axis in [(x, 1), (y, 0)]:
        delta = np.diff(values)
        if np.all(delta < 0):
            if axis == 1: x, z = x[::-1].copy(), z[:, ::-1].copy()
            else: y, z = y[::-1].copy(), z[::-1, :].copy()
        elif not np.all(delta > 0):
            raise ValueError('Coordinate vectors must be strictly monotonic and unique')
    limits = np.asarray(limits, float)
    if limits.shape != (2,) or not np.isfinite(limits).all() or limits[0] >= limits[1]:
        raise ValueError('limits must contain two increasing finite values')
    finite = np.isfinite(z)
    if not finite.any() or ((z[finite] < limits[0]) | (z[finite] > limits[1])).any():
        raise ValueError('No finite data, or data fall outside explicit color limits')
    if center is None:
        norm = Normalize(*limits, clip=False)
    else:
        if not np.isscalar(center) or not np.isfinite(center) or not limits[0] < center < limits[1]:
            raise ValueError('center must lie strictly inside limits')
        norm = TwoSlopeNorm(center, *limits)
    for a in (x, y, z): a.flags.writeable = False
    return GridField(x, y, z, norm)


def scalar_field(ax, field, *, cmap=None, missing_color=None, levels=None):
    """Coordinate-aware pcolormesh; declared missing areas stay visible as NA.

    pcolormesh treats values as cell centers. Edge extrapolation is half of the
    adjacent coordinate interval, including nonuniform grids. For nodal finite
    element results, use the original mesh and nodal interpolation instead.
    """
    import matplotlib as mpl
    from project_style import colormap, role
    cm = (mpl.colormaps[cmap] if cmap is not None else colormap(diverging=hasattr(field.norm,'vcenter'))).with_extremes(bad=missing_color or role('missing'))
    mesh = ax.pcolormesh(field.x, field.y, np.ma.masked_invalid(field.z),
                         shading='nearest', cmap=cm, norm=field.norm,
                         linewidth=0, rasterized=True)
    if levels is not None:
        ax.contour(field.x, field.y, np.ma.masked_invalid(field.z), levels=levels,
                   colors='#FFFFFF', linewidths=.35, alpha=.7)
    return mesh


def field_surface(ax, field, *, cmap=None, elev=27, azim=-58,
                  box_aspect=(1, 1, .65), rasterized=True):
    """Render every grid vertex without silently decimating Matplotlib defaults.

    NA vertices break surface patches. Camera and box aspect change projection,
    never x/y/z data. Very large meshes require an explicit user-facing rendering
    strategy; rasterizing these faces keeps text and axes editable.
    """
    aspect = np.asarray(box_aspect, float)
    if aspect.shape != (3,) or not np.isfinite(aspect).all() or (aspect <= 0).any():
        raise ValueError('box_aspect needs three finite positive components')
    X, Y = np.meshgrid(field.x, field.y)
    from project_style import colormap
    if cmap is None: cmap = colormap(diverging=hasattr(field.norm,'vcenter'))
    artist = ax.plot_surface(X, Y, field.z, cmap=cmap, norm=field.norm,
        rcount=len(field.y), ccount=len(field.x), linewidth=0,
        antialiased=False, shade=False, rasterized=rasterized)
    ax.view_init(elev=elev, azim=azim)
    ax.set_box_aspect(aspect)
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.pane.set_facecolor((1, 1, 1, 0))
        axis.pane.set_edgecolor((.8, .83, .86, .3))
        axis._axinfo['grid'].update(color=(.72, .76, .80, .4), linewidth=.4)
    return artist


def volume_isosurface(ax, volume, *, spacing, level, origin=(0,0,0), color='#88569A',elev=25,azim=35,shade=True):
    """Render a true voxel-derived mesh, including overhangs/disconnected patches.

    Input order and spacing/origin are (z,y,x); displayed axes are x,y,z in the
    same physical units. Threshold is caller-specified, not an automatic cell
    detector. Marching cubes linearly interpolates the specified isovalue; no
    smoothing, component deletion, gap filling or mesh decimation is performed.
    Faces reaching a crop boundary may be open and are reported as such.
    """
    from skimage.measure import marching_cubes
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    a=np.asarray(volume);spacing=np.asarray(spacing,float);origin=np.asarray(origin,float)
    if a.ndim!=3 or min(a.shape)<2 or not np.isfinite(a).all():
        raise ValueError('Finite 3D voxel array with at least two samples per axis required')
    if spacing.shape!=(3,) or origin.shape!=(3,) or not np.isfinite([spacing,origin]).all() or (spacing<=0).any():
        raise ValueError('Explicit finite z,y,x spacing/origin required')
    if not np.isfinite(level) or not a.min()<level<a.max():raise ValueError('Explicit isovalue must lie inside the data range')
    vertices,faces,normals,values=marching_cubes(a,level=level,spacing=spacing,step_size=1,allow_degenerate=False)
    # Unit-spacing marching cubes can return float32; add large world origins
    # only after promotion so sub-voxel coordinates are not rounded away.
    vertices=vertices.astype(np.float64,copy=False)
    # A fraction-of-voxel tolerance is independent of world origin and whether
    # calibrated length is expressed, for example, in micrometres or metres.
    index_vertices=vertices/spacing
    touches=bool(np.any(np.isclose(index_vertices,0,rtol=0,atol=1e-5)) or
                 np.any(np.isclose(index_vertices,np.array(a.shape)-1,rtol=0,atol=1e-5)))
    vertices=vertices+origin;xyz=vertices[:,::-1]
    from matplotlib.colors import LightSource
    artist=Poly3DCollection(xyz[faces],facecolors=color,linewidth=0,rasterized=True,
        shade=shade,lightsource=LightSource(azdeg=315,altdeg=35))
    artist.set_edgecolor('none')
    ax.add_collection3d(artist)
    upper=origin+(np.array(a.shape)-1)*spacing
    for axis,start,stop in zip('zyx',origin,upper):getattr(ax,'set_'+axis+'lim')((start,stop))
    ax.set_box_aspect((upper-origin)[::-1]);ax.view_init(elev=elev,azim=azim)
    import hashlib
    report={'array_order':'zyx','spacing':spacing.tolist(),'origin':origin.tolist(),'level':float(level),
        'vertices':len(vertices),'triangles':len(faces),'touches_crop_boundary':touches,'boundary_tolerance_voxels':1e-5,
        'volume_sha256':hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest(),
        'vertex_sha256':hashlib.sha256(xyz.tobytes()).hexdigest(),'face_sha256':hashlib.sha256(faces.tobytes()).hexdigest(),
        'material_lighting':bool(shade),
        'boundary':'Isovalue surface, not validated segmentation or cell counts; color is material, not scalar intensity.'}
    return artist,report,xyz,faces
