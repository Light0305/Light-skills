"""Fixed-page mosaic layout with renderer-measured text and explicit panel roles.

Source ideas: Nature's evidence hierarchy, SciPilot's layout helpers, FigMirror's
panel-local geometry and figures4papers' shared legends/metric alignment.
No data, scale, font size, labels or scientific marks are changed by fitting.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt


class LayoutError(ValueError):
    pass


@dataclass
class Composition:
    figure: object
    axes: dict
    slots: dict
    panels: dict
    size_mm: tuple
    gap_mm: float
    grid: dict

    def fit(self, *, pad_mm=1.0, max_passes=8, tolerance_mm=.15):
        """Measure decorations at final size, then reserve aligned text corridors.

        Slots include axes decorations; plot_aspect means physical data rectangle
        W/H, not a data transform. min_plot_mm is a readability budget for the
        actual rendered data rectangle, including any equal-aspect shrinkage.
        Fail visibly when a page is too small; never silently shrink fonts.
        """
        fw, fh = self.size_mm
        if not isinstance(max_passes,int) or max_passes < 1 or not np.isfinite([pad_mm,tolerance_mm]).all() or min(pad_mm,tolerance_mm) < 0:
            raise ValueError('Positive pass count and finite nonnegative padding/tolerance required')
        previous = None
        converged = False
        for iteration in range(max_passes):
            for ax in self.axes.values():
                for manager in getattr(ax, '_light_chart_end_labels', []):
                    manager.update()
            self.figure.canvas.draw()
            renderer = self.figure.canvas.get_renderer()
            scale = 25.4 / self.figure.dpi
            pads = {}
            for key, ax in self.axes.items():
                b = ax.get_window_extent(renderer)
                t = ax.get_tightbbox(renderer)
                pads[key] = np.maximum(0, [b.x0-t.x0, t.y1-b.y1, t.x1-b.x1, b.y0-t.y0]) * scale + pad_mm
            # Match the data edges of panels sharing the same slot edges. This
            # preserves comparison alignment without forcing unequal roles equal.
            aligned = {key: p.copy() for key, p in pads.items()}
            for side, coord in enumerate([0, 1, 2, 3]):
                for key, slot in self.slots.items():
                    peers = [k for k, s in self.slots.items() if abs(s[coord]-slot[coord]) < 1e-6]
                    aligned[key][side] = max(pads[k][side] for k in peers)
            if self.grid['balance_columns']:
                a = self.grid['mosaic']
                nc = a.shape[1]
                columns = {key:int(np.where(a == key)[1][0]) for key in self.axes}
                lp = np.array([max((aligned[k][0] for k in self.axes if columns[k] == col), default=0) for col in range(nc)])
                rp = np.array([max((aligned[k][2] for k in self.axes if columns[k] == col), default=0) for col in range(nc)])
                margins = self.grid['margins']
                remaining = fw-margins[0]-margins[2]-self.gap_mm*(nc-1)-lp.sum()-rp.sum()
                if remaining <= 0:
                    raise LayoutError('Column labels exhaust physical width')
                wr = self.grid['width_ratios']
                widths = remaining*wr/wr.sum()+lp+rp
                xs = margins[0]+np.r_[0, np.cumsum(widths+self.gap_mm)[:-1]]
                for key, slot in self.slots.items():
                    col = columns[key]
                    slot[0], slot[2] = float(xs[col]), float(xs[col]+widths[col])
            rects = {}
            for key, (left, top, right, bottom) in self.slots.items():
                p = aligned[key]
                x, y, w, h = left+p[0], top+p[1], right-left-p[0]-p[2], bottom-top-p[1]-p[3]
                if w <= 0 or h <= 0:
                    raise LayoutError(f'{key}: labels exhaust slot; enlarge page or restructure panels')
                aspect = self.panels.get(key, {}).get('plot_aspect')
                if aspect is not None:
                    if not np.isfinite(aspect) or aspect <= 0:
                        raise LayoutError('plot_aspect must be positive and finite')
                    if w/h > aspect:
                        x += (w-h*aspect)/2; w = h*aspect
                    else:
                        y += (h-w/aspect)/2; h = w/aspect
                minimum = self.panels.get(key, {}).get('min_plot_mm', [16, 14])
                if np.asarray(minimum).shape != (2,) or not np.isfinite(minimum).all() or min(minimum) <= 0:
                    raise ValueError('min_plot_mm needs two positive finite dimensions')
                if w < minimum[0] or h < minimum[1]:
                    raise LayoutError(f'{key}: data rectangle {w:.1f}×{h:.1f} mm below {minimum}; enlarge or split')
                rects[key] = [x, y, w, h]
            # Comparable image acquisitions can share physical mm per source
            # pixel. ROI magnification is a separate, explicitly chosen mode.
            image_groups = {}
            for key, options in self.panels.items():
                group=options.get('equal_pixel_group') or options.get('equal_unit_group')
                if group:
                    shape = np.asarray(options.get('image_shape') if options.get('equal_pixel_group') else options.get('data_span'),float)
                    if shape.shape != (2,) or not np.isfinite(shape).all() or (shape<=0).any():
                        raise LayoutError('Equal-scale groups need positive image_shape or data_span [height,width]')
                    mode='pixel' if options.get('equal_pixel_group') else 'unit'
                    image_groups.setdefault((mode,group),[]).append((key,shape))
            for members in image_groups.values():
                scale_px = min(min(rects[k][2]/shape[1],rects[k][3]/shape[0]) for k,shape in members)
                for key,(rows,cols) in members:
                    r=rects[key]
                    w,h=cols*scale_px,rows*scale_px
                    r[0]+=(r[2]-w)/2; r[1]+=(r[3]-h)/2; r[2:]=[w,h]
                    if any(v<m for v,m in zip((w,h),self.panels[key].get('min_plot_mm',[16,14]))):
                        raise LayoutError(f'{key}: equal-scale group falls below physical budget')
            # Marginals/risk strips retain the main panel's coordinate edges.
            # They can become smaller inside their own slot, never invade peers.
            for key, options in self.panels.items():
                for kind, indices in [('share_x_with', (0,2)), ('share_y_with', (1,3))]:
                    if options.get(kind):
                        parent = options[kind]
                        if parent not in rects or parent == key:
                            raise LayoutError(f'{key}: invalid alignment owner {parent}')
                        start, length = indices
                        r, target = rects[key], rects[parent]
                        if target[start] < r[start]-tolerance_mm or target[start]+target[length] > r[start]+r[length]+tolerance_mm:
                            raise LayoutError(f'{key}: shared coordinates exceed available text corridor')
                        r[start], r[length] = target[start], target[length]
            for key, (x,y,w,h) in rects.items():
                self.axes[key].set_position([x/fw, 1-(y+h)/fh, w/fw, h/fh])
            current = np.asarray(list(rects.values()))
            if previous is not None and np.max(np.abs(current-previous)) < tolerance_mm:
                converged = True
                break
            previous = current
        self.figure.canvas.draw()
        violations = []
        scale = 25.4 / self.figure.dpi
        renderer = self.figure.canvas.get_renderer()
        actual_rects = {}
        for key, ax in self.axes.items():
            # Matplotlib's adjustable='box' applies the data aspect at draw
            # time, potentially shrinking one dimension inside the allocated
            # rectangle. Check and report that actual box, not its reservation.
            b = ax.get_window_extent(renderer)
            actual = [b.x0*scale, fh-b.y1*scale, b.width*scale, b.height*scale]
            actual_rects[key] = actual
            minimum = self.panels.get(key, {}).get('min_plot_mm', [16, 14])
            if any(value < required-1e-8 for value, required in zip(actual[2:], minimum)):
                raise LayoutError(f'{key}: actual rendered data rectangle {actual[2]:.1f}×{actual[3]:.1f} mm '
                                  f'below {minimum}; enlarge the page or change the panel layout')
            t = ax.get_tightbbox(renderer)
            extent = np.array([t.x0*scale, fh-t.y1*scale, t.x1*scale, fh-t.y0*scale])
            s = self.slots[key]
            if np.any(np.array([s[0]-extent[0], s[1]-extent[1], extent[2]-s[2], extent[3]-s[3]]) > tolerance_mm):
                violations.append(key)
        if not converged or violations:
            raise LayoutError(f'Layout did not settle inside declared slots: {violations}; change geometry, not font size')
        report = {'size_mm': list(self.size_mm), 'passes': iteration+1, 'converged': True,
                  'slots_mm': self.slots, 'plot_rectangles_mm': actual_rects,
                  'allocated_plot_rectangles_mm': rects,
                  'panels': self.panels, 'text_padding_mm': {k: v.tolist() for k, v in aligned.items()},
                  'boundary': 'Geometry only; evidence roles and visual quality require actual review.'}
        self.figure._light_chart_composition = report
        return report

    def labels(self, labels=None, *, fontsize=9):
        """Panel letters anchored to slots, outside data and shared across rows."""
        keys = [k for k in self.axes if self.panels.get(k,{}).get('panel_label',True)]
        labels = labels or list('abcdefghijklmnopqrstuvwxyz')[:len(keys)]
        if len(labels) != len(keys):
            raise ValueError('Exactly one label per panel required')
        fw, fh = self.size_mm
        return [self.figure.text(self.slots[k][0]/fw, 1-self.slots[k][1]/fh,
                    label, ha='left', va='bottom', fontsize=fontsize, fontweight='bold')
                for k, label in zip(keys, labels)]


def compose(size_mm, mosaic, *, panels=None, width_ratios=None, height_ratios=None,
            margins_mm=(4, 7, 4, 4), gap_mm=4, balance_columns=False):
    """Create rectangular spanning slots. '.' is intentional empty space.

    Ratios are explicit evidence/shape choices, not inferred from panel count.
    Panels may specify role, question, min_plot_mm and plot_aspect metadata.
    Coordinates in slots are [left, top, right, bottom] in physical millimetres.
    balance_columns budgets decoration widths before applying width_ratios to
    DATA widths; it supports panels that stay within one column (row spans OK).
    """
    size = np.asarray(size_mm, float)
    a = np.asarray(mosaic, dtype=object)
    margin = np.asarray(margins_mm, float)
    if size.shape != (2,) or not np.isfinite(size).all() or (size <= 0).any():
        raise ValueError('Positive finite page dimensions required')
    if a.ndim != 2 or not a.size or margin.shape != (4,) or not np.isfinite(margin).all() or (margin < 0).any():
        raise ValueError('Rectangular mosaic and four nonnegative finite margins required')
    if not all(isinstance(k,str) and k for k in a.flat) or all(k == '.' for k in a.flat):
        raise ValueError('Mosaic requires named panels and optional dot placeholders')
    if set(panels or {}) - (set(a.flat)-{'.'}):
        raise ValueError('Panel options name a panel absent from the mosaic')
    if not np.isfinite(gap_mm) or gap_mm < 0:
        raise ValueError('Nonnegative finite gap required')
    nr, nc = a.shape
    wr = np.asarray(width_ratios if width_ratios is not None else np.ones(nc), float)
    hr = np.asarray(height_ratios if height_ratios is not None else np.ones(nr), float)
    if wr.shape != (nc,) or hr.shape != (nr,) or not np.isfinite(wr).all() or not np.isfinite(hr).all() or (wr <= 0).any() or (hr <= 0).any():
        raise ValueError('Positive ratios must match mosaic dimensions')
    available = size - [margin[0]+margin[2]+gap_mm*(nc-1), margin[1]+margin[3]+gap_mm*(nr-1)]
    if (available <= 0).any():
        raise LayoutError('Margins and gutters exhaust page')
    widths, heights = wr/wr.sum()*available[0], hr/hr.sum()*available[1]
    xs = margin[0]+np.r_[0, np.cumsum(widths+gap_mm)[:-1]]
    ys = margin[1]+np.r_[0, np.cumsum(heights+gap_mm)[:-1]]
    fig = plt.figure(figsize=size/25.4, layout=None)
    axes, slots = {}, {}
    try:
        for key in dict.fromkeys(a.flat):
            if key == '.':
                continue
            rr, cc = np.where(a == key)
            r0, r1, c0, c1 = rr.min(), rr.max(), cc.min(), cc.max()
            if not (a[r0:r1+1, c0:c1+1] == key).all():
                raise LayoutError(f'{key}: spanning panels must be rectangles')
            if balance_columns and c0 != c1:
                raise LayoutError('Balanced data columns require each panel to stay within one column')
            left, top = xs[c0], ys[r0]
            right, bottom = xs[c1]+widths[c1], ys[r1]+heights[r1]
            slots[key] = [float(v) for v in [left, top, right, bottom]]
            projection = (panels or {}).get(key,{}).get('projection')
            if projection not in (None,'3d'):
                raise LayoutError('Supported projections are 2D and 3d')
            axes[key] = fig.add_axes([left/size[0], 1-bottom/size[1], (right-left)/size[0], (bottom-top)/size[1]], label=key,projection=projection)
    except BaseException:
        plt.close(fig)
        raise
    return Composition(fig, axes, slots, panels or {}, tuple(size), gap_mm,
        {'mosaic':a, 'width_ratios':wr, 'margins':margin, 'balance_columns':balance_columns})


class _EndLabels:
    def __init__(self, ax, lines, annotations, minimum_gap_pt):
        self.ax, self.lines, self.annotations = ax, lines, annotations
        self.minimum_gap_pt = minimum_gap_pt

    def update(self):
        ax = self.ax
        bounds = ax.get_window_extent()
        gap = self.minimum_gap_pt*ax.figure.dpi/72
        pad = gap/2
        if gap*(len(self.lines)-1)+2*pad > bounds.height:
            raise LayoutError('Line-end labels exceed vertical capacity; facet or reserve a legend')
        target = np.array([ax.transData.transform(line.get_xydata()[-1])[1] for line in self.lines])
        order = np.argsort(target, kind='stable')
        positions = np.clip(target[order],bounds.y0+pad,bounds.y1-pad)
        for i in range(1,len(positions)):
            positions[i] = max(positions[i],positions[i-1]+gap)
        if len(positions):
            positions[-1] = min(positions[-1],bounds.y1-pad)
        for i in range(len(positions)-2,-1,-1):
            positions[i] = min(positions[i],positions[i+1]-gap)
        for i, pos in zip(order, positions):
            self.annotations[i].xy = self.lines[i].get_xydata()[-1]
            self.annotations[i].set_position((1.025,(pos-bounds.y0)/bounds.height))


def label_line_ends(ax, lines=None, *, minimum_gap_pt=11, fontsize=None):
    """Place nonoverlapping direct labels with leaders to unchanged endpoints.

    Kept live during Composition.fit so spacing stays in final physical points.
    Use only when series identity at the end is meaningful; no end is moved and
    no curve, observation or interval is hidden to make labels fit.
    """
    if not np.isfinite(minimum_gap_pt) or minimum_gap_pt <= 0:
        raise ValueError('Positive finite label spacing required')
    chosen = list(lines) if lines is not None else [line for line in ax.lines
        if line.get_label() and not line.get_label().startswith('_')]
    if not chosen:
        raise ValueError('Named lines required')
    notes = []
    for line in chosen:
        xy = line.get_xydata()
        if not len(xy) or not np.isfinite(xy[-1]).all():
            raise ValueError('Each line needs a finite endpoint')
        notes.append(ax.annotate(line.get_label(),xy=xy[-1],xycoords='data',
            xytext=(1.025,.5),textcoords='axes fraction',ha='left',va='center',
            fontsize=fontsize, color=line.get_color(),annotation_clip=False,
            arrowprops={'arrowstyle':'-','color':line.get_color(),'linewidth':.55,
                        'shrinkA':2,'shrinkB':2,'connectionstyle':'arc3,rad=0'}))
    manager = _EndLabels(ax,chosen,notes,minimum_gap_pt)
    if not hasattr(ax,'_light_chart_end_labels'):
        ax._light_chart_end_labels=[]
    ax._light_chart_end_labels.append(manager)
    manager.update()
    return notes
