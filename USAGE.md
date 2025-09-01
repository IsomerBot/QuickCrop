# QuickCrop Usage Guide

## How the Application Works

QuickCrop is designed as a real-time photo cropping tool with live preview. Here's the intended workflow:

### 1. Upload an Image
- Use the **left panel** to upload an image via drag-and-drop or file selection
- Supported formats: JPEG, PNG, WebP
- Maximum file size: 10MB (configurable)

### 2. Crop Editor (Left Side)
The **Crop Editor** on the left side is where you:
- **Select a preset** from the 4 buttons at the top:
  - **Headshot** (2000×2000) - Square crop for professional headshots
  - **Website Avatar** (300×300) - Small square for profile pictures  
  - **Website Photo** (1600×2000) - Portrait 4:5 for website headers
  - **Full Body** (3400×4000) - Portrait 17:20 for full professional photos
  
- **Adjust the crop area** manually by:
  - Dragging the image to reposition
  - Using the zoom slider to zoom in/out
  - Using keyboard shortcuts (Arrow keys to move, Ctrl +/- to zoom)
  - Using Undo/Redo buttons to revert changes

### 3. Preview Panel (Right Side)
The **Preview Panel** on the right shows:
- **Main Preview**: Large preview of the currently selected preset with your crop adjustments
- **All Preset Previews**: Small thumbnails showing how your crop looks in all 4 presets
- **Show Original** button: Toggle to compare original vs cropped

### 4. Real-Time Updates
**IMPORTANT**: As you adjust the crop in the left panel:
- The preview on the right updates **automatically after you stop dragging**
- The system uses the `onCropComplete` event (triggered when you release the mouse)
- All 4 preset previews update simultaneously to show the crop in different aspect ratios

### 5. Export Options (Right Side, Bottom)
Once satisfied with your crop:
- **Employee Name**: Auto-detected from filename or enter manually
- **Select Presets**: Choose which formats to export (can select multiple)
- **Export Settings**: Choose quality and optimization options
- **Export Button**: Generates the final images in selected formats

## Visual Feedback

### During Crop Adjustment:
- **Grid overlay** appears on the crop area
- **Aspect ratio** is locked based on selected preset
- **Zoom percentage** shown next to slider

### In Preview Panel:
- **Thin border** around cropped images shows exact crop boundaries
- **Active preset** highlighted with blue ring
- **Dimensions** shown below each preview
- **Aspect ratio** displayed for reference

## Tips for Best Results

1. **Start with the right preset**: Choose the preset that matches your intended use first
2. **Use zoom carefully**: Zoom in to focus on the subject, but ensure important details aren't cut off
3. **Check all previews**: Look at the small previews to ensure your crop works for all formats
4. **Use keyboard shortcuts**: For precise adjustments, use arrow keys instead of dragging
5. **Compare with original**: Toggle "Show Original" to ensure you're not losing important content

## Technical Notes

- The application uses **MediaPipe** for face detection to suggest initial crops
- **React Easy Crop** library provides the cropping interface
- Crops are calculated in pixels for precise output
- All processing happens client-side for privacy

## Common Issues

**Preview not updating?**
- The preview updates when you release the mouse after dragging
- If it doesn't update, try clicking elsewhere on the crop area

**Wrong aspect ratio?**
- Each preset has a fixed aspect ratio that cannot be changed
- Switch to a different preset if you need a different ratio

**Export not working?**
- Ensure you've selected at least one preset for export
- Check that employee name field is filled (if required)