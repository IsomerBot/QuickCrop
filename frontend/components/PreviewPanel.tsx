'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { UploadedFile, CropPreset, CROP_PRESETS, CropArea, CropPresetConfig, PhotoCategory } from '@/types';
import { calculateCropPreviewStyles } from '@/utils/cropCalculations';
import { ScanEye } from 'lucide-react';

interface PreviewPanelProps {
  file: UploadedFile;
  preset: CropPreset;
  cropArea?: CropArea;
  showAllPresets?: boolean;
  onPresetSelect?: (preset: CropPreset) => void;
  allCropAreas?: Record<string, CropArea>;
  presets?: CropPresetConfig[];
  enableComparison?: boolean; // when false, hides comparison toggle/section
  defaultShowComparison?: boolean; // initial state when comparisons are enabled
  category?: PhotoCategory; // 'employee' | 'project'
}

interface PreviewItemProps {
  file: UploadedFile;
  presetConfig: CropPresetConfig;
  cropArea?: CropArea;
  isActive: boolean;
  onClick?: () => void;
  size?: 'small' | 'medium' | 'large';
}

function PreviewItem({ 
  file, 
  presetConfig, 
  cropArea, 
  isActive, 
  onClick,
  size = 'medium' 
}: PreviewItemProps) {
  const [width, height] = presetConfig.aspectRatio;
  const aspectRatio = width / height;
  
  // Calculate crop styles based on cropArea
  const cropStyles = useMemo(() => {
    return calculateCropPreviewStyles(cropArea, file.dimensions, aspectRatio);
  }, [cropArea, file.dimensions, aspectRatio]);
  
  const sizeClasses = {
    small: 'max-w-[150px]',
    medium: 'max-w-[250px]',
    large: 'max-w-full'
  };
  
  return (
    <div
      className={`
        relative cursor-pointer transition-all
        ${isActive 
          ? 'ring-2 ring-orange-500 ring-offset-2 shadow-lg scale-105' 
          : 'hover:shadow-md hover:scale-102'
        }
        ${sizeClasses[size]}
      `}
      onClick={onClick}
    >
      {/* Image container with pure aspect ratio */}
      <div 
        className="relative bg-gray-800 overflow-hidden rounded-md"
        style={{ aspectRatio: aspectRatio.toString() }}
      >
        <img
          src={file.url}
          alt={`${presetConfig.name} preview`}
          className="absolute"
          style={cropStyles}
        />
        <div className="absolute inset-0 border border-gray-500 rounded-md pointer-events-none z-10"></div>
        
        {/* Active indicator */}
        {isActive && (
          <div className="absolute top-2 right-2">
            <div className="w-3 h-3 bg-orange-500 rounded-full animate-pulse"></div>
          </div>
        )}
      </div>
      
      {/* Remove name from thumbnails - it will be shown once in the info section */}
    </div>
  );
}

export default function PreviewPanel({ 
  file, 
  preset, 
  cropArea, 
  showAllPresets = true,
  onPresetSelect,
  allCropAreas = {},
  presets = CROP_PRESETS,
  enableComparison = true,
  defaultShowComparison = false,
  category
}: PreviewPanelProps) {
  const [selectedPreview, setSelectedPreview] = useState<CropPreset>(preset);
  const [showComparison, setShowComparison] = useState(defaultShowComparison);
  
  useEffect(() => {
    setSelectedPreview(preset);
  }, [preset]);
  
  const currentPresetConfig = presets.find(p => p.id === selectedPreview);
  const mainPresetConfig = presets.find(p => p.id === preset);
  
  const handlePresetClick = (presetId: CropPreset) => {
    setSelectedPreview(presetId);
    if (onPresetSelect) {
      onPresetSelect(presetId);
    }
  };
  
  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <ScanEye className="w-5 h-5" />
          Preview
        </h2>
        {enableComparison && (
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="text-sm text-orange-600 hover:text-orange-700 transition-colors"
          >
            {showComparison ? 'Hide' : 'Show'} Sample Comparison
          </button>
        )}
      </div>
      
      {/* Main Preview Area */}
      <div className="space-y-4">
        {/* Comparison View */}
        {enableComparison && showComparison && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-800 rounded-lg">
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Your Crop</h3>
              {currentPresetConfig && (
                <PreviewItem
                  file={file}
                  presetConfig={currentPresetConfig}
                  cropArea={cropArea}
                  isActive={false}
                  size="large"
                />
              )}
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">
                Sample ({currentPresetConfig?.name})
              </h3>
              {currentPresetConfig && (
                <div className="relative bg-gray-800 rounded-md overflow-hidden border border-gray-600">
                  <img
                    src={`/sample-images/Matt Ninnemann - ${currentPresetConfig.name === 'Headshot' ? 'Headshot' : currentPresetConfig.name === 'Full Body' ? 'Full Body' : 'Website'}.jpg`}
                    alt={`Sample ${currentPresetConfig.name}`}
                    className="w-full h-auto"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Main Preview */}
        {(!enableComparison || !showComparison) && mainPresetConfig && (
          <div>
            <div className="border border-gray-600 rounded-lg overflow-hidden relative">
              {category === 'project' && mainPresetConfig.id === 'proj_description' ? (
                (() => {
                  const overlayAR = 2303 / 1781; // overlay aspect ratio
                  const gapFactor = 0.1875;      // 18.75% of overlay width from left edge
                  const viewAR = 11 / 10;        // viewport/export aspect

                  // Container matches overlay AR (so overlay is never distorted)
                  // Viewport width as a fraction of overlay width
                  const viewportFrac = viewAR / overlayAR;

                  const styles = calculateCropPreviewStyles(cropArea, file.dimensions, viewAR);

                  return (
                    <div className="relative mx-auto overflow-hidden" style={{ aspectRatio: overlayAR.toString(), width: '100%' }}>
                      {/* Image shown only within the viewport clipped region */}
                      <div
                        className="absolute top-0 bottom-0 overflow-hidden"
                        style={{ left: `${gapFactor * 100}%`, width: `${viewportFrac * 100}%` }}
                      >
                        <img
                          src={file.url}
                          alt={`${mainPresetConfig.name} preview`}
                          className="absolute"
                          style={styles as React.CSSProperties}
                        />
                      </div>
                      {/* Overlay on top, at native AR */}
                      <img
                        src="/overlay/project_description_overlay.png"
                        alt="Project Description Overlay"
                        className="absolute inset-0 w-full h-full object-contain opacity-100 pointer-events-none z-10"
                      />
                    </div>
                  );
                })()
              ) : (
                <PreviewItem
                  file={file}
                  presetConfig={mainPresetConfig}
                  cropArea={cropArea}
                  isActive={false}
                  size="large"
                />
              )}
            </div>
          </div>
        )}
        
        {/* Consolidated Info */}
        {mainPresetConfig && (
          <div className="mt-4 p-3 bg-gray-700 rounded-lg">
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <p className="text-sm font-medium text-gray-200">
                  {mainPresetConfig.name}
                </p>
                <p className="text-sm text-gray-400">
                  Aspect Ratio: {mainPresetConfig.aspectRatio.join(':')}
                </p>
              </div>
              {mainPresetConfig.outputSizes && mainPresetConfig.outputSizes.length > 0 && (
                <p className="text-sm text-gray-400">
                  Output Sizes: {mainPresetConfig.outputSizes.map(s => `${s.size[0]}×${s.size[1]}`).join(', ')}
                </p>
              )}
              <p className="text-sm text-gray-500">
                {mainPresetConfig.description}
              </p>
              {file.dimensions && (
                <p className="text-sm text-gray-400">
                  Original Image: {file.dimensions.width} × {file.dimensions.height}px
                </p>
              )}
            </div>
          </div>
        )}
        
      </div>
    </div>
  );
}
