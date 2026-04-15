'use strict';
// Preload script — runs in the renderer process before any page scripts.
// With contextIsolation: true and nodeIntegration: false, this is the only
// place where Node APIs are accessible from the renderer side.
//
// Currently no Node APIs need to be bridged to the renderer because the app
// is a full Flask web application served over HTTP. This file is kept as a
// placeholder for future inter-process communication (IPC) if needed.

const { contextBridge } = require('electron');

// Expose a minimal version object so the web app can detect it's running
// inside Electron if required (optional).
contextBridge.exposeInMainWorld('electronBridge', {
  isElectron: true,
});