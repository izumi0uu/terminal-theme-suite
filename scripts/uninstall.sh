#!/bin/sh
set -eu

INSTALL_ROOT=${TTS_INSTALL_ROOT:-"$HOME/.local/share/terminal-theme-suite"}
BIN_DIR=${TTS_BIN_DIR:-"$HOME/.local/bin"}
ITERM_SUPPORT_LINK=${TTS_ITERM_SUPPORT_LINK:-"$HOME/Library/ApplicationSupport"}
ITERM_SCRIPTS_DIR=${TTS_ITERM_SCRIPTS_DIR:-"$ITERM_SUPPORT_LINK/iTerm2/Scripts"}
PROFILE_FILE="$HOME/Library/Application Support/iTerm2/DynamicProfiles/Terminal Theme Suite.plist"
DAEMON="$ITERM_SCRIPTS_DIR/AutoLaunch/terminal_theme_suite.py"
LEGACY_RUNNER="$ITERM_SCRIPTS_DIR/terminal_theme_suite.py"

pkill -f '[/]AutoLaunch[/]terminal_theme_suite[.]py' 2>/dev/null || true
if [ -x "$BIN_DIR/term-theme" ]; then
  "$BIN_DIR/term-theme" omp-live-reload remove >/dev/null 2>&1 || true
fi
rm -f \
  "$BIN_DIR/term-theme" \
  "$BIN_DIR/terminal-theme-suite" \
  "$PROFILE_FILE" \
  "$DAEMON" \
  "$LEGACY_RUNNER"
rm -rf "$INSTALL_ROOT"

echo "Program removed. User themes remain in ~/.config/terminal-theme-suite."
