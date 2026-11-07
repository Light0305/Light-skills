const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");

ipcMain.handle("orders:list", async () => [
  { id: "A-100", total: 42.5 },
  { id: "A-101", total: 18.0 },
]);

function createWindow() {
  const window = new BrowserWindow({
    width: 900,
    height: 640,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  window.loadFile("index.html");
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
