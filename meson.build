# Ada - Meson build configuration
# Used for Flatpak builds and system installation

project('ada', 'python',
  version: '0.1.0',
  meson_version: '>= 0.59.0',
  default_options: [
    'warning_level=2',
  ]
)

# Installation directories
prefix = get_option('prefix')
bindir = get_option('bindir')
libdir = get_option('libdir')
datadir = get_option('datadir')

# Python installation
py = import('python').find_installation('python3')
py.install_sources(
  'src/ada',
  subdir: 'ada'
)

# Install data files
install_data(
  'data/ada.desktop',
  install_dir: join_paths(datadir, 'applications')
)

install_data(
  'data/icons/hicolor/scalable/apps/ada.svg',
  install_dir: join_paths(datadir, 'icons/hicolor/scalable/apps')
)

install_data(
  'data/ada.service',
  install_dir: join_paths(libdir, 'systemd/user')
)

# Install D-Bus service
install_data(
  'data/org.nebula.Ada.service',
  install_dir: join_paths(datadir, 'dbus-1/services')
)

# Install configuration
install_data(
  'config/ada.yaml',
  install_dir: join_paths(datadir, 'ada')
)

# Create executable script
configure_file(
  input: 'scripts/ada.in',
  output: 'ada',
  configuration: {
    'PYTHON': py.path(),
    'PREFIX': prefix,
  },
  install_dir: bindir,
  install_mode: 'rwxr-xr-x'
)

# Post-install message
meson.add_install_script('scripts/meson_post_install.py')
