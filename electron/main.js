'use strict';

const { app, BrowserWindow, shell, dialog } = require('electron');
const path  = require('path');
const fs    = require('fs');
const http  = require('http');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const USER_DATA  = path.join(app.getPath('appData'), 'ValveSizing');
const PORT_FILE  = path.join(USER_DATA, 'port.txt');
const POLL_MS    = 500;   // interval between port-file checks
const MAX_WAIT_S = 40;    // max seconds to wait for backend to start

let mainWindow    = null;
let backendProcess = null;
let backendPort   = null;

// ---------------------------------------------------------------------------
// Resolve path to the PyInstaller-bundled backend executable
// ---------------------------------------------------------------------------
function getBackendExe() {
  if (app.isPackaged) {
    const exeName = process.platform === 'win32'
      ? 'ValveSizingBackend.exe'
      : 'ValveSizingBackend';
    return path.join(process.resourcesPath, 'backend', exeName);
  }
  // Development: run the Python script directly
  return null;
}

// ---------------------------------------------------------------------------
// Start the Flask backend process
// ---------------------------------------------------------------------------
function startBackend() {
  return new Promise((resolve, reject) => {
    // Remove stale port file from a previous run
    try { fs.unlinkSync(PORT_FILE); } catch (_) {}

    const exePath = getBackendExe();

    if (exePath) {
      // Packaged: launch the compiled exe
      backendProcess = spawn(exePath, [], { detached: false, windowsHide: true });
    } else {
      // Development: launch via Python
      const projectRoot = path.join(__dirname, '..');
      backendProcess = spawn(
        process.platform === 'win32' ? 'python' : 'python3',
        ['electron_backend.py'],
        { cwd: projectRoot, detached: false }
      );
    }

    backendProcess.stdout.on('data', d => console.log('[backend]', d.toString().trim()));
    backendProcess.stderr.on('data', d => console.error('[backend]', d.toString().trim()));
    backendProcess.on('error', err => reject(new Error(`Backend spawn failed: ${err.message}`)));
    backendProcess.on('exit', code => {
      if (code !== 0 && code !== null) {
        console.error(`[backend] exited with code ${code}`);
      }
    });

    // Poll for port.txt written by electron_backend.py
    let elapsed = 0;
    const timer = setInterval(() => {
      elapsed += POLL_MS;
      try {
        const port = parseInt(fs.readFileSync(PORT_FILE, 'utf8').trim(), 10);
        if (port > 0) {
          clearInterval(timer);
          backendPort = port;
          resolve(port);
        }
      } catch (_) { /* file not ready yet */ }

      if (elapsed >= MAX_WAIT_S * 1000) {
        clearInterval(timer);
        reject(new Error(`Backend did not write port.txt within ${MAX_WAIT_S}s`));
      }
    }, POLL_MS);
  });
}

// ---------------------------------------------------------------------------
// Wait until Flask is actually accepting connections on the port
// ---------------------------------------------------------------------------
function waitForFlask(port, maxRetries = 60) {
  return new Promise((resolve, reject) => {
    let tries = 0;
    function attempt() {
      const req = http.get(`http://127.0.0.1:${port}/`, res => {
        res.resume();
        resolve(port);
      });
      req.on('error', () => {
        tries++;
        if (tries >= maxRetries) {
          reject(new Error('Flask did not respond in time'));
        } else {
          setTimeout(attempt, 500);
        }
      });
      req.setTimeout(1000, () => req.destroy());
    }
    attempt();
  });
}

// ---------------------------------------------------------------------------
// Create the main browser window
// ---------------------------------------------------------------------------
function createWindow(port) {
  mainWindow = new BrowserWindow({
    width:  1400,
    height: 900,
    minWidth:  900,
    minHeight: 600,
    title: 'Valve Sizing',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      sandbox:          true,
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${port}/`);

  // Open external links (e.g. Google OAuth redirect) in the default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(`http://127.0.0.1:${port}`)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(async () => {
  try {
    const port = await startBackend();
    await waitForFlask(port);
    createWindow(port);
  } catch (err) {
    console.error('[main] Startup failed:', err.message);
    dialog.showErrorBox(
      'Valve Sizing — Startup Error',
      `Could not start the application backend.\n\n${err.message}`
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  _killBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null && backendPort) createWindow(backendPort);
});

app.on('before-quit', _killBackend);

function _killBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
    backendProcess = null;
  }
}