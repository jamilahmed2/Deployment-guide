const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Keep a global reference of the window object
let mainWindow;
let isDev = process.argv.includes('--dev');

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    titleBarStyle: 'default',
    show: false, // Don't show until ready
    icon: getIconPath()
  });

  // Load the app
  mainWindow.loadFile('src/index.html');

  // Show when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.webContents.setZoomFactor(1.0);
    mainWindow.webContents.setZoomLevel(0);
    if (isDev) {
      mainWindow.webContents.openDevTools();
    }
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Cleanup on app quit
  mainWindow.on('close', (e) => {
    // Allow window to close
    console.log('Window closing, cleaning up...');
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  // Disable zoom
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.control && (input.key === '+' || input.key === '-' || input.key === '=')) {
      event.preventDefault();
    }
  });
}

function getIconPath() {
  if (process.platform === 'darwin') return path.join(__dirname, 'assets/icon.icns');
  if (process.platform === 'win32') return path.join(__dirname, 'assets/icon.ico');
  return path.join(__dirname, 'assets/icon.png');
}

// Get Python CLI path
function getPythonCliPath() {
  // Always use the deploybot folder relative to deploybot-gui
  const cliPath = path.join(__dirname, '..', 'deploybot', 'cli.py');
  console.log('CLI path:', cliPath);
  if (!fs.existsSync(cliPath)) {
    console.error('CLI not found at:', cliPath);
  }
  return cliPath;
}

// App event handlers
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  console.log('All windows closed, quitting app...');
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Get Python executable path
function getPythonPath() {
  if (process.platform === 'win32') {
    const candidates = [
      path.normalize(path.join(require('os').homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe')),
      path.normalize(path.join(require('os').homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe')),
      path.normalize(path.join(require('os').homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe')),
      path.normalize(path.join(require('os').homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe')),
    ];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        console.log('Found Python at:', candidate);
        return candidate;
      }
    }
    console.error('Python not found in any candidate location');
  }
  return 'python3';
}

// IPC handlers for Python CLI integration
function executeCommand(command, args = []) {
  return new Promise((resolve, reject) => {
    const cliPath = getPythonCliPath();
    const pythonPath = getPythonPath();
    
    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python not found at: ${pythonPath}`));
      return;
    }
    
    console.log('Executing:', pythonPath, [cliPath, command, ...args]);

    const fullArgs = [cliPath, command, ...args];
    
    const proc = spawn(pythonPath, fullArgs, {
      cwd: path.dirname(cliPath),
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONLEGACYWINDOWSSTDIO: '0',
        PATH: process.env.PATH
      }
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      mainWindow?.webContents.send('command-output', { type: 'stdout', data: output });
    });

    proc.stderr.on('data', (data) => {
      const output = data.toString();
      stderr += output;
      mainWindow?.webContents.send('command-output', { type: 'stderr', data: output });
    });

    proc.on('close', (code) => {
      resolve({ code, stdout: stdout.trim(), stderr: stderr.trim(), success: code === 0 });
    });

    proc.on('error', (err) => {
      console.error('Spawn error:', err);
      console.error('Python path:', pythonPath);
      console.error('CLI path:', cliPath);
      console.error('Args:', fullArgs);
      reject(new Error(`Failed to start Python process: ${err.message}`));
    });
  });
}

ipcMain.handle('execute-command', async (event, command, args = []) => {
  return executeCommand(command, args);
});

// Deploy command with live progress
ipcMain.handle('deploy', async (event, config) => {
  const args = [
    '--host', config.host,
    '--domain', config.domain,
    '--type', config.type,
    '--user', config.username || 'root',
  ];

  if (config.password) args.push('--password', config.password);
  if (config.keyPath) args.push('--key', config.keyPath);
  if (config.repo) args.push('--repo', config.repo);
  if (config.branch && config.branch !== 'main') args.push('--branch', config.branch);
  if (config.dbType) args.push('--db', config.dbType);
  if (config.enableSsl) args.push('--ssl');
  if (config.dryRun) args.push('--dry-run');

  return await executeCommand('deploy', args);
});

// Server check
ipcMain.handle('server-check', async (event, serverConfig) => {
  const args = [
    '--host', serverConfig.host,
    '--user', serverConfig.username || 'root'
  ];
  
  if (serverConfig.password) args.push('--password', serverConfig.password);
  if (serverConfig.keyPath) args.push('--key', serverConfig.keyPath);

  return await executeCommand('server', ['check', ...args]);
});

// Test connection
ipcMain.handle('test-connection', async (event, serverConfig) => {
  const args = [
    '--host', serverConfig.host,
    '--user', serverConfig.username || 'root'
  ];

  if (serverConfig.password) args.push('--password', serverConfig.password);
  if (serverConfig.keyPath) args.push('--key', serverConfig.keyPath);

  try {
    const result = await executeCommand('server', ['check', ...args]);
    return { success: result.success, message: result.success ? 'Connection successful' : result.stderr };
  } catch (err) {
    return { success: false, message: err.message };
  }
});

// File dialog for SSH key selection
ipcMain.handle('select-ssh-key', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select SSH Private Key',
    defaultPath: path.join(require('os').homedir(), '.ssh'),
    filters: [
      { name: 'SSH Keys', extensions: ['*'] },
      { name: 'All Files', extensions: ['*'] }
    ],
    properties: ['openFile']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// App info
ipcMain.handle('get-app-info', () => {
  return {
    version: app.getVersion(),
    platform: process.platform,
    isDev: isDev
  };
});
