#!/bin/bash

# This script sets up the necessary permissions for Voice Typer on Fedora Wayland.

echo "Setting up Voice Typer permissions..."

# 1. Add user to 'input' group
if ! groups $USER | grep &>/dev/null "\binput\b"; then
    echo "Adding $USER to 'input' group..."
    sudo usermod -aG input $USER
    echo "NOTE: You will need to log out and log back in for this to take effect."
else
    echo "User $USER is already in 'input' group."
fi

# 2. Setup udev rule for /dev/uinput
UDEV_RULE_PATH="/etc/udev/rules.d/99-voice-typer.rules"
echo "Creating udev rule for /dev/uinput..."
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' | sudo tee $UDEV_RULE_PATH > /dev/null

# 3. Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# 4. Ensure /dev/uinput has the right group right now
sudo chgrp input /dev/uinput
sudo chmod 660 /dev/uinput

# 5. Install desktop file, icon, and binary symlink
echo "Installing desktop entry, icon, and binary..."
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$BIN_DIR"

# Absolute path to the launcher
PROJECT_PATH=$(pwd)

cp launchers/voice-typer.desktop "$DESKTOP_DIR/"
cp launchers/voice-typer.svg "$ICON_DIR/"

# Create a symlink in ~/.local/bin to the run.sh script
ln -sf "$PROJECT_PATH/run.sh" "$BIN_DIR/voice-typer"

# Update the Exec line in the desktop file to use the absolute path
sed -i "s|Exec=.*|Exec=bash -c \"cd $PROJECT_PATH \&\& ./run.sh\"|" "$DESKTOP_DIR/voice-typer.desktop"
sed -i "s|Icon=.*|Icon=$ICON_DIR/voice-typer.svg|" "$DESKTOP_DIR/voice-typer.desktop"

echo "Done! You can now run 'voice-typer' from your terminal or launcher."
