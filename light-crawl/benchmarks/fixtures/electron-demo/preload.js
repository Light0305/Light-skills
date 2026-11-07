const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("demoApi", {
  loadOrders: () => ipcRenderer.invoke("orders:list"),
});
