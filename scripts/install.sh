#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(dirname "$SCRIPT_DIR")
INSTALL_ROOT=${TTS_INSTALL_ROOT:-"$HOME/.local/share/terminal-theme-suite"}
BIN_DIR=${TTS_BIN_DIR:-"$HOME/.local/bin"}
ITERM_SUPPORT_LINK=${TTS_ITERM_SUPPORT_LINK:-"$HOME/Library/ApplicationSupport"}
ITERM_SCRIPTS_DIR=${TTS_ITERM_SCRIPTS_DIR:-"$ITERM_SUPPORT_LINK/iTerm2/Scripts"}
VENV="$INSTALL_ROOT/venv"
DAEMON="$ITERM_SCRIPTS_DIR/AutoLaunch/terminal_theme_suite.py"
LEGACY_RUNNER="$ITERM_SCRIPTS_DIR/terminal_theme_suite.py"

command -v python3 >/dev/null 2>&1 || {
  echo "error: python3 is required" >&2
  exit 1
}

if [ ! -e "$ITERM_SUPPORT_LINK" ]; then
  ln -s "Application Support" "$ITERM_SUPPORT_LINK"
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$ITERM_SCRIPTS_DIR/AutoLaunch"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet --upgrade "$REPO_DIR"
cp "$REPO_DIR/scripts/iterm_api_daemon.py" "$DAEMON"
chmod 755 "$DAEMON"
rm -f "$LEGACY_RUNNER"
ln -sfn "$VENV/bin/term-theme" "$BIN_DIR/term-theme"
ln -sfn "$VENV/bin/terminal-theme-suite" "$BIN_DIR/terminal-theme-suite"

"$BIN_DIR/term-theme" init --daemon "$DAEMON"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "note: add $BIN_DIR to PATH" ;;
esac

echo "installed: $BIN_DIR/term-theme"
