// DeployBot Desktop - Frontend Logic
const { ipcRenderer } = require('electron');

// State management
let currentTab = 'deploy';
let isDeploying = false;
let deploymentProcess = null;

// ------------------------------------------------------------------ //
//  Servers
// ------------------------------------------------------------------ //
function loadServers() {
  return JSON.parse(localStorage.getItem('servers') || '[]');
}

function saveServer(config) {
  const servers = loadServers();
  const idx = servers.findIndex(s => s.host === config.host && s.username === config.username);
  const entry = { host: config.host, username: config.username, keyPath: config.keyPath || null, savedAt: new Date().toISOString() };
  if (idx >= 0) servers[idx] = entry; else servers.push(entry);
  localStorage.setItem('servers', JSON.stringify(servers));
  renderServers();
}

function deleteServer(host, username) {
  localStorage.setItem('servers', JSON.stringify(loadServers().filter(s => !(s.host === host && s.username === username))));
  renderServers();
}

function renderServers() {
  const grid = document.getElementById('servers-grid');
  const servers = loadServers();
  if (!servers.length) {
    grid.innerHTML = '<div class="server-card placeholder"><div class="server-info"><h4>No servers saved</h4><p>Auto-saved on successful connection test</p></div></div>';
    return;
  }
  grid.innerHTML = servers.map(s => `
    <div class="server-card">
      <div class="server-info">
        <h4 style="font-family:var(--font-mono);color:var(--accent-primary);margin-bottom:4px">${s.host}</h4>
        <p style="font-size:12px;color:var(--fg-secondary)">${s.username} &bull; ${s.keyPath ? 'SSH Key' : 'Password'}</p>
        <small style="color:var(--fg-tertiary);font-size:11px">Saved ${new Date(s.savedAt).toLocaleString()}</small>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <button class="btn btn-secondary" onclick="loadServerToForm('${s.host}','${s.username}','${s.keyPath||''}')" >LOAD</button>
        <button class="btn btn-ghost" onclick="deleteServer('${s.host}','${s.username}')">REMOVE</button>
      </div>
    </div>
  `).join('');
}

function loadServerToForm(host, username, keyPath) {
  document.getElementById('host').value = host;
  document.getElementById('username').value = username;
  if (keyPath) {
    document.getElementById('key-path').value = keyPath;
    document.getElementById('auth-method').value = 'key';
  } else {
    document.getElementById('auth-method').value = 'password';
  }
  toggleAuthMethod();
  switchTab('deploy');
}

// ------------------------------------------------------------------ //
//  Profiles
// ------------------------------------------------------------------ //
function loadProfiles() {
  return JSON.parse(localStorage.getItem('profiles') || '[]');
}

function saveProfile(name, config) {
  const profiles = loadProfiles();
  const idx = profiles.findIndex(p => p.name === name);
  const entry = { name, config, savedAt: new Date().toISOString() };
  if (idx >= 0) profiles[idx] = entry; else profiles.push(entry);
  localStorage.setItem('profiles', JSON.stringify(profiles));
  renderProfiles();
}

function deleteProfile(name) {
  localStorage.setItem('profiles', JSON.stringify(loadProfiles().filter(p => p.name !== name)));
  renderProfiles();
}

function renderProfiles() {
  const list = document.getElementById('profiles-list');
  const profiles = loadProfiles();
  if (!profiles.length) {
    list.innerHTML = '<div class="server-card placeholder"><div class="server-info"><h4>No profiles saved</h4><p>Fill in the deploy form and save it as a profile</p></div></div>';
    return;
  }
  list.innerHTML = profiles.map(p => `
    <div class="server-card">
      <div class="server-info">
        <h4 style="font-family:var(--font-mono);color:var(--accent-primary);margin-bottom:4px">${p.name}</h4>
        <p style="font-size:12px;color:var(--fg-secondary)">${p.config.host} &bull; ${p.config.domain} &bull; ${p.config.type}</p>
        <small style="color:var(--fg-tertiary);font-size:11px">Saved ${new Date(p.savedAt).toLocaleString()}</small>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <button class="btn btn-secondary" onclick="loadProfileToForm('${p.name}')">LOAD</button>
        <button class="btn btn-ghost" onclick="deleteProfile('${p.name}')">REMOVE</button>
      </div>
    </div>
  `).join('');
}

function loadProfileToForm(name) {
  const profile = loadProfiles().find(p => p.name === name);
  if (!profile) return;
  const c = profile.config;
  document.getElementById('host').value = c.host || '';
  document.getElementById('username').value = c.username || 'root';
  document.getElementById('domain').value = c.domain || '';
  document.getElementById('stack-type').value = c.type || 'node';
  document.getElementById('repo').value = c.repo || '';
  document.getElementById('branch').value = c.branch || 'main';
  document.getElementById('database').value = c.dbType || '';
  document.getElementById('enable-ssl').checked = c.enableSsl !== false;
  if (c.keyPath) {
    document.getElementById('key-path').value = c.keyPath;
    document.getElementById('auth-method').value = 'key';
  } else {
    document.getElementById('auth-method').value = 'password';
  }
  toggleAuthMethod();
  switchTab('deploy');
}

// DOM Elements
const elements = {
  // Navigation
  navItems: document.querySelectorAll('.nav-item'),
  tabContents: document.querySelectorAll('.tab-content'),
  
  // Forms
  deployForm: document.getElementById('deploy-form'),
  authMethod: document.getElementById('auth-method'),
  keyGroup: document.getElementById('key-group'),
  passwordGroup: document.getElementById('password-group'),
  browseKeyBtn: document.getElementById('browse-key'),
  testConnectionBtn: document.getElementById('test-connection'),
  connectionStatus: document.getElementById('connection-status'),
  deployBtn: document.getElementById('deploy-btn'),
  
  // Console
  console: document.getElementById('console-content'),
  clearConsoleBtn: document.getElementById('clear-console'),
  copyLogsBtn: document.getElementById('copy-logs'),
  
  // Modal
  progressModal: document.getElementById('progress-modal'),
  progressConsole: document.getElementById('progress-console'),
  progressStatus: document.getElementById('progress-status'),
  cancelDeployBtn: document.getElementById('cancel-deploy'),
  closeProgressBtn: document.getElementById('close-progress'),
  overlay: document.getElementById('overlay'),
  
  // Status
  status: document.getElementById('status')
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  initializeApp();
});

function initializeEventListeners() {
  // Navigation
  elements.navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      const tab = e.target.dataset.tab;
      if (tab) switchTab(tab);
    });
  });

  // Auth method toggle
  elements.authMethod.addEventListener('change', toggleAuthMethod);
  
  // Browse SSH key
  elements.browseKeyBtn.addEventListener('click', browseSSHKey);
  
  // Test connection
  elements.testConnectionBtn.addEventListener('click', testConnection);
  
  // Disconnect button
  document.getElementById('disconnect-btn').addEventListener('click', disconnectServer);
  
  // Deploy form
  elements.deployForm.addEventListener('submit', handleDeploy);
  
  // Console controls
  elements.clearConsoleBtn.addEventListener('click', clearConsole);
  elements.copyLogsBtn.addEventListener('click', copyLogs);

  // Profile save
  document.getElementById('save-profile-btn').addEventListener('click', () => {
    const name = document.getElementById('profile-name').value.trim();
    if (!name) return;
    const config = getDeployConfig();
    if (!config.host) { logConsole('ERROR', 'Fill in host before saving profile'); return; }
    saveProfile(name, config);
    document.getElementById('profile-name').value = '';
    logConsole('SUCCESS', `Profile "${name}" saved`);
  });
  
  // Modal controls
  elements.cancelDeployBtn.addEventListener('click', cancelDeployment);
  elements.closeProgressBtn.addEventListener('click', closeProgressModal);
  elements.overlay.addEventListener('click', closeProgressModal);
  
  // IPC listeners
  ipcRenderer.on('command-output', handleCommandOutput);
}

async function initializeApp() {
  try {
    const appInfo = await ipcRenderer.invoke('get-app-info');
    console.log('App initialized:', appInfo);

    renderServers();
    renderProfiles();
    updateStatus('READY');
    
    // Load default values
    const defaultKeyPath = getDefaultSSHKeyPath();
    if (defaultKeyPath) {
      document.getElementById('key-path').value = defaultKeyPath;
    }
  } catch (error) {
    console.error('Failed to initialize app:', error);
    updateStatus('ERROR');
    logConsole('ERROR', 'Failed to initialize application');
  }
}

function getDefaultSSHKeyPath() {
  const os = require('os');
  const path = require('path');
  return path.join(os.homedir(), '.ssh', 'id_rsa');
}

// Navigation
function switchTab(tabName) {
  if (isDeploying) return; // Prevent tab switching during deployment
  
  // Update nav items
  elements.navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tabName);
  });
  
  // Update tab contents
  elements.tabContents.forEach(content => {
    content.classList.toggle('active', content.id === `${tabName}-tab`);
  });
  
  currentTab = tabName;
}

// Authentication
function toggleAuthMethod() {
  const method = elements.authMethod.value;
  
  if (method === 'key') {
    elements.keyGroup.classList.remove('hidden');
    elements.passwordGroup.classList.add('hidden');
  } else {
    elements.keyGroup.classList.add('hidden');
    elements.passwordGroup.classList.remove('hidden');
  }
  
  // Clear connection status when auth method changes
  elements.connectionStatus.textContent = '';
  elements.connectionStatus.className = 'connection-status';
}

async function browseSSHKey() {
  try {
    const keyPath = await ipcRenderer.invoke('select-ssh-key');
    if (keyPath) {
      document.getElementById('key-path').value = keyPath;
    }
  } catch (error) {
    console.error('Failed to browse SSH key:', error);
    showConnectionStatus('Failed to browse files', 'error');
  }
}

async function testConnection() {
  const button = elements.testConnectionBtn;
  const disconnectBtn = document.getElementById('disconnect-btn');
  const loading = button.querySelector('.btn-loading');
  
  try {
    // Show loading
    loading.classList.remove('hidden');
    button.disabled = true;
    
    // Get server config
    const config = getServerConfig();
    if (!config.host) {
      throw new Error('Host is required');
    }
    
    // Test connection
    const result = await ipcRenderer.invoke('test-connection', config);
    
    if (result.success) {
      showConnectionStatus('Connection successful', 'success');
      logConsole('SUCCESS', `Connected to ${config.host}`);
      saveServer(config);
      disconnectBtn.classList.remove('hidden');
    } else {
      showConnectionStatus(result.message || 'Connection failed', 'error');
      logConsole('ERROR', `Failed to connect to ${config.host}: ${result.message}`);
      disconnectBtn.classList.add('hidden');
    }
    
  } catch (error) {
    console.error('Connection test failed:', error);
    showConnectionStatus(error.message, 'error');
    logConsole('ERROR', `Connection test failed: ${error.message}`);
    document.getElementById('disconnect-btn').classList.add('hidden');
  } finally {
    // Hide loading
    loading.classList.add('hidden');
    button.disabled = false;
  }
}

function disconnectServer() {
  const config = getServerConfig();
  showConnectionStatus('', '');
  document.getElementById('disconnect-btn').classList.add('hidden');
  logConsole('INFO', `Disconnected from ${config.host}`);
}

function getServerConfig() {
  const authMethod = elements.authMethod.value;
  
  return {
    host: document.getElementById('host').value.trim(),
    username: document.getElementById('username').value.trim() || 'root',
    password: authMethod === 'password' ? document.getElementById('password').value : null,
    keyPath: authMethod === 'key' ? document.getElementById('key-path').value.trim() : null
  };
}

function getDeployConfig() {
  const serverConfig = getServerConfig();
  
  return {
    ...serverConfig,
    domain: document.getElementById('domain').value.trim(),
    type: document.getElementById('stack-type').value,
    repo: document.getElementById('repo').value.trim() || null,
    branch: document.getElementById('branch').value.trim() || 'main',
    dbType: document.getElementById('database').value || null,
    enableSsl: document.getElementById('enable-ssl').checked,
    dryRun: document.getElementById('dry-run').checked
  };
}

function showConnectionStatus(message, type) {
  elements.connectionStatus.textContent = message;
  elements.connectionStatus.className = `connection-status ${type}`;
}

// Deployment
async function handleDeploy(e) {
  e.preventDefault();
  
  if (isDeploying) return;
  
  try {
    const config = getDeployConfig();
    
    // Validate required fields
    if (!config.host || !config.domain) {
      throw new Error('Host and domain are required');
    }
    
    // Start deployment
    startDeployment(config);
    
  } catch (error) {
    console.error('Deployment validation failed:', error);
    logConsole('ERROR', `Deployment failed: ${error.message}`);
  }
}

async function startDeployment(config) {
  isDeploying = true;
  
  // Update UI
  updateDeployButton(true);
  updateStatus('DEPLOYING');
  showProgressModal();
  clearProgressConsole();
  
  try {
    logConsole('INFO', `Starting deployment to ${config.host}...`);
    logProgressConsole('INFO', 'Initializing deployment...');
    
    // Execute deployment
    const result = await ipcRenderer.invoke('deploy', config);
    
    if (result.success) {
      logConsole('SUCCESS', `Deployment completed successfully!`);
      logProgressConsole('SUCCESS', 'Deployment completed successfully!');
      updateStatus('READY');
      showDeploymentSuccess();
    } else {
      logConsole('ERROR', `Deployment failed: ${result.stderr || 'Unknown error'}`);
      logProgressConsole('ERROR', `Deployment failed: ${result.stderr || 'Unknown error'}`);
      updateStatus('ERROR');
    }
    
  } catch (error) {
    console.error('Deployment error:', error);
    logConsole('ERROR', `Deployment error: ${error.message}`);
    logProgressConsole('ERROR', `Deployment error: ${error.message}`);
    updateStatus('ERROR');
  } finally {
    isDeploying = false;
    updateDeployButton(false);
    showCloseButton();
  }
}

function cancelDeployment() {
  if (deploymentProcess) {
    deploymentProcess.kill();
    deploymentProcess = null;
  }
  
  isDeploying = false;
  updateDeployButton(false);
  updateStatus('CANCELLED');
  logConsole('WARNING', 'Deployment cancelled by user');
  logProgressConsole('WARNING', 'Deployment cancelled by user');
  closeProgressModal();
}

function updateDeployButton(loading) {
  const button = elements.deployBtn;
  const loadingSpinner = button.querySelector('.btn-loading');
  const buttonText = button.querySelector('.btn-text');
  
  if (loading) {
    loadingSpinner.classList.remove('hidden');
    buttonText.textContent = 'DEPLOYING...';
    button.disabled = true;
  } else {
    loadingSpinner.classList.add('hidden');
    buttonText.textContent = 'DEPLOY';
    button.disabled = false;
  }
}

function showDeploymentSuccess() {
  elements.progressStatus.textContent = 'Deployment completed successfully!';
  elements.progressStatus.className = 'progress-status text-success';
}

function showCloseButton() {
  elements.cancelDeployBtn.classList.add('hidden');
  elements.closeProgressBtn.classList.remove('hidden');
}

// Modal management
function showProgressModal() {
  elements.progressModal.classList.remove('hidden');
  elements.overlay.classList.remove('hidden');
  elements.cancelDeployBtn.classList.remove('hidden');
  elements.closeProgressBtn.classList.add('hidden');
  elements.progressStatus.textContent = 'Initializing...';
  elements.progressStatus.className = 'progress-status';
}

function closeProgressModal() {
  elements.progressModal.classList.add('hidden');
  elements.overlay.classList.add('hidden');
}

// Console management
function logConsole(type, message) {
  const line = document.createElement('div');
  line.className = `console-line ${type.toLowerCase()}`;
  
  const prompt = document.createElement('span');
  prompt.className = 'prompt';
  prompt.textContent = `[${new Date().toLocaleTimeString()}]`;
  
  const text = document.createElement('span');
  text.className = 'text';
  text.textContent = message;
  
  line.appendChild(prompt);
  line.appendChild(text);
  
  elements.console.appendChild(line);
  elements.console.scrollTop = elements.console.scrollHeight;
}

function logProgressConsole(type, message) {
  const line = document.createElement('div');
  line.className = `console-line ${type.toLowerCase()}`;
  line.style.marginBottom = '4px';
  line.style.fontFamily = 'var(--font-mono)';
  line.style.fontSize = '11px';
  
  const prompt = document.createElement('span');
  prompt.style.color = 'var(--accent-primary)';
  prompt.style.fontWeight = '600';
  prompt.style.marginRight = '8px';
  prompt.textContent = `[${new Date().toLocaleTimeString()}]`;
  
  const text = document.createElement('span');
  text.textContent = message;
  
  // Apply type-specific styling
  switch (type.toUpperCase()) {
    case 'SUCCESS':
      text.style.color = 'var(--success)';
      break;
    case 'ERROR':
      text.style.color = 'var(--danger)';
      break;
    case 'WARNING':
      text.style.color = 'var(--warning)';
      break;
    default:
      text.style.color = 'var(--fg-primary)';
  }
  
  line.appendChild(prompt);
  line.appendChild(text);
  
  elements.progressConsole.appendChild(line);
  elements.progressConsole.scrollTop = elements.progressConsole.scrollHeight;
}

function copyLogs() {
  const lines = elements.console.querySelectorAll('.console-line');
  const text = Array.from(lines).map(line => {
    const prompt = line.querySelector('.prompt')?.textContent || '';
    const msg = line.querySelector('.text')?.textContent || '';
    return `${prompt} ${msg}`.trim();
  }).join('\n');

  navigator.clipboard.writeText(text).then(() => {
    const btn = elements.copyLogsBtn;
    btn.textContent = 'COPIED!';
    setTimeout(() => btn.textContent = 'COPY LOGS', 1500);
  });
}

function clearConsole() {
  elements.console.innerHTML = `
    <div class="console-line welcome">
      <span class="prompt">[DEPLOYBOT]</span>
      <span class="text">Ready for deployment commands...</span>
    </div>
  `;
}

function clearProgressConsole() {
  elements.progressConsole.innerHTML = '';
}

// Handle real-time command output
function handleCommandOutput(event, output) {
  const { type, data } = output;
  
  if (type === 'stdout') {
    logProgressConsole('INFO', data.trim());
    logConsole('INFO', data.trim());
  } else if (type === 'stderr') {
    logProgressConsole('ERROR', data.trim());
    logConsole('ERROR', data.trim());
  }
  
  // Update progress status
  if (data.includes('System Preparation')) {
    elements.progressStatus.textContent = 'Preparing system...';
  } else if (data.includes('Node.js')) {
    elements.progressStatus.textContent = 'Installing Node.js...';
  } else if (data.includes('Database')) {
    elements.progressStatus.textContent = 'Setting up database...';
  } else if (data.includes('Repository')) {
    elements.progressStatus.textContent = 'Cloning repository...';
  } else if (data.includes('Application')) {
    elements.progressStatus.textContent = 'Building application...';
  } else if (data.includes('NGINX')) {
    elements.progressStatus.textContent = 'Configuring NGINX...';
  } else if (data.includes('SSL')) {
    elements.progressStatus.textContent = 'Setting up SSL...';
  }
}

// Status management
function updateStatus(status) {
  elements.status.textContent = status;
  elements.status.className = 'status';
  
  switch (status) {
    case 'READY':
      elements.status.classList.add('text-success');
      break;
    case 'DEPLOYING':
      elements.status.classList.add('text-warning');
      break;
    case 'ERROR':
    case 'CANCELLED':
      elements.status.classList.add('text-danger');
      break;
  }
}

// Utility functions
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTimestamp() {
  return new Date().toLocaleTimeString();
}

// Error handling
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
  logConsole('ERROR', `Application error: ${event.error.message}`);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  logConsole('ERROR', `Promise rejection: ${event.reason}`);
});

// Export for debugging
if (process.env.NODE_ENV === 'development') {
  window.deployBot = {
    switchTab,
    testConnection,
    getServerConfig,
    getDeployConfig,
    logConsole,
    clearConsole
  };
}

// Expose functions globally for onclick handlers
window.loadServerToForm = loadServerToForm;
window.deleteServer = deleteServer;
window.loadProfileToForm = loadProfileToForm;
window.deleteProfile = deleteProfile;
