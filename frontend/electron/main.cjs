const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0a0a0a'
  });

  const isDev = process.env.NODE_ENV === 'development';

  if (isDev) {
    const projectRoot = path.join(__dirname, '../..');
    const venvPython = path.join(projectRoot, 'backend', '.venv', 'Scripts', 'python.exe');
    
    try {
      pythonProcess = spawn(venvPython, ['-m', 'uvicorn', 'backend.api:app', '--port', '8000', '--reload'], {
        cwd: projectRoot
      });
      pythonProcess.stdout?.on('data', (data) => console.log(`[Backend]: ${data}`));
      pythonProcess.stderr?.on('data', (data) => console.error(`[Backend Log]: ${data}`));
    } catch (e) {
      console.error("Failed to spawn Python dev server", e);
    }

    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // In production, spawn the bundled python backend
    pythonProcess = spawn(path.join(process.resourcesPath, 'backend', 'backend.exe'), [], {
      cwd: path.join(process.resourcesPath, 'backend')
    });
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
  if (pythonProcess) {
    pythonProcess.kill();
  }
});
