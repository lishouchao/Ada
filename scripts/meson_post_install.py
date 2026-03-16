#!/usr/bin/env python3
"""
Meson post-install script for Ada.

Updates icon cache and other post-installation tasks.
"""

import os
import subprocess
import sys

def update_icon_cache(datadir):
    """Update GTK icon cache"""
    icon_dir = os.path.join(datadir, 'icons', 'hicolor')
    if os.path.exists(icon_dir):
        try:
            subprocess.call(['gtk-update-icon-cache', '-f', icon_dir])
        except Exception:
            pass

def update_desktop_database(datadir):
    """Update desktop database"""
    applications_dir = os.path.join(datadir, 'applications')
    if os.path.exists(applications_dir):
        try:
            subprocess.call(['update-desktop-database', applications_dir])
        except Exception:
            pass

def main():
    if len(sys.argv) < 2:
        print("Usage: meson_post_install.py <datadir>")
        sys.exit(1)

    datadir = sys.argv[1]

    update_icon_cache(datadir)
    update_desktop_database(datadir)

    print("Ada post-installation complete")

if __name__ == '__main__':
    main()
