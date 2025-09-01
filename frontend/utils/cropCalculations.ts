/**
 * Utility functions for crop calculations
 */

export interface CropDimensions {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Calculate CSS styles to display a cropped portion of an image
 * within a container while maintaining aspect ratio
 */
export function calculateCropPreviewStyles(
  cropArea: CropDimensions | undefined,
  imageDimensions: { width: number; height: number } | undefined,
  containerAspectRatio: number
): React.CSSProperties {
  // If no crop area, show the full image centered and covering
  if (!cropArea || !imageDimensions) {
    return {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      objectPosition: 'center'
    };
  }

  // Calculate what percentage of the image is being cropped
  const cropWidthPercent = (cropArea.width / imageDimensions.width) * 100;
  const cropHeightPercent = (cropArea.height / imageDimensions.height) * 100;
  
  // Scale the image so the crop area fills the container
  // Using the width as the basis for scaling since container maintains aspect ratio
  const scale = 100 / cropWidthPercent;
  
  // Calculate position as percentage of the container
  const offsetXPercent = -(cropArea.x / cropArea.width) * 100;
  const offsetYPercent = -(cropArea.y / cropArea.height) * 100;
  
  return {
    width: `${scale * 100}%`,
    height: 'auto',
    position: 'absolute',
    left: `${offsetXPercent}%`,
    top: `${offsetYPercent}%`,
    maxWidth: 'none',
    maxHeight: 'none'
  };
}

/**
 * Calculate if an image needs to be scaled differently for a preset
 */
export function shouldFitToWidth(
  cropAspectRatio: number,
  containerAspectRatio: number
): boolean {
  return containerAspectRatio > cropAspectRatio;
}