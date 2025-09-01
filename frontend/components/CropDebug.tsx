import React from 'react';
import { CropArea } from '@/types';

interface CropDebugProps {
  cropArea?: CropArea;
  imageDimensions?: { width: number; height: number };
}

export default function CropDebug({ cropArea, imageDimensions }: CropDebugProps) {
  if (!cropArea || !imageDimensions) {
    return (
      <div className="text-xs text-gray-500 p-2 bg-gray-100 rounded">
        No crop area selected yet
      </div>
    );
  }

  return (
    <div className="text-xs font-mono text-gray-600 p-2 bg-gray-100 rounded space-y-1">
      <div className="font-semibold text-gray-700">Crop Debug Info:</div>
      <div>Image: {imageDimensions.width} × {imageDimensions.height}px</div>
      <div>Crop X: {Math.round(cropArea.x)}px</div>
      <div>Crop Y: {Math.round(cropArea.y)}px</div>
      <div>Crop W: {Math.round(cropArea.width)}px</div>
      <div>Crop H: {Math.round(cropArea.height)}px</div>
      <div>Crop %: {Math.round((cropArea.width / imageDimensions.width) * 100)}% × {Math.round((cropArea.height / imageDimensions.height) * 100)}%</div>
    </div>
  );
}