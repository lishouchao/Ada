"""
Systemd Integration - Service management for Ada
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SystemdIntegration:
    """
    Integration with systemd for service management.

    Provides:
    - Service file generation
    - Auto-start configuration
    - Service status monitoring
    """

    SERVICE_NAME = "ada.service"
    UNIT_NAME = "ada"

    def __init__(self):
        self._user_service_dir = Path.home() / ".config" / "systemd" / "user"
        self._system_service_dir = Path("/etc/systemd/system")

    def generate_user_service_file(self, exec_path: str, working_dir: str) -> str:
        """Generate systemd user service file content"""
        return f"""[Unit]
Description=Ada AI Assistant
Documentation=https://github.com/nebula/ada
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart={exec_path}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5

# Environment
Environment="ADA_MODE=daemon"
Environment="ADA_LOG_LEVEL=info"

# Security (for user service)
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={working_dir}

# Resource limits
MemoryMax=1G
CPUQuota=50%

[Install]
WantedBy=default.target
"""

    def generate_system_service_file(self, exec_path: str, working_dir: str) -> str:
        """Generate systemd system service file content"""
        return f"""[Unit]
Description=Ada AI Assistant (System Service)
Documentation=https://github.com/nebula/ada
After=network.target
Wants=network.target

[Service]
Type=simple
User=ada
Group=ada
ExecStart={exec_path}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=10

# Environment
Environment="ADA_MODE=daemon"
Environment="ADA_LOG_LEVEL=info"

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true

# Sandboxing
CapabilityBoundingSet=
SystemCallFilter=@system-service
SystemCallArchitectures=native

# Resource limits
MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
"""

    def install_user_service(self, exec_path: str, working_dir: str) -> bool:
        """Install as user service"""
        try:
            # Create service directory
            self._user_service_dir.mkdir(parents=True, exist_ok=True)

            # Write service file
            service_file = self._user_service_dir / self.SERVICE_NAME
            content = self.generate_user_service_file(exec_path, working_dir)

            with open(service_file, 'w') as f:
                f.write(content)

            logger.info(f"Installed user service: {service_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to install user service: {e}")
            return False

    def uninstall_user_service(self) -> bool:
        """Uninstall user service"""
        try:
            service_file = self._user_service_dir / self.SERVICE_NAME
            if service_file.exists():
                service_file.unlink()
            logger.info("Uninstalled user service")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall user service: {e}")
            return False

    def enable_service(self, user: bool = True) -> bool:
        """Enable the service to start on boot"""
        import subprocess

        try:
            if user:
                subprocess.run(
                    ["systemctl", "--user", "enable", self.UNIT_NAME],
                    check=True
                )
            else:
                subprocess.run(
                    ["systemctl", "enable", self.UNIT_NAME],
                    check=True
                )

            logger.info(f"Enabled service: {self.UNIT_NAME}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable service: {e}")
            return False

    def start_service(self, user: bool = True) -> bool:
        """Start the service"""
        import subprocess

        try:
            if user:
                subprocess.run(
                    ["systemctl", "--user", "start", self.UNIT_NAME],
                    check=True
                )
            else:
                subprocess.run(
                    ["systemctl", "start", self.UNIT_NAME],
                    check=True
                )

            logger.info(f"Started service: {self.UNIT_NAME}")
            return True

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False

    def stop_service(self, user: bool = True) -> bool:
        """Stop the service"""
        import subprocess

        try:
            if user:
                subprocess.run(
                    ["systemctl", "--user", "stop", self.UNIT_NAME],
                    check=True
                )
            else:
                subprocess.run(
                    ["systemctl", "stop", self.UNIT_NAME],
                    check=True
                )

            logger.info(f"Stopped service: {self.UNIT_NAME}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False

    def get_service_status(self, user: bool = True) -> dict:
        """Get service status"""
        import subprocess

        try:
            if user:
                result = subprocess.run(
                    ["systemctl", "--user", "show", self.UNIT_NAME,
                     "--property=ActiveState,SubState,MainPID"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["systemctl", "show", self.UNIT_NAME,
                     "--property=ActiveState,SubState,MainPID"],
                    capture_output=True,
                    text=True
                )

            status = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    status[key] = value

            return status

        except Exception as e:
            return {"error": str(e)}

    def reload_daemon(self, user: bool = True) -> bool:
        """Reload systemd daemon"""
        import subprocess

        try:
            if user:
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    check=True
                )
            else:
                subprocess.run(
                    ["systemctl", "daemon-reload"],
                    check=True
                )

            return True

        except Exception as e:
            logger.error(f"Failed to reload daemon: {e}")
            return False

    def is_service_running(self, user: bool = True) -> bool:
        """Check if service is running"""
        status = self.get_service_status(user)
        return status.get("ActiveState") == "active"
