"""
deployment_engine.py — Full workflow orchestration.
Builds step groups for each supported stack and runs them via CommandEngine.
"""

from __future__ import annotations
import secrets
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from .ssh_manager import SSHManager
from .command_engine import CommandEngine, Step, StepGroup
from .template_engine import TemplateEngine

console = Console()


@dataclass
class DeploymentConfig:
    # Server
    host: str
    username: str = "root"
    password: Optional[str] = None
    key_path: Optional[str] = None
    port: int = 22

    # Project
    domain: str = ""
    project_type: str = "node"         # node | remix | laravel | static | next
    repo_url: Optional[str] = None
    project_path: str = ""             # auto-derived if empty
    branch: str = "main"
    app_name: str = ""                 # auto-derived from domain

    # App config
    app_port: int = 3000
    node_version: str = "lts"          # lts | 20 | 18 etc.
    php_version: str = "8.2"
    db_type: Optional[str] = None      # mysql | postgres | none
    db_name: str = ""
    db_password: str = ""

    # Env vars to inject into .env
    env_vars: dict = field(default_factory=dict)

    # Deployment flags
    enable_ssl: bool = True
    use_pm2: bool = True
    run_migrations: bool = False
    run_setup: bool = False            # npm run setup (Prisma etc.)

    # Control
    dry_run: bool = False
    interactive: bool = False
    skip_nginx: bool = False
    skip_ssl: bool = False

    def __post_init__(self):
        if not self.app_name:
            self.app_name = self.domain.replace(".", "-").replace("*", "wildcard")
        if not self.project_path:
            self.project_path = f"/var/www/html/{self.app_name}"


class DeploymentEngine:
    """
    Top-level orchestrator. Converts a DeploymentConfig into
    ordered StepGroups and executes them via CommandEngine.
    """

    def __init__(self, ssh: SSHManager, config: DeploymentConfig):
        self.ssh = ssh
        self.cfg = config
        self.engine = CommandEngine(ssh, dry_run=config.dry_run, interactive=config.interactive)
        self.tpl = TemplateEngine()

    # ------------------------------------------------------------------ #
    #  Public entry points                                                  #
    # ------------------------------------------------------------------ #

    def deploy(self) -> bool:
        """Run the full automated deployment pipeline."""
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]🚀 DeployBot — Auto Deploy[/bold cyan]\n"
            f"  Host  : [white]{self.cfg.username}@{self.cfg.host}[/white]\n"
            f"  Domain: [white]{self.cfg.domain}[/white]\n"
            f"  Stack : [white]{self.cfg.project_type.upper()}[/white]\n"
            f"  Path  : [white]{self.cfg.project_path}[/white]",
            border_style="cyan",
        ))

        groups = self._build_pipeline()
        ok = self.engine.run_groups(groups)
        self.engine.print_summary()

        if ok:
            console.print()
            console.print(Panel(
                f"[bold green]✅ Deployment Complete![/bold green]\n\n"
                f"  🌐  https://{self.cfg.domain}\n"
                f"  📁  {self.cfg.project_path}\n"
                f"  📋  pm2 logs {self.cfg.app_name}",
                border_style="green",
                title="Success",
            ))
        return ok

    # ------------------------------------------------------------------ #
    #  Pipeline builder — dispatches by stack                              #
    # ------------------------------------------------------------------ #

    def _build_pipeline(self) -> list[StepGroup]:
        pipeline: list[StepGroup] = []

        # Always: system prep
        pipeline.append(self._group_system_prep())

        stack = self.cfg.project_type.lower()

        if stack in ("node", "remix", "express", "next"):
            pipeline.extend(self._pipeline_node())
        elif stack in ("laravel", "php"):
            pipeline.extend(self._pipeline_laravel())
        elif stack in ("static", "html", "react", "vue"):
            pipeline.extend(self._pipeline_static())
        else:
            # Fallback: generic node
            pipeline.extend(self._pipeline_node())

        # Always: NGINX + SSL
        if not self.cfg.skip_nginx:
            pipeline.append(self._group_nginx())
        if self.cfg.enable_ssl and not self.cfg.skip_ssl:
            pipeline.append(self._group_ssl())

        return pipeline

    # ------------------------------------------------------------------ #
    #  Shared step groups                                                   #
    # ------------------------------------------------------------------ #

    def _group_system_prep(self) -> StepGroup:
        return StepGroup(
            name="System Preparation",
            icon="🖥️",
            description="Update system packages and install base dependencies",
            steps=[
                Step(
                    name="Update apt",
                    command="apt-get update -qq",
                    sudo=True,
                    timeout=120,
                    error_hint="Check your internet connection and apt sources.",
                ),
                Step(
                    name="Install base packages",
                    command="apt-get install -y -qq curl wget git unzip software-properties-common ufw",
                    sudo=True,
                    timeout=180,
                ),
                Step(
                    name="Create project directory",
                    command=f"mkdir -p {self.cfg.project_path}",
                    sudo=True,
                ),
                Step(
                    name="Set directory ownership",
                    command=f"chown -R {self.cfg.username}:{self.cfg.username} {self.cfg.project_path}",
                    sudo=True,
                    critical=False,
                ),
            ],
        )

    def _group_nginx(self) -> StepGroup:
        nginx_conf = self.tpl.nginx_for_stack(
            self.cfg.project_type,
            {
                "domain": self.cfg.domain,
                "port": self.cfg.app_port,
                "project_path": self.cfg.project_path,
                "php_version": self.cfg.php_version,
            },
        )
        conf_path = f"/etc/nginx/sites-available/{self.cfg.domain}"
        enabled_path = f"/etc/nginx/sites-enabled/{self.cfg.domain}"

        # Write nginx config via SFTP (not as a step command)
        def write_nginx_config():
            if not self.cfg.dry_run:
                self.ssh.write_remote_file(conf_path, nginx_conf)

        return StepGroup(
            name="NGINX Configuration",
            icon="🌐",
            description=f"Set up reverse proxy for {self.cfg.domain}",
            steps=[
                Step(
                    name="Install NGINX",
                    command="apt-get install -y nginx",
                    sudo=True,
                    skip_on_success_pattern="already",
                    timeout=120,
                ),
                Step(
                    name="Write NGINX config",
                    command=f"cat > {conf_path} << 'NGINX_EOF'\n{nginx_conf}\nNGINX_EOF",
                    sudo=True,
                    error_hint="Check /etc/nginx/sites-available permissions.",
                ),
                Step(
                    name="Enable site",
                    command=f"ln -sf {conf_path} {enabled_path}",
                    sudo=True,
                ),
                Step(
                    name="Remove default site",
                    command="rm -f /etc/nginx/sites-enabled/default",
                    sudo=True,
                    critical=False,
                ),
                Step(
                    name="Test NGINX config",
                    command="nginx -t",
                    sudo=True,
                    error_hint="Syntax error in nginx config — check the generated file.",
                ),
                Step(
                    name="Restart NGINX",
                    command="systemctl restart nginx && systemctl enable nginx",
                    sudo=True,
                ),
            ],
        )

    def _group_ssl(self) -> StepGroup:
        return StepGroup(
            name="SSL Certificate (Let's Encrypt)",
            icon="🔒",
            description=f"Issue and configure HTTPS for {self.cfg.domain}",
            steps=[
                Step(
                    name="Install Certbot",
                    command="apt-get install -y certbot python3-certbot-nginx",
                    sudo=True,
                    timeout=120,
                ),
                Step(
                    name="Issue SSL certificate",
                    command=(
                        f"certbot --nginx -d {self.cfg.domain} "
                        f"--non-interactive --agree-tos "
                        f"--email admin@{self.cfg.domain} "
                        f"--redirect"
                    ),
                    sudo=True,
                    timeout=120,
                    error_hint=(
                        "DNS must be pointed to this server. "
                        "Check: dig +short " + self.cfg.domain
                    ),
                    retries=2,
                ),
                Step(
                    name="Set up auto-renewal",
                    command="systemctl enable certbot.timer && systemctl start certbot.timer",
                    sudo=True,
                    critical=False,
                ),
            ],
        )

    # ------------------------------------------------------------------ #
    #  Node.js / Remix pipeline                                             #
    # ------------------------------------------------------------------ #

    def _pipeline_node(self) -> list[StepGroup]:
        groups = [self._group_install_node()]

        if self.cfg.db_type == "mysql":
            groups.append(self._group_install_mysql())
        elif self.cfg.db_type == "postgres":
            groups.append(self._group_install_postgres())

        if self.cfg.repo_url:
            groups.append(self._group_clone_repo())

        groups.append(self._group_node_app())
        return groups

    def _group_install_node(self) -> StepGroup:
        ver = self.cfg.node_version
        nvm_install = (
            f"curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash && "
            f"export NVM_DIR=\"$HOME/.nvm\" && "
            f". \"$NVM_DIR/nvm.sh\" && "
            f"nvm install {ver} && nvm use {ver} && nvm alias default {ver}"
        )
        return StepGroup(
            name="Node.js Installation",
            icon="📦",
            description="Install Node.js via NVM",
            steps=[
                Step(
                    name="Install NVM",
                    command=nvm_install,
                    timeout=300,
                    stream=True,
                    skip_on_success_pattern="already installed",
                    error_hint="Check network access to raw.githubusercontent.com",
                ),
                Step(
                    name="Verify NVM installation",
                    command="export NVM_DIR=\"$HOME/.nvm\" && . \"$NVM_DIR/nvm.sh\" && nvm --version",
                    timeout=30,
                    critical=False,
                ),
                Step(
                    name="Verify Node.js installation",
                    command="export NVM_DIR=\"$HOME/.nvm\" && . \"$NVM_DIR/nvm.sh\" && node -v && npm -v",
                    timeout=30,
                ),
                Step(
                    name="Install PM2 globally",
                    command=(
                        "export NVM_DIR=\"$HOME/.nvm\" && . \"$NVM_DIR/nvm.sh\" && "
                        "npm install -g pm2"
                    ),
                    skip_on_success_pattern="already installed",
                    timeout=120,
                ),
            ],
        )

    def _group_install_mysql(self) -> StepGroup:
        pw = self.cfg.db_password or secrets.token_urlsafe(16)
        return StepGroup(
            name="MySQL Server",
            icon="🗄️",
            description="Install and configure MySQL",
            steps=[
                Step(
                    name="Install MySQL",
                    command="apt-get install -y mysql-server",
                    sudo=True, timeout=180,
                ),
                Step(
                    name="Start & enable MySQL",
                    command="systemctl start mysql && systemctl enable mysql",
                    sudo=True,
                ),
                Step(
                    name="Verify MySQL status",
                    command="systemctl status mysql --no-pager",
                    sudo=True,
                    critical=False,
                ),
                Step(
                    name="Create database and set root password",
                    command=(
                        f"mysql -u root -e \""
                        f"CREATE DATABASE IF NOT EXISTS {self.cfg.db_name}; "
                        f"ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '{pw}'; "
                        f"FLUSH PRIVILEGES;\""
                    ),
                    sudo=True,
                    error_hint="MySQL may already have a root password set. Use --db-password flag.",
                ),
            ],
        )

    def _group_install_postgres(self) -> StepGroup:
        pw = self.cfg.db_password or secrets.token_urlsafe(16)
        return StepGroup(
            name="PostgreSQL Server",
            icon="🐘",
            description="Install and configure PostgreSQL",
            steps=[
                Step(
                    name="Install PostgreSQL",
                    command="apt-get install -y postgresql postgresql-contrib",
                    sudo=True, timeout=180,
                ),
                Step(
                    name="Start & enable PostgreSQL",
                    command="systemctl start postgresql && systemctl enable postgresql",
                    sudo=True,
                ),
                Step(
                    name="Verify PostgreSQL status",
                    command="systemctl status postgresql --no-pager",
                    sudo=True,
                    critical=False,
                ),
                Step(
                    name="Create database and set password",
                    command=(
                        f"sudo -u postgres psql -c \""
                        f"CREATE DATABASE {self.cfg.db_name}; "
                        f"ALTER USER postgres PASSWORD '{pw}';\""
                    ),
                    sudo=True, critical=False,
                ),
            ],
        )

    def _group_clone_repo(self) -> StepGroup:
        return StepGroup(
            name="Repository",
            icon="📥",
            description=f"Clone {self.cfg.repo_url}",
            steps=[
                Step(
                    name="Clone repo",
                    command=(
                        f"git clone --branch {self.cfg.branch} "
                        f"{self.cfg.repo_url} {self.cfg.project_path} 2>/dev/null || "
                        f"(cd {self.cfg.project_path} && git pull origin {self.cfg.branch})"
                    ),
                    timeout=300,
                    error_hint="Check repo URL and SSH key access for private repos.",
                ),
            ],
        )

    def _group_node_app(self) -> StepGroup:
        env_content = self.tpl.env_for_stack(self.cfg.project_type, {
            "domain": self.cfg.domain,
            "port": self.cfg.app_port,
            "database_type": self.cfg.db_type,
            "db_password": self.cfg.db_password,
            "db_name": self.cfg.db_name,
            "custom_vars": self.cfg.env_vars,
            "session_secret": secrets.token_hex(32),
        })

        nvm_prefix = (
            "export NVM_DIR=\"$HOME/.nvm\" && . \"$NVM_DIR/nvm.sh\" && "
        )
        pm2_cmd = (
            f"pm2 describe {self.cfg.app_name} > /dev/null 2>&1 && "
            f"pm2 restart {self.cfg.app_name} || "
            f"pm2 start npm --name \"{self.cfg.app_name}\" -- run start"
        )

        steps = [
            Step(
                name="Write .env file",
                command=f"cat > {self.cfg.project_path}/.env << 'ENV_EOF'\n{env_content}\nENV_EOF",
                error_hint="Check write permissions on project directory.",
            ),
            Step(
                name="Install npm dependencies",
                command=f"cd {self.cfg.project_path} && {nvm_prefix}npm install --production",
                timeout=300,
                error_hint="Check package.json exists and npm registry is reachable.",
            ),
        ]

        if self.cfg.run_setup:
            steps.append(Step(
                name="Run setup (Prisma/migrations)",
                command=f"cd {self.cfg.project_path} && {nvm_prefix}npm run setup",
                timeout=120,
                critical=False,
            ))

        steps.append(Step(
            name="Build application",
            command=f"cd {self.cfg.project_path} && {nvm_prefix}npm run build",
            timeout=300,
            error_hint="Build failed — check build script in package.json.",
        ))

        if self.cfg.use_pm2:
            steps.extend([
                Step(
                    name="Start with PM2",
                    command=f"cd {self.cfg.project_path} && {nvm_prefix}{pm2_cmd}",
                    timeout=60,
                ),
                Step(
                    name="Save PM2 config",
                    command=f"{nvm_prefix}pm2 save && pm2 startup | tail -1 | bash",
                    sudo=True,
                    critical=False,
                ),
                Step(
                    name="Create log directory",
                    command=f"mkdir -p /var/log/{self.cfg.app_name}",
                    sudo=True, critical=False,
                ),
            ])

        return StepGroup(
            name="Application Deployment",
            icon="🚀",
            description="Install, build, and start the application",
            steps=steps,
        )

    # ------------------------------------------------------------------ #
    #  Laravel pipeline                                                     #
    # ------------------------------------------------------------------ #

    def _pipeline_laravel(self) -> list[StepGroup]:
        groups = [self._group_install_php()]
        if self.cfg.repo_url:
            groups.append(self._group_clone_repo())
        groups.append(self._group_laravel_app())
        return groups

    def _group_install_php(self) -> StepGroup:
        v = self.cfg.php_version
        return StepGroup(
            name="PHP Installation",
            icon="🐘",
            description=f"Install PHP {v} and extensions",
            steps=[
                Step(
                    name="Add PHP PPA",
                    command="add-apt-repository -y ppa:ondrej/php && apt-get update -qq",
                    sudo=True, timeout=120,
                ),
                Step(
                    name="Install PHP + extensions",
                    command=(
                        f"apt-get install -y php{v} php{v}-fpm php{v}-mysql php{v}-xml "
                        f"php{v}-curl php{v}-mbstring php{v}-zip php{v}-gd composer"
                    ),
                    sudo=True, timeout=300,
                ),
                Step(
                    name="Start PHP-FPM",
                    command=f"systemctl start php{v}-fpm && systemctl enable php{v}-fpm",
                    sudo=True,
                ),
            ],
        )

    def _group_laravel_app(self) -> StepGroup:
        p = self.cfg.project_path
        return StepGroup(
            name="Laravel Application",
            icon="🎼",
            description="Composer install, env, key, migrate",
            steps=[
                Step(name="Composer install", command=f"cd {p} && composer install --no-dev --optimize-autoloader", timeout=300),
                Step(name="Set .env", command=f"cp {p}/.env.example {p}/.env", critical=False),
                Step(name="Generate app key", command=f"cd {p} && php artisan key:generate"),
                Step(name="Run migrations", command=f"cd {p} && php artisan migrate --force", critical=False),
                Step(name="Cache config", command=f"cd {p} && php artisan config:cache && php artisan route:cache"),
                Step(name="Set permissions", command=f"chown -R www-data:www-data {p}/storage {p}/bootstrap/cache", sudo=True),
            ],
        )

    # ------------------------------------------------------------------ #
    #  Static pipeline                                                      #
    # ------------------------------------------------------------------ #

    def _pipeline_static(self) -> list[StepGroup]:
        groups = []
        if self.cfg.repo_url:
            groups.append(self._group_clone_repo())
        # Optional build step for React/Vue
        if self.cfg.project_type.lower() in ("react", "vue", "next"):
            groups.append(self._group_static_build())
        return groups

    def _group_static_build(self) -> StepGroup:
        nvm_prefix = "export NVM_DIR=\"$HOME/.nvm\" && . \"$NVM_DIR/nvm.sh\" && "
        return StepGroup(
            name="Static Build",
            icon="⚡",
            description="Install and build frontend assets",
            steps=[
                Step(name="Install NVM + Node", command=f"curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash && {nvm_prefix}nvm install lts", timeout=300),
                Step(name="npm install", command=f"cd {self.cfg.project_path} && {nvm_prefix}npm install", timeout=300),
                Step(name="npm build", command=f"cd {self.cfg.project_path} && {nvm_prefix}npm run build", timeout=300),
            ],
        )
