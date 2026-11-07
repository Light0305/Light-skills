"""Generate ten MIT-licensed, explicitly synthetic visual-review examples.

Every plotted value is generated here. These are demonstrations of encodings and
geometry, not measurements, benchmark results, significance tests or paper figures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': .7,
        'savefig.facecolor': 'white', 'pdf.fonttype': 42})
    rng = np.random.default_rng(207)
    records = []

    def save(fig, name, arrays, caption):
        # Explicit margins are part of each encoding, never an image-only crop.
        fig.savefig(output/f'{name}.png', dpi=170)
        fig.savefig(output/f'{name}.pdf', metadata={'CreationDate': None, 'ModDate': None})
        np.savez_compressed(output/f'{name}.npz', **arrays)
        (output/f'{name}.md').write_text('# '+name+'\n\nSYNTHETIC DEMONSTRATION — no experimental claims.\n\n'+caption+'\n\nData: '+name+'.npz. Generator: scripts/generate_review_examples.py; NumPy RNG seed 207.\n', encoding='utf-8')
        records.append({'id': name, 'preview': f'{name}.png', 'vector': f'{name}.pdf',
                        'data': f'{name}.npz', 'caption': f'{name}.md', 'data_origin': 'synthetic',
                        'license': 'MIT', 'sha256': hashlib.sha256((output/f'{name}.png').read_bytes()).hexdigest()})
        plt.close(fig)

    before = rng.normal(5, .9, 16)
    after = before + rng.normal(.6, .4, 16)
    fig, ax = plt.subplots(figsize=(4.3, 3.3), layout='constrained')
    ax.plot([0, 1], np.stack([before, after]), color='#9ca7b0', lw=.8, zorder=1)
    ax.scatter(np.zeros(16), before, color='#315b7c', s=18, zorder=2)
    ax.scatter(np.ones(16), after, color='#b85c3b', s=18, zorder=2)
    ax.set(xticks=[0, 1], xticklabels=['Condition A', 'Condition B'], ylabel='Generated value (a.u.)', xlim=(-.3, 1.3))
    save(fig, '01-paired', {'before': before, 'after': after}, 'Sixteen generated pairs. Lines retain pair identity; no hypothesis test or population inference is supplied.')

    x = np.linspace(0, 10, 70)
    observations = np.sin(x[None, :]/2) + rng.normal(0, .25, (12, len(x)))
    mean, sd = observations.mean(axis=0), observations.std(axis=0, ddof=1)
    fig, ax = plt.subplots(figsize=(4.6, 3.2), layout='constrained')
    ax.fill_between(x, mean-sd, mean+sd, color='#d7e4ed', label='Generated mean ± SD')
    ax.plot(x, mean, color='#315b7c', lw=1.4)
    ax.set(xlabel='Generated coordinate (a.u.)', ylabel='Generated signal (a.u.)')
    ax.legend(frameon=False, fontsize=8)
    save(fig, '02-trajectory-band', {'x': x, 'observations': observations}, 'Twelve generated trajectories. The band is sample SD, not a confidence interval; these are not independent observations from a real experiment.')

    rows, cols = np.arange(12), np.arange(8)
    matrix = np.sin(rows[:, None]/2)*np.cos(cols[None, :]/3)
    fig, ax = plt.subplots(figsize=(4.1, 3.5), layout='constrained')
    art = ax.imshow(matrix, cmap='RdBu_r', norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1), aspect='auto')
    ax.set(xlabel='Generated condition', ylabel='Generated feature', xticks=cols, yticks=rows)
    fig.colorbar(art, ax=ax, label='Analytical value (a.u.)', shrink=.82)
    save(fig, '03-centered-matrix', {'matrix': matrix}, 'An analytical 12×8 matrix with a fixed zero-centered color scale. No gene, sample, clustering or significance interpretation is intended.')

    samples = rng.multivariate_normal([0, 0], [[1, .55], [.55, .8]], size=550)
    fig = plt.figure(figsize=(4.4, 3.9), layout='constrained')
    grid = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4])
    main = fig.add_subplot(grid[1, 0]); top = fig.add_subplot(grid[0, 0], sharex=main); right = fig.add_subplot(grid[1, 1], sharey=main)
    main.scatter(*samples.T, s=7, alpha=.35, c='#315b7c', edgecolors='none')
    top.hist(samples[:, 0], bins=22, color='#315b7c'); right.hist(samples[:, 1], bins=22, orientation='horizontal', color='#b85c3b')
    top.tick_params(labelbottom=False); right.tick_params(labelleft=False)
    main.set(xlabel='Generated x (a.u.)', ylabel='Generated y (a.u.)')
    top.set(ylabel='Count'); right.set(xlabel='Count')
    save(fig, '04-joint-distribution', {'samples': samples}, '550 draws from a specified bivariate normal distribution; marginal bars show counts of the same generated points. These panels are complementary views of one sample, not independent evidence.')

    xy = np.linspace(-2.2, 2.2, 85); xx, yy = np.meshgrid(xy, xy)
    zz = np.cos(2*np.hypot(xx, yy))*np.exp(-.3*(xx**2+yy**2))
    fig = plt.figure(figsize=(5.6, 4)); ax = fig.add_axes([.03, .14, .73, .80], projection='3d')
    surface = ax.plot_surface(xx, yy, zz, cmap='viridis', linewidth=0, antialiased=True, vmin=-1, vmax=1)
    ax.set(xlabel='x (a.u.)', ylabel='y (a.u.)', zlabel='z (a.u.)'); ax.view_init(28, -54)
    ax.set_box_aspect((1, 1, .6))
    fig.colorbar(surface, cax=fig.add_axes([.88, .25, .025, .48]), label='Analytical z')
    save(fig, '05-damped-surface', {'x': xx, 'y': yy, 'z': zz}, 'Analytical damped radial surface. Vertical display proportion is 0.6 relative to equal x/y extents; no physical surface or measured field is implied.')

    saddle = .25*(xx**2-yy**2)
    fig = plt.figure(figsize=(7.8, 3.8))
    a = fig.add_axes([.04, .14, .38, .77], projection='3d'); b = fig.add_axes([.59, .18, .27, .70])
    a.plot_surface(xx, yy, saddle, cmap='RdBu_r', vmin=-1.3, vmax=1.3, linewidth=0)
    a.set(xlabel='x', ylabel='y', zlabel='z'); a.set_box_aspect((1, 1, .6))
    field = b.contourf(xx, yy, saddle, levels=np.linspace(-1.3, 1.3, 15), cmap='RdBu_r', extend='both')
    b.set(xlabel='x (a.u.)', ylabel='y (a.u.)', aspect='equal')
    fig.colorbar(field, cax=fig.add_axes([.89, .22, .018, .62]), label='Analytical z')
    save(fig, '06-surface-and-contours', {'x': xx, 'y': yy, 'z': saddle}, 'The same analytical saddle shown as a surface and contour field. Colors share limits. The projection is another representation of the same values.')

    broken = np.where(np.abs(xx) < .28, np.nan, zz)
    fig = plt.figure(figsize=(4.8, 3.7), layout='constrained'); ax = fig.add_subplot(projection='3d')
    ax.plot_surface(xx, yy, broken, color='#8fb1be', linewidth=0, antialiased=True)
    ax.set(xlabel='x (a.u.)', ylabel='y (a.u.)', zlabel='z (a.u.)'); ax.set_box_aspect((1, 1, .6))
    save(fig, '07-masked-surface', {'x': xx, 'y': yy, 'z': broken}, 'The analytical radial surface is deliberately undefined for |x|<0.28. Missing values are masked; no bridge or zero-valued patch is inserted. Fixed surface color is decorative, not a scalar mapping.')

    u, v = np.meshgrid(np.linspace(0, 2*np.pi, 65), np.linspace(0, np.pi, 35))
    sphere = np.stack([np.cos(u)*np.sin(v), np.sin(u)*np.sin(v), np.cos(v)])
    fig = plt.figure(figsize=(4.8, 3.7), layout='constrained'); ax = fig.add_subplot(projection='3d')
    ax.plot_surface(sphere[0]-.95, .6*sphere[1], .75*sphere[2], color='#4d7e96', linewidth=0)
    ax.plot_surface(.65*sphere[0]+1.05, .8*sphere[1], .9*sphere[2], color='#c38463', linewidth=0)
    ax.set(xlabel='x', ylabel='y', zlabel='z', xlim=(-2, 2), ylim=(-1, 1), zlim=(-1, 1)); ax.set_box_aspect((2, 1, 1))
    save(fig, '08-separated-objects', {'unit_sphere_mesh': sphere}, 'Two separate parametric ellipsoids in arbitrary units. This is an analytical mesh example, not a segmented volume; visible components must not be interpreted as biological objects.')

    t = np.linspace(0, 6*np.pi, 420)
    helix = np.stack([np.cos(t), np.sin(t), t/(3*np.pi)-1])
    fig = plt.figure(figsize=(7.2, 3.7)); a = fig.add_axes([.04, .16, .38, .77], projection='3d'); b = fig.add_axes([.62, .19, .34, .72])
    a.plot(*helix, color='#315b7c', lw=1.3); a.set(xlabel='x', ylabel='y', zlabel='z'); a.set_box_aspect((1, 1, 1))
    b.plot(helix[0], helix[2], color='#315b7c', lw=1.2); b.set(xlabel='x (a.u.)', ylabel='z (a.u.)')
    save(fig, '09-trajectory-and-projection', {'t': t, 'xyz': helix}, 'A parametric helix and its x–z projection. No time or motion measurement is supplied; t is an analytical parameter. Projection overlap does not imply repeated independent observations.')

    y = np.linspace(-1, 1, 100); layers = np.array([np.sin(3*y+phase) for phase in (0, .7, 1.4, 2.1)])
    fig = plt.figure(figsize=(4.8, 3.7), layout='constrained'); ax = fig.add_subplot(projection='3d')
    colors = ['#315b7c', '#547f8f', '#9a8d70', '#b85c3b']
    for index, values in enumerate(layers):
        ax.plot(y, np.full_like(y, index), values, color=colors[index], lw=1.4)
    ax.set(xlabel='x (a.u.)', ylabel='Display layer', zlabel='Analytical z', yticks=range(4)); ax.set_box_aspect((1.2, 1, .7))
    save(fig, '10-layered-curves', {'x': y, 'z': layers, 'display_layer': np.arange(4)}, 'Four phase-shifted analytical curves separated by display layer. Layer spacing is categorical placement, not measured distance. Colors identify layers rather than magnitude.')

    manifest = {'origin': 'Independently authored Light-Science synthetic examples', 'seed': 207,
                'license': 'MIT', 'scientific_evidence': False, 'examples': records}
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (output/'README.md').write_text('# Visual review examples\n\nTen independently generated synthetic examples, not experimental evidence. Each image has analytical/generated input (`.npz`), a separate caption and a vector PDF. Rebuild with `python scripts/generate_review_examples.py --out assets/examples/visual-review`. MIT; no FigMirror source image or paper screenshot is used.\n', encoding='utf-8')
    print(json.dumps({'examples': len(records), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=str(Path(__file__).resolve().parents[1]/'assets/examples/visual-review'))
    generate(parser.parse_args().out)
