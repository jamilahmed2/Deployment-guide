# 🚀 DeployBot

**Production-grade SSH deployment automation for developers.**

Transforms your server from bare Ubuntu to a fully deployed, SSL-secured application — with one command.

---

## Architecture

```
deploybot/
├── cli.py                    # Typer CLI — entry point for all commands
├── core/
│   ├── ssh_manager.py        # SSH connection, exec, SFTP (Paramiko)
│   ├── command_engine.py     # Step orchestration, retry, rollback, Rich TUI
│   ├── deployment_engine.py  # Full pipeline builder per stack
│   ├── template_engine.py    # Jinja2: NGINX, .env, PM2 configs
│   ├── credential_store.py   # AES-encrypted local vault (Fernet)
│   └── logger.py             # Rich + file logging
├── workflows/
│   ├── nodejs.yaml           # Config-driven Node.js workflow
│   └── laravel.yaml          # Config-driven Laravel workflow
├── requirements.txt
└── setup.py
```

---

## Quick Start

### Install

```bash
# Clone DeployBot
git clone https://github.com/you/deploybot && cd deploybot

# Install dependencies
pip install -r requirements.txt

# Or install as CLI tool
pip install -e .
```

### Deploy a Remix/Node app (fully automated)

```bash
python cli.py deploy \
  --host 1.2.3.4 \
  --domain app.example.com \
  --type remix \
  --repo https://github.com/you/your-app \
  --db mysql \
  --ssl
```

### Guided wizard (beginner-friendly)

```bash
python cli.py wizard
```

### Manual SSH shell

```bash
python cli.py manual --host 1.2.3.4 --user root --key ~/.ssh/id_rsa
```

### Check server status

```bash
python cli.py server check --host 1.2.3.4 --user root
```

### Tail logs

```bash
python cli.py server logs --host 1.2.3.4 --app my-app --lines 100
```

---

## Supported Stacks

| Stack      | NGINX Template | DB Support | Build Step | Process Manager |
|------------|---------------|------------|------------|-----------------|
| `node`     | Reverse proxy  | MySQL/PG   | npm build  | PM2             |
| `remix`    | Reverse proxy  | MySQL/PG   | npm build  | PM2             |
| `next`     | Reverse proxy  | MySQL/PG   | npm build  | PM2             |
| `express`  | Reverse proxy  | MySQL/PG   | optional   | PM2             |
| `laravel`  | PHP-FPM        | MySQL      | composer   | PHP-FPM         |
| `static`   | Static files   | —          | optional   | NGINX           |
| `react`    | Static files   | —          | npm build  | NGINX           |
| `vue`      | Static files   | —          | npm build  | NGINX           |

---

## Deployment Pipeline

Every deployment runs these ordered phases:

```
1. System Prep      → apt update, install curl/git/unzip
2. Runtime Install  → Node.js via NVM  /  PHP + Composer
3. Database         → MySQL or PostgreSQL (optional)
4. Clone Repo       → git clone or git pull
5. App Config       → Write .env from template
6. Build & Start    → npm install + build + PM2 start
7. NGINX            → Render config template → enable site
8. SSL              → Certbot --nginx (Let's Encrypt)
```

---

## Security Model

- Credentials are **never stored in plaintext**
- Vault file (`~/.deploybot/vault.enc`) uses **AES-128-CBC + HMAC-SHA256** (Fernet)
- Master password is derived via **PBKDF2-SHA256** with 480,000 iterations
- SSH keys take priority over passwords
- Sensitive output is never logged to file

---

## Environment Variables

| Variable                    | Description                        |
|-----------------------------|------------------------------------|
| `DEPLOYBOT_MASTER_PASSWORD` | Skip vault password prompt         |

---

## Extending DeployBot

### Add a new stack

1. Add a new workflow YAML in `workflows/`
2. Add a NGINX template in `core/template_engine.py`
3. Add a pipeline method in `deployment_engine.py`

### Add a new command

```python
@app.command()
def my_command(...):
    """Description shown in help."""
    ...
```

---

## Dependencies

| Package       | Purpose                        |
|---------------|-------------------------------|
| paramiko      | SSH connections + SFTP         |
| typer         | CLI framework                  |
| rich          | Terminal UI + progress         |
| jinja2        | Config template rendering      |
| cryptography  | AES vault encryption           |
| questionary   | Interactive prompts            |
| pyyaml        | Workflow YAML parsing          |

---

## Roadmap

- [ ] Docker-based deployments
- [ ] Multi-server orchestration
- [ ] CI/CD webhook integration
- [ ] Electron GUI wrapper
- [ ] Plugin system for custom stacks
- [ ] Deployment history dashboard
