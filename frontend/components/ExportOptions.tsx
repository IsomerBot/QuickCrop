'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { UploadedFile, CropPreset, ExportSize, CROP_PRESETS, CropArea } from '@/types';
import * as Slider from '@radix-ui/react-slider';
import { calculateCropPreviewStyles } from '@/utils/cropCalculations';
import { FolderInput, ImageDown } from 'lucide-react';

interface ExportOptionsProps {
  file: UploadedFile;
  preset: CropPreset;
  cropArea?: CropArea;
  allCropAreas?: Record<string, CropArea>;
  onExport: (options: ExportSettings) => Promise<void>;
  isProcessing: boolean;
  onPresetSelect?: (preset: CropPreset) => void;
}

export interface ExportSettings {
  format: 'jpeg' | 'png' | 'webp';
  quality: number;
  optimize: boolean;
  autoOptimize: boolean;  // New: Use Tinify for auto optimization
  employeeName: string;
  exportAll: boolean;
  selectedSizes: ExportSize[];
  outputFolder: string;
}

interface ExportHistory {
  id: string;
  timestamp: Date;
  fileName: string;
  employeeName: string;
  preset: string;
  format: string;
  size: number;
  status: 'success' | 'failed';
}

export default function ExportOptions({ 
  file, 
  preset, 
  cropArea,
  allCropAreas = {},
  onExport, 
  isProcessing,
  onPresetSelect
}: ExportOptionsProps) {
  // Export settings
  const [format, setFormat] = useState<'jpeg' | 'png' | 'webp'>('jpeg');
  const [quality, setQuality] = useState(85);
  const [optimize, setOptimize] = useState(true);
  const [autoOptimize, setAutoOptimize] = useState(true);  // New: Smart compression with Tinify
  // Always export multiple - no toggle needed
  const exportAll = true;
  const [selectedSizes, setSelectedSizes] = useState<ExportSize[]>(['headshot', 'avatar', 'website', 'full_body']);
  
  // Employee name parsing
  const [employeeName, setEmployeeName] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [autoDetectName, setAutoDetectName] = useState(true);
  
  // Export management
  const [exportHistory, setExportHistory] = useState<ExportHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStatus, setExportStatus] = useState<'idle' | 'exporting' | 'success' | 'error'>('idle');
  
  // Parse employee name from filename
  useEffect(() => {
    if (autoDetectName && file && file.name) {
      // Try to extract name from filename patterns like:
      // "john_doe_photo.jpg", "JohnDoe.jpg", "john-doe-headshot.png"
      const namePattern = /^([a-zA-Z]+[-_]?[a-zA-Z]+)/;
      const match = file.name.match(namePattern);
      
      if (match) {
        const parsedName = match[1]
          .replace(/[-_]/g, ' ')
          .split(' ')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
          .join(' ');
        setEmployeeName(parsedName);
      } else {
        // Fallback: use filename without extension
        const nameWithoutExt = file.name.split('.')[0];
        setEmployeeName(nameWithoutExt);
      }
    }
  }, [file?.name, autoDetectName]);
  
  // Handle size selection for batch export
  const handleSizeToggle = (sizeId: ExportSize) => {
    setSelectedSizes(prev => {
      if (prev.includes(sizeId)) {
        return prev.filter(p => p !== sizeId);
      } else {
        return [...prev, sizeId];
      }
    });
  };
  
  // Handle export
  const handleExport = async () => {
    setExportStatus('exporting');
    setExportProgress(0);
    
    const settings: ExportSettings = {
      format,
      quality,
      optimize,
      autoOptimize,
      employeeName,
      exportAll,
      selectedSizes: exportAll ? selectedSizes : ['headshot'],
      outputFolder: `exports/${employeeName.toLowerCase().replace(/\s+/g, '_')}`
    };
    
    try {
      // Simulate progress for demo
      const progressInterval = setInterval(() => {
        setExportProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);
      
      await onExport(settings);
      
      clearInterval(progressInterval);
      setExportProgress(100);
      setExportStatus('success');
      
      // Add to history
      const historyEntry: ExportHistory = {
        id: Date.now().toString(),
        timestamp: new Date(),
        fileName: `${employeeName}_${preset}.${format}`,
        employeeName,
        preset: CROP_PRESETS.find(p => p.id === preset)?.name || preset,
        format,
        size: Math.floor(file.size * 0.8), // Simulated compressed size
        status: 'success'
      };
      
      setExportHistory(prev => [historyEntry, ...prev].slice(0, 10));
      
      // Reset after success
      setTimeout(() => {
        setExportStatus('idle');
        setExportProgress(0);
      }, 3000);
      
    } catch (error) {
      setExportStatus('error');
      setExportProgress(0);
      
      // Add failed entry to history
      const historyEntry: ExportHistory = {
        id: Date.now().toString(),
        timestamp: new Date(),
        fileName: `${employeeName}_${preset}.${format}`,
        employeeName,
        preset: CROP_PRESETS.find(p => p.id === preset)?.name || preset,
        format,
        size: 0,
        status: 'failed'
      };
      
      setExportHistory(prev => [historyEntry, ...prev].slice(0, 10));
      
      setTimeout(() => {
        setExportStatus('idle');
      }, 3000);
    }
  };
  
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };
  
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      month: 'short',
      day: 'numeric'
    }).format(date);
  };
  
  // Helper function to render preset preview
  const renderPresetPreview = (presetConfig: typeof CROP_PRESETS[0]) => {
    const [width, height] = presetConfig.aspectRatio;
    const aspectRatio = width / height;
    const currentCropArea = allCropAreas[presetConfig.id] || (presetConfig.id === preset ? cropArea : undefined);
    const cropStyles = calculateCropPreviewStyles(currentCropArea, file.dimensions, aspectRatio);
    
    return (
      <div
        key={presetConfig.id}
        className={`
          relative cursor-pointer transition-all rounded-lg p-4 flex items-center justify-center
          ${presetConfig.id === preset 
            ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800 shadow-lg bg-gray-700' 
            : 'hover:shadow-md border border-gray-600 bg-gray-800'
          }
        `}
        onClick={() => onPresetSelect?.(presetConfig.id)}
        style={{ minHeight: '200px' }}
      >
        <div className="w-full">
          <div 
            className="relative bg-gray-700 overflow-hidden border border-black mx-auto"
            style={{ 
              aspectRatio: aspectRatio.toString(),
              maxWidth: '100%'
            }}
          >
            <img
              src={file.url}
              alt={`${presetConfig.name} preview`}
              className="absolute"
              style={cropStyles}
            />
            {presetConfig.id === preset && (
              <div className="absolute top-1 right-1">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <ImageDown className="w-5 h-5" />
        Export Options
      </h2>
      
      <div className="flex gap-6">
        {/* Left side - Preset Previews */}
        <div className="flex-1">
          <label className="text-sm font-medium text-gray-300 block mb-3">Preset Previews</label>
          <div className="grid grid-cols-3 gap-4">
            {CROP_PRESETS.map((presetConfig) => renderPresetPreview(presetConfig))}
          </div>
        </div>
        
        {/* Right side - Export Options */}
        <div className="w-2/5 space-y-3">
        {/* Employee Name */}
        <div>
          <label className="text-sm font-medium text-gray-300 mb-1 block">
            Employee Name
          </label>
          <div className="flex items-center space-x-2">
            {isEditingName ? (
              <input
                type="text"
                value={employeeName}
                onChange={(e) => setEmployeeName(e.target.value)}
                onBlur={() => setIsEditingName(false)}
                onKeyPress={(e) => e.key === 'Enter' && setIsEditingName(false)}
                className="flex-1 px-2 py-1.5 text-sm border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:outline-none focus:ring-2 focus:ring-orange-500"
                autoFocus
              />
            ) : (
              <div
                onClick={() => setIsEditingName(true)}
                className="flex-1 px-2 py-1.5 text-sm border border-gray-600 rounded-md cursor-text hover:border-gray-500 flex items-center justify-between bg-gray-700"
              >
                <span className={employeeName ? 'text-gray-200' : 'text-gray-500'}>
                  {employeeName || 'Enter name'}
                </span>
                <svg className="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </div>
            )}
            <button
              onClick={() => setAutoDetectName(!autoDetectName)}
              className={`px-2 py-1.5 text-xs rounded transition-colors ${
                autoDetectName 
                  ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' 
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
              title="Auto-detect name from filename"
            >
              Auto
            </button>
          </div>
        </div>
        
        {/* Format and Quality Row */}
        <div className="flex gap-3">
          {/* Format Selection */}
          <div className="w-32">
            <label className="text-sm font-medium text-gray-300 mb-1 block">
              Format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as any)}
              className="w-full h-[38px] px-3 text-sm border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="jpeg">JPEG</option>
              <option value="png">PNG</option>
              <option value="webp">WebP</option>
            </select>
          </div>
          
          {/* Auto-optimize indicator when active */}
          {autoOptimize && (
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-300 mb-1 block">
                Compression Mode
              </label>
              <div 
                onClick={() => setAutoOptimize(false)}
                className="h-[38px] px-3 bg-green-900/30 border border-green-600 rounded-md flex items-center gap-2 cursor-pointer hover:bg-green-900/50 transition-colors"
                title="Click to disable smart compression"
              >
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm text-green-400">Smart Compress (TinyPNG)</span>
              </div>
            </div>
          )}
          
          {/* Quality Slider - Only show when NOT using auto-optimize */}
          {!autoOptimize && (format === 'jpeg' || format === 'webp') && (
            <>
              <div className="flex-1">
                <label className="text-sm font-medium text-gray-300 mb-1 block">
                  Quality: {quality}%
                </label>
                <div className="h-[38px] flex items-center">
                  <Slider.Root
                    className="relative flex items-center select-none touch-none w-full h-5"
                    value={[quality]}
                    onValueChange={(value) => setQuality(value[0])}
                    max={100}
                    min={1}
                    step={1}
                  >
                    <Slider.Track className="bg-gray-700 relative grow rounded-full h-2">
                      <Slider.Range className="absolute bg-orange-500 rounded-full h-full" />
                    </Slider.Track>
                    <Slider.Thumb className="block w-5 h-5 bg-white border-2 border-orange-500 rounded-full hover:bg-orange-50 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2" />
                  </Slider.Root>
                </div>
              </div>
              
              {/* Web Optimization Toggle */}
              <div>
                <label className="text-sm font-medium text-gray-300 mb-1 block">
                  Web Optimize
                </label>
                <div className="h-[38px] flex items-center">
                  <button
                    onClick={() => setOptimize(!optimize)}
                    className={`
                      relative inline-flex h-6 w-11 items-center rounded-full
                      transition-colors duration-200 ease-in-out
                      ${optimize ? 'bg-orange-500' : 'bg-gray-600'}
                    `}
                  >
                    <span
                      className={`
                        inline-block h-4 w-4 transform rounded-full bg-white
                        transition-transform duration-200 ease-in-out
                        ${optimize ? 'translate-x-6' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
        
        {/* Export Multiple Presets Row */}
        <div>
          <div className="mb-3">
            <label className="text-sm font-medium text-gray-300">
              Items to Export
            </label>
          </div>
          
          <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => handleSizeToggle('headshot')}
                className={`
                  px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-2
                  ${selectedSizes.includes('headshot')
                    ? 'bg-green-600 text-white border-green-600 hover:bg-green-700'
                    : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
                  }
                `}
              >
                {selectedSizes.includes('headshot') ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4"/>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 9l-6 6m0-6l6 6"/>
                  </svg>
                )}
                Headshot
              </button>
              <button
                onClick={() => handleSizeToggle('avatar')}
                className={`
                  px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-2
                  ${selectedSizes.includes('avatar')
                    ? 'bg-green-600 text-white border-green-600 hover:bg-green-700'
                    : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
                  }
                `}
              >
                {selectedSizes.includes('avatar') ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4"/>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 9l-6 6m0-6l6 6"/>
                  </svg>
                )}
                Avatar
              </button>
              <button
                onClick={() => handleSizeToggle('website')}
                className={`
                  px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-2
                  ${selectedSizes.includes('website')
                    ? 'bg-green-600 text-white border-green-600 hover:bg-green-700'
                    : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
                  }
                `}
              >
                {selectedSizes.includes('website') ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4"/>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 9l-6 6m0-6l6 6"/>
                  </svg>
                )}
                Website
              </button>
              <button
                onClick={() => handleSizeToggle('full_body')}
                className={`
                  px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-2
                  ${selectedSizes.includes('full_body')
                    ? 'bg-green-600 text-white border-green-600 hover:bg-green-700'
                    : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
                  }
                `}
              >
                {selectedSizes.includes('full_body') ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4"/>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeWidth="2"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 9l-6 6m0-6l6 6"/>
                  </svg>
                )}
                Full Body
              </button>
            </div>
        </div>
        
        {/* Export Progress */}
        {exportStatus !== 'idle' && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">
                {exportStatus === 'exporting' && 'Exporting...'}
                {exportStatus === 'success' && 'Export complete!'}
                {exportStatus === 'error' && 'Export failed'}
              </span>
              <span className="text-gray-400">{exportProgress}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  exportStatus === 'success' ? 'bg-green-500' :
                  exportStatus === 'error' ? 'bg-red-500' : 'bg-orange-500'
                }`}
                style={{ width: `${exportProgress}%` }}
              />
            </div>
          </div>
        )}
        
        {/* Export Button */}
        <button
          onClick={handleExport}
          disabled={isProcessing || exportStatus === 'exporting' || !employeeName}
          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {exportStatus === 'exporting' ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing {exportAll ? selectedSizes.length : 1} image(s)...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <FolderInput className="w-5 h-5" />
              Export {exportAll ? `${selectedSizes.length} Images` : 'Image'}
            </span>
          )}
        </button>
        
        {/* Export History */}
        <div className="pt-2 border-t border-gray-600">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-gray-100"
          >
            <span>History</span>
            <svg
              className={`w-4 h-4 transition-transform ${showHistory ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showHistory && exportHistory.length > 0 && (
            <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
              {exportHistory.map((entry) => (
                <div
                  key={entry.id}
                  className={`p-2 rounded text-xs ${
                    entry.status === 'success' ? 'bg-green-50' : 'bg-red-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-gray-200">{entry.fileName}</p>
                      <p className="text-gray-400">{entry.preset} • {formatFileSize(entry.size)}</p>
                    </div>
                    <div className="text-right">
                      <p className={entry.status === 'success' ? 'text-green-600' : 'text-red-600'}>
                        {entry.status === 'success' ? '✓' : '✗'}
                      </p>
                      <p className="text-gray-500">{formatDate(entry.timestamp)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {showHistory && exportHistory.length === 0 && (
            <p className="mt-3 text-sm text-gray-500 text-center">No exports yet</p>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}