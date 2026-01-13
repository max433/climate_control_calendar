# Icons for Climate Control Calendar

This folder contains icon files for the integration in various formats and styles.

## Available Icons

### 🎨 `icon.svg` - Full Design
**Style**: Detailed, with calendar grid and thermometer gauge
**Use for**: README headers, documentation, social media
**Colors**: Home Assistant blue (#03a9f4) + Orange accent (#ff9800)
**Features**:
- Calendar with binding rings
- Active day highlight (orange)
- Temperature gauge with gradient (cold→hot)
- Connection arrow showing calendar→climate flow

### ✨ `icon-minimal.svg` - Minimal Design
**Style**: Clean, modern, abstract
**Use for**: App icons, favicons, small displays
**Colors**: HA blue gradient background + minimal white elements
**Features**:
- Simplified calendar with dot grid
- Abstract temperature waves (hot/warm/cool)
- Centered connection indicator
- Better scalability for small sizes

---

## How to Use

### For HACS Integration
HACS requires `icon.png` (256x256 PNG):

```bash
# Convert SVG to PNG using one of these methods:

# Method 1: ImageMagick (if installed)
convert icon.svg -resize 256x256 icon.png

# Method 2: Inkscape (if installed)
inkscape icon.svg --export-png=icon.png --export-width=256 --export-height=256

# Method 3: Online converter
# Upload icon.svg to: https://cloudconvert.com/svg-to-png
# Set output size: 256x256
# Download as icon.png
```

### For Home Assistant Brand Icons
Place in `custom_components/climate_control_calendar/`:
- `icon.png` - 256x256 PNG (required by HACS)
- `icon@2x.png` - 512x512 PNG (optional, for retina displays)

### For README/Documentation
Use SVG directly in markdown:

```markdown
![Climate Control Calendar](icon.svg)
```

Or convert to PNG and use:
```markdown
![Climate Control Calendar](icon.png)
```

### For Favicon (Web/Browser)
Create smaller sizes:

```bash
# 32x32 for favicon
convert icon-minimal.svg -resize 32x32 favicon-32.png

# 16x16 for browser tab
convert icon-minimal.svg -resize 16x16 favicon-16.png

# ICO format (multi-size)
convert icon-minimal.svg -define icon:auto-resize=16,32,48,64,256 favicon.ico
```

---

## Design Rationale

### Color Palette
- **Primary Blue (#03a9f4)**: Home Assistant brand color, represents automation/smart home
- **Dark Blue (#0277bd)**: Depth and contrast
- **Orange (#ff9800)**: Warmth, heating, active state highlighting
- **Red-Orange (#ff6b6b)**: Hot temperature
- **Teal (#4ecdc4)**: Cool temperature
- **White**: Clean, modern, Apple-style aesthetic

### Symbolism
- **Calendar Grid**: Event-based scheduling, flexibility
- **Binding Rings**: Connection between events and actions
- **Active Day Highlight**: Current active event
- **Temperature Gradient**: Climate control range (cold→hot)
- **Connection Arrow/Indicator**: Calendar→Climate data flow

### Style Inspiration
- Material Design (Google/Android)
- Home Assistant Dashboard aesthetics
- Apple iOS icon design (rounded, modern)
- Flat design with subtle gradients

---

## Customization

### Change Colors
Edit the SVG files and modify the color codes:

```xml
<!-- Primary blue -->
<stop offset="0%" style="stop-color:#03a9f4;stop-opacity:1" />

<!-- Orange accent -->
<rect fill="#ff9800"/>
```

### Export Different Sizes

```bash
# Small (64x64) for thumbnails
convert icon.svg -resize 64x64 icon-small.png

# Medium (128x128) for mobile
convert icon.svg -resize 128x128 icon-medium.png

# Large (512x512) for hi-res displays
convert icon.svg -resize 512x512 icon-large.png

# Extra large (1024x1024) for press/media kit
convert icon.svg -resize 1024x1024 icon-xlarge.png
```

---

## Online Tools (No Installation Required)

If you don't have ImageMagick or Inkscape:

1. **SVG to PNG Converter**: https://cloudconvert.com/svg-to-png
2. **Favicon Generator**: https://realfavicongenerator.net/
3. **SVG Editor**: https://boxy-svg.com/app (edit online)
4. **Multi-Size Generator**: https://www.websiteplanet.com/webtools/favicon-generator/

---

## License

These icon files are part of the Climate Control Calendar integration and are licensed under the same MIT License as the project.

---

## Credits

Designed specifically for Climate Control Calendar integration
Inspired by Home Assistant design language and Material Design principles
Created with love for the smart home community ❤️
