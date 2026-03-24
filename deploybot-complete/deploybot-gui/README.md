# 🖥️ DeployBot Desktop

**Visual deployment automation with an industrial terminal aesthetic.**

Transform your server deployment workflow with a sleek desktop interface that wraps the powerful DeployBot CLI.

![DeployBot Desktop](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Electron](https://img.shields.io/badge/Electron-28.0.0-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎯 **Visual Deployment Wizard**
- Clean form-based configuration
- Real-time connection testing
- Stack type selection (Node, Remix, Laravel, Static)
- Database integration (MySQL/PostgreSQL)
- SSL certificate automation

### 🖥️ **Server Management**
- Multiple server connections
- Health monitoring dashboard
- Live system status checks
- SSH key management

### 📋 **Real-time Console**
- Live deployment progress
- Command output streaming
- Colored log levels
- Execution history

### 📁 **Profile Management**
- Save deployment configurations
- Quick profile switching
- Encrypted credential storage
- Reusable templates

### 🎨 **Industrial Terminal Aesthetic**
- Dark theme with terminal green accents
- JetBrains Mono typography
- ASCII art branding
- Brutalist/utilitarian design

---

## 🚀 Quick Start

### Prerequisites
- **Node.js 16+** — [Download here](https://nodejs.org/)
- **Python 3.8+** — [Download here](https://www.python.org/downloads/)
- **Git** — For repository cloning

### 1. Install
```bash
# Make setup script executable
chmod +x setup.sh

# Run installation
./setup.sh
```

### 2. Launch
```bash
npm start
```

### 3. Deploy
1. Open the **DEPLOY** tab
2. Enter your server credentials
3. Click **TEST CONNECTION**
4. Configure your application settings
5. Hit **DEPLOY** and watch the magic! ✨

---

## 📋 Supported Deployment Stacks

| Stack | Description | Features |
|-------|-------------|----------|
| **Node.js** | Standard Node apps | NVM, PM2, NGINX proxy |
| **Remix** | Full-stack React framework | Shopify integration, Prisma support |
| **Next.js** | React production framework | SSG/SSR, API routes |
| **Express** | Minimal Node web framework | Custom middleware, APIs |
| **Laravel** | PHP web application framework | Composer, Artisan, PHP-FPM |
| **Static** | HTML/CSS/JS sites | Gzip, caching, CDN-ready |
| **React** | SPA with build step | Webpack, production optimization |
| **Vue** | Progressive JavaScript framework | CLI builds, PWA support |

---

## 🔧 Architecture

```
┌─────────────────────────┐
│   Electron Frontend    │
│   (HTML/CSS/JS)        │
├─────────────────────────┤
│   Main Process         │
│   (Node.js IPC)        │
├─────────────────────────┤
│   Python CLI Bridge    │
│   (spawn processes)    │
├─────────────────────────┤
│   DeployBot Core       │
│   (SSH automation)     │
└─────────────────────────┘
```

### Key Components
- **`main.js`** — Electron main process, window management
- **`src/index.html`** — Application interface
- **`src/renderer.js`** — Frontend logic, IPC communication
- **`src/styles.css`** — Industrial terminal aesthetic
- **`../deploybot/`** — Python CLI backend (required)

---

## 🖱️ GUI Features

### **Deploy Tab**
- **Server Connection**
  - Host/IP input with validation
  - Username (defaults to 'root')
  - Authentication: SSH key or password
  - Connection testing with live feedback
- **Application Config**
  - Domain name validation
  - Stack type selection
  - Git repository integration
  - Database selection
  - SSL toggle (Let's Encrypt)
- **Deploy Actions**
  - Dry run preview mode
  - One-click deployment
  - Real-time progress tracking

### **Servers Tab**
- Server health monitoring
- System information display
- Quick server actions
- Connection status indicators

### **Logs Tab** 
- Real-time console output
- Color-coded log levels
- Command execution history
- Scrollable terminal interface

### **Profiles Tab**
- Save deployment configurations
- Quick profile loading
- Encrypted credential storage
- Profile management

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Switch to Deploy tab |
| `Ctrl+2` | Switch to Servers tab |
| `Ctrl+3` | Switch to Logs tab |
| `Ctrl+4` | Switch to Profiles tab |
| `Ctrl+T` | Test connection |
| `Ctrl+D` | Deploy |
| `Ctrl+L` | Clear console |
| `Escape` | Close modal |

---

## 🏗️ Development

### Prerequisites
- Node.js 16+
- Python 3.8+
- DeployBot CLI in `../deploybot/`

### Setup
```bash
# Clone and setup
git clone <repo>
cd deploybot-gui
npm install

# Install Python CLI dependencies
cd ../deploybot
pip install -r requirements.txt

# Return to GUI
cd ../deploybot-gui
```

### Development Mode
```bash
# Launch with dev tools
npm run dev

# Watch for changes (separate terminal)
npm run watch
```

### Building
```bash
# Build for current platform
npm run build

# Build for all platforms
npm run dist

# Package without distribution
npm run pack
```

### Project Structure
```
deploybot-gui/
├── src/
│   ├── index.html          # Main application window
│   ├── styles.css          # Industrial terminal theme
│   └── renderer.js         # Frontend logic
├── assets/
│   ├── icon.ico           # Windows icon
│   ├── icon.icns          # macOS icon
│   └── icon.png           # Linux icon
├── main.js                # Electron main process
├── package.json           # Dependencies & build config
└── setup.sh              # Installation script
```

---

## 🔒 Security

### Credential Storage
- **AES-256 encryption** via Fernet
- **PBKDF2-SHA256** key derivation (480k iterations)
- **Local-only storage** in `~/.deploybot/vault.enc`
- **Memory-safe** credential handling

### SSH Security
- **Key-based auth preferred** over passwords
- **No plaintext credential logging**
- **Secure process spawning** for CLI execution
- **Connection validation** before deployment

---

## 🎨 Theming

The interface uses an **industrial terminal aesthetic**:

### Color Palette
- **Background**: Dark grays (`#0a0a0a`, `#1a1a1a`, `#2a2a2a`)
- **Accent**: Terminal green (`#00ff00`, `#00cc00`, `#008800`)
- **Text**: High contrast whites and greens
- **Status**: Color-coded (green=success, red=error, amber=warning)

### Typography
- **Display**: JetBrains Mono (ASCII art, console output)
- **Interface**: Inter (forms, buttons, labels)
- **Aesthetic**: Uppercase labels, letter spacing, industrial feel

### Animations
- **Subtle hover states** on interactive elements
- **Loading spinners** during operations
- **Status pulsing** for live indicators
- **Smooth transitions** (0.15s ease)

---

## 🐛 Troubleshooting

### Common Issues

**"Python not found"**
```bash
# Ensure Python is in PATH
which python3
# or
which python
```

**"DeployBot CLI not found"**
```bash
# Ensure CLI is in parent directory
ls ../deploybot/cli.py
```

**"Node dependencies failed"**
```bash
# Clear cache and reinstall
npm cache clean --force
rm -rf node_modules
npm install
```

**"Connection test fails"**
- Verify server IP/hostname
- Check SSH key permissions (`chmod 600 ~/.ssh/id_rsa`)
- Ensure server allows SSH connections
- Test manually: `ssh user@server`

### Debug Mode
```bash
# Launch with debug console
npm run dev

# Enable verbose logging
DEBUG=* npm start
```

### Log Locations
- **Application logs**: `~/.deploybot/logs/`
- **Electron logs**: Developer Console (`F12`)
- **CLI output**: Real-time in Logs tab

---

## 📦 Distribution

### Build Targets
- **Windows**: NSIS installer (`.exe`)
- **macOS**: DMG package (`.dmg`) 
- **Linux**: AppImage (`.AppImage`)

### Build Process
```bash
# All platforms (requires docker for cross-platform)
npm run dist

# Current platform only
npm run build

# Unsigned builds (for testing)
npm run build -- --publish=never
```

### Bundle Contents
- Electron application
- DeployBot Python CLI
- Required Node modules
- Platform-specific icons
- Auto-updater support

---

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- **JavaScript**: ESLint + Prettier
- **CSS**: BEM methodology
- **HTML**: Semantic structure
- **Python**: CLI follows existing patterns

### Testing
```bash
# Run tests
npm test

# UI testing
npm run test:ui

# Integration testing
npm run test:integration
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🆘 Support

- **Documentation**: Check the main [DeployBot README](../deploybot/README.md)
- **Issues**: [GitHub Issues](https://github.com/you/deploybot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/you/deploybot/discussions)

---

**Built with ❤️ for developers who love beautiful, functional tools.**
