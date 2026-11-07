# Electron demo fixture

A minimal Electron source tree used by the `L4_APP` benchmark case. It contains
the three boundaries the L4 lane cares about:

- main process entry (`main.js`);
- preload bridge (`preload.js`);
- renderer (`index.html`).

It is deliberately small and local. The benchmark only routes the target; it does
not launch Electron or execute the app.
