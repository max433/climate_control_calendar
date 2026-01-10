#!/bin/bash
# Installation script for Climate Control Calendar
# For Home Assistant manual installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Climate Control Calendar - Manual Installation${NC}"
echo ""

# Check if HA config path is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <path-to-homeassistant-config>${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 /config                     # Docker"
    echo "  $0 ~/.homeassistant            # Core installation"
    echo "  $0 /usr/share/hassio/homeassistant  # Supervised"
    echo ""
    exit 1
fi

HA_CONFIG="$1"

# Verify HA config directory exists
if [ ! -d "$HA_CONFIG" ]; then
    echo -e "${RED}Error: Home Assistant config directory not found: $HA_CONFIG${NC}"
    exit 1
fi

# Verify configuration.yaml exists
if [ ! -f "$HA_CONFIG/configuration.yaml" ]; then
    echo -e "${YELLOW}Warning: configuration.yaml not found in $HA_CONFIG${NC}"
    echo "Are you sure this is your Home Assistant config directory?"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create custom_components directory if it doesn't exist
CUSTOM_DIR="$HA_CONFIG/custom_components"
echo "Creating custom_components directory..."
mkdir -p "$CUSTOM_DIR"

# Remove old installation if exists
if [ -d "$CUSTOM_DIR/climate_control_calendar" ]; then
    echo -e "${YELLOW}Removing old installation...${NC}"
    rm -rf "$CUSTOM_DIR/climate_control_calendar"
fi

# Copy integration files
echo "Copying Climate Control Calendar files..."
cp -r custom_components/climate_control_calendar "$CUSTOM_DIR/"

# Verify installation
if [ -f "$CUSTOM_DIR/climate_control_calendar/manifest.json" ]; then
    VERSION=$(grep -oP '"version":\s*"\K[^"]+' "$CUSTOM_DIR/climate_control_calendar/manifest.json")
    echo -e "${GREEN}✓ Installation successful!${NC}"
    echo ""
    echo "Installed: Climate Control Calendar v$VERSION"
    echo "Location: $CUSTOM_DIR/climate_control_calendar"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Restart Home Assistant"
    echo "2. Go to Settings → Devices & Services"
    echo "3. Click '+ Add Integration'"
    echo "4. Search for 'Climate Control Calendar'"
    echo ""
    echo -e "${YELLOW}Note:${NC} Make sure you have at least one calendar integration configured!"
else
    echo -e "${RED}✗ Installation failed!${NC}"
    exit 1
fi
