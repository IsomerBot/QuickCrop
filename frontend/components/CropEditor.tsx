'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import Cropper from 'react-easy-crop';
import type { Point, Area } from 'react-easy-crop';
import * as Slider from '@radix-ui/react-slider';
import { UploadedFile, CropPreset, CROP_PRESETS, CropArea, CropPresetConfig, PhotoCategory } from '@/types';
import { Crop, ZoomIn, ZoomOut } from 'lucide-react';

interface CropEditorProps {
  file: UploadedFile;
  preset: CropPreset;
  onPresetChange: (preset: CropPreset) => void;
  onCropComplete?: (cropArea: CropArea, cropPixels: CropArea) => void;
  onCropChange?: (cropArea: CropArea) => void;
  cropArea?: CropArea;  // Initial crop suggestion from AI
  onCroppingStateChange?: (isCropping: boolean) => void;
  presets?: CropPresetConfig[];
  category?: PhotoCategory; // 'employee' | 'project'
  onCategoryChange?: (category: PhotoCategory) => void;
}

interface CropState {
  crop: Point;
  zoom: number;
  rotation: number;
  croppedArea: Area | null;
  croppedAreaPixels: Area | null;
}

interface HistoryState {
  past: CropState[];
  present: CropState;
  future: CropState[];
}

interface PresetCropStates {
  [key: string]: CropState;
}

export default function CropEditor({ 
  file, 
  preset, 
  onPresetChange,
  onCropComplete,
  onCropChange,
  cropArea,
  onCroppingStateChange,
  presets = CROP_PRESETS,
  category,
  onCategoryChange
}: CropEditorProps) {
  // Find the current preset configuration
  const currentPresetConfig = presets.find(p => p.id === preset);
  const resolvedCategory: PhotoCategory = category || 'employee';
  const categoryOptions: Array<{ value: PhotoCategory; label: string }> = [
    { value: 'employee', label: 'Team' },
    { value: 'project', label: 'Project' }
  ];
  const aspectRatio = currentPresetConfig 
    ? currentPresetConfig.aspectRatio[0] / currentPresetConfig.aspectRatio[1]
    : 1;
  
  // Determine target output size for current preset
  const outputSize = (() => {
    if (!currentPresetConfig) return undefined as undefined | [number, number];
    const match = (currentPresetConfig.outputSizes || []).find(s => s.id === preset as any);
    const size = match?.size || currentPresetConfig.outputSizes?.[0]?.size;
    return size as undefined | [number, number];
  })();

  // Per-preset toggle: allow zooming beyond no-upscaling rule
  const [allowUpscaleByPreset, setAllowUpscaleByPreset] = useState<Record<string, boolean>>(() => {
    const m: Record<string, boolean> = {};
    (CROP_PRESETS as CropPresetConfig[]).forEach(p => { m[p.id] = false; });
    return m;
  });
  const allowUpscale = !!allowUpscaleByPreset[preset];

  // Compute maximum allowed zoom to avoid upscaling beyond source pixels
  const maxZoom = (() => {
    const imgW = file.dimensions?.width || 0;
    const imgH = file.dimensions?.height || 0;
    if (!imgW || !imgH || !outputSize) return 3; // fallback when unknown
    const [outW, outH] = outputSize;
    if (!outW || !outH) return 3;
    const limit = Math.min(imgW / outW, imgH / outH);
    // Enforce no-upscaling rule unless upscaling is allowed for this preset
    const base = Math.max(1, limit);
    return allowUpscale ? Math.max(base, 10) : base; // allow up to 10x when enabled
  })();

  
  // State for boundary feedback
  const [showBoundaryFeedback, setShowBoundaryFeedback] = useState(false);
  const [currentCropPixels, setCurrentCropPixels] = useState<CropArea | null>(null);

  // Initial crop state
  const initialState: CropState = {
    crop: { x: 0, y: 0 },
    zoom: 1,
    rotation: 0,
    croppedArea: null,
    croppedAreaPixels: null
  };

  // Store separate crop states for each preset
  const [presetStates, setPresetStates] = useState<PresetCropStates>(() => {
    const states: PresetCropStates = {};
    presets.forEach(p => {
      states[p.id] = { ...initialState };
    });
    return states;
  });

  // Rebuild preset states when available presets set changes
  useEffect(() => {
    const states: PresetCropStates = {};
    presets.forEach(p => { states[p.id] = { ...initialState }; });
    setPresetStates(states);
    // Reset history to current preset baseline
    setHistory({ past: [], present: states[preset] || initialState, future: [] });
  }, [presets]);

  // State for undo/redo functionality (for current preset)
  const [history, setHistory] = useState<HistoryState>(() => {
    const initial = presetStates[preset] || initialState;
    return {
      past: [],
      present: initial,
      future: []
    };
  });

  // Use history.present values directly for better reactivity
  const crop = history.present.crop;
  const zoom = history.present.zoom;
  const rotation = history.present.rotation;
  

  // Track previous preset to detect changes
  const prevPresetRef = useRef(preset);
  
  // Debounce timer for history
  const historyTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastKeyboardAttemptRef = useRef<{ key: string; crop: Point; timestamp: number } | null>(null);
  const lastSavedStateRef = useRef<CropState | null>(history.present);
  const baselineStateRef = useRef<CropState | null>(history.present);
  
  // Update history when preset changes (not when presetStates updates)
  useEffect(() => {
    if (prevPresetRef.current !== preset) {
      prevPresetRef.current = preset;
      // Clear any pending history save when switching presets
      if (historyTimerRef.current) {
        clearTimeout(historyTimerRef.current);
      }
      setHistory({
        past: [],
        present: presetStates[preset] || initialState,
        future: []
      });
      lastSavedStateRef.current = presetStates[preset] || initialState;
      baselineStateRef.current = presetStates[preset] || initialState;
    }
  }, [preset, presetStates, initialState]); // Safe to include these now with the ref check
  
  // Track which presets have received AI suggestions to avoid re-applying
  const appliedSuggestionsRef = useRef<Set<string>>(new Set());
  // Flag to prevent handleCropChange from overriding AI suggestions
  const isApplyingSuggestionRef = useRef(false);
  
  // Apply AI crop suggestions when they come in (only once per preset)
  useEffect(() => {
    
    // Only apply if we have a valid AI suggestion (not a default full-width crop)
    const isValidAISuggestion = cropArea && 
                                file.dimensions && 
                                cropArea.width < file.dimensions.width && // AI crops are never full width
                                !appliedSuggestionsRef.current.has(preset);
    
    
    if (isValidAISuggestion) {
      // Mark this preset as having received suggestions
      appliedSuggestionsRef.current.add(preset);
      isApplyingSuggestionRef.current = true;
      
      // The cropArea from AI is in pixels, we need to convert to react-easy-crop's system
      if (!file?.dimensions) {
        // Dimensions unknown (e.g., metadata not set yet) — skip applying this suggestion
        return;
      }
      const { width: imgWidth, height: imgHeight } = file.dimensions as { width: number; height: number };
      
      // Calculate zoom to fit the suggested crop
      // For a square crop, we use the height to calculate zoom
      const newZoom = imgHeight / cropArea.height;
      
      // Now we need to position the crop correctly
      // React-easy-crop uses percentage offsets from center
      // We need to calculate what offset will show our specific crop region
      
      // The visible area after zoom
      const visibleWidth = imgWidth / newZoom;
      const visibleHeight = imgHeight / newZoom;
      
      // Calculate the center of our desired crop
      const cropCenterX = cropArea.x + cropArea.width / 2;
      const cropCenterY = cropArea.y + cropArea.height / 2;
      
      // Calculate the center of the image
      const imgCenterX = imgWidth / 2;
      const imgCenterY = imgHeight / 2;
      
      // Calculate offset needed to center our crop
      // This is the distance from image center to crop center
      const pixelOffsetX = cropCenterX - imgCenterX;
      const pixelOffsetY = cropCenterY - imgCenterY;
      
      // Convert to percentage of visible area
      // In react-easy-crop: positive values move the image right/down (showing left/top parts)
      //                     negative values move the image left/up (showing right/bottom parts)
      const percentOffsetX = -(pixelOffsetX / visibleWidth) * 100;
      const percentOffsetY = -(pixelOffsetY / visibleHeight) * 100;
      
      const newCrop = {
        x: percentOffsetX,
        y: percentOffsetY
      };
      
      const newState: CropState = {
        crop: newCrop,
        zoom: newZoom,
        rotation: 0,
        croppedArea: null,
        croppedAreaPixels: {
          x: cropArea.x,
          y: cropArea.y,
          width: cropArea.width,
          height: cropArea.height
        }
      };
      
      // Update the preset state with AI suggestion
      setPresetStates(prev => {
        return {
          ...prev,
          [preset]: newState
        };
      });
      
      // Update current history
      setHistory(prev => {
        return {
          past: [],
          present: newState,
          future: []
        };
      });
      
      // Verify the crop will show the head properly
      const headTopInImage = cropArea.y - (cropArea.height * 0.145);  // Where head should be
      const headVisibleAfterZoom = headTopInImage >= cropArea.y;
      
      // Allow handleCropChange to run again after a brief delay
      setTimeout(() => {
        isApplyingSuggestionRef.current = false;
      }, 100);
    }
  }, [cropArea, preset, file.dimensions, aspectRatio]);
  
  // Reset applied suggestions when file changes
  useEffect(() => {
    appliedSuggestionsRef.current.clear();
  }, [file.id]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (historyTimerRef.current) {
        clearTimeout(historyTimerRef.current);
      }
    };
  }, []);

  // Clamp current zoom if preset/image constraints reduce maxZoom
  useEffect(() => {
    if (history.present.zoom > maxZoom) {
      handleZoomChange(maxZoom, true);
    }
  }, [maxZoom]);

  // Keyboard control state
  const [keyboardStep] = useState({ position: 2, zoom: 0.02 });
  
  // Function to check if crop is at boundary based on pixel coordinates
  const checkIfAtBoundary = (): { atBoundary: boolean; directions: string[] } => {
    if (!currentCropPixels || !file.dimensions) {
      return { atBoundary: false, directions: [] };
    }
    
    const directions: string[] = [];
    const tolerance = 2; // pixels tolerance
    
    // Check each boundary
    if (currentCropPixels.x <= tolerance) {
      directions.push('left');
    }
    if (currentCropPixels.x + currentCropPixels.width >= file.dimensions.width - tolerance) {
      directions.push('right');
    }
    if (currentCropPixels.y <= tolerance) {
      directions.push('top');
    }
    if (currentCropPixels.y + currentCropPixels.height >= file.dimensions.height - tolerance) {
      directions.push('bottom');
    }
    
    return {
      atBoundary: directions.length > 0,
      directions
    };
  };
  
  // Function to show boundary feedback
  const triggerBoundaryFeedback = () => {
    setShowBoundaryFeedback(true);
    setTimeout(() => setShowBoundaryFeedback(false), 300);
  };
  
  // Debounced history save
  const saveToHistory = useCallback((newState: CropState, immediate = false) => {
    // Clear any pending save
    if (historyTimerRef.current) {
      clearTimeout(historyTimerRef.current);
    }
    
    if (immediate) {
      // Save immediately for discrete actions (buttons, keyboard)
      if (!lastSavedStateRef.current || 
          JSON.stringify(lastSavedStateRef.current) !== JSON.stringify(newState)) {
        setHistory(prev => ({
          past: [...prev.past, prev.present],
          present: newState,
          future: []
        }));
        lastSavedStateRef.current = newState;
        baselineStateRef.current = newState;
      }
    } else {
      // For continuous actions, capture baseline if this is the start
      if (!historyTimerRef.current) {
        // This is the start of a continuous action
        baselineStateRef.current = lastSavedStateRef.current;
      }
      
      // Debounce for continuous actions (dragging, slider)
      historyTimerRef.current = setTimeout(() => {
        // Only add to history if we've actually changed from the baseline
        if (baselineStateRef.current && 
            JSON.stringify(baselineStateRef.current) !== JSON.stringify(newState)) {
          setHistory(prev => ({
            past: baselineStateRef.current ? [...prev.past, baselineStateRef.current] : prev.past,
            present: newState,
            future: []
          }));
          lastSavedStateRef.current = newState;
          baselineStateRef.current = newState;
        }
      }, 500); // Save to history after 500ms of inactivity
    }
  }, []);

  // Handle crop complete
  const onCropCompleteHandler = useCallback((croppedArea: Area, croppedAreaPixels: Area) => {
    const newState: CropState = {
      ...history.present,
      croppedArea,
      croppedAreaPixels
    };

    // Update present state immediately
    setHistory(prev => ({
      ...prev,
      present: newState
    }));
    
    // Save to history with debounce
    saveToHistory(newState, false);

    // Save state for current preset
    setPresetStates(prev => ({
      ...prev,
      [preset]: newState
    }));

    // Convert Area to CropArea format and notify parent
    const cropAreaFormat: CropArea = {
      x: croppedAreaPixels.x,
      y: croppedAreaPixels.y,
      width: croppedAreaPixels.width,
      height: croppedAreaPixels.height
    };
    
    if (onCropComplete) {
      onCropComplete(cropAreaFormat, cropAreaFormat);
    }
    
    // Also update via onCropChange for real-time preview
    if (onCropChange) {
      onCropChange(cropAreaFormat);
    }
  }, [history.present, preset, onCropComplete, onCropChange, saveToHistory]);

  // Handle crop change (while dragging - don't add to history)
  const handleCropChange = useCallback((location: Point) => {
    // Don't override AI suggestions when they're being applied
    if (isApplyingSuggestionRef.current) {
      return;
    }
    
    const newState: CropState = {
      ...history.present,
      crop: location
    };
    
    // Only update present, don't add to history during drag
    setHistory(prev => ({
      ...prev,
      present: newState
    }));

    // Save state for current preset
    setPresetStates(prev => ({
      ...prev,
      [preset]: newState
    }));

    // Proactively push latest known pixel crop to parent for real-time preview
    if (onCropChange && currentCropPixels) {
      onCropChange(currentCropPixels);
    }
  }, [history.present, preset]);

  // Handle zoom change  
  const handleZoomChange = useCallback((newZoom: number, immediate = false) => {
    const clampedZoom = Math.max(1, Math.min(maxZoom, newZoom));
    const newState: CropState = {
      ...history.present,
      zoom: clampedZoom
    };
    
    // Update present state immediately
    setHistory(prev => ({
      ...prev,
      present: newState
    }));
    
    // Save to history - immediate for buttons/keyboard, debounced for slider
    saveToHistory(newState, immediate);

    // Save state for current preset
    setPresetStates(prev => ({
      ...prev,
      [preset]: newState
    }));
  }, [history.present, preset, saveToHistory, maxZoom]);

  // Undo functionality
  const undo = useCallback(() => {
    if (history.past.length === 0) return;
    
    // Clear any pending history save
    if (historyTimerRef.current) {
      clearTimeout(historyTimerRef.current);
    }
    
    const previous = history.past[history.past.length - 1];
    const newPast = history.past.slice(0, history.past.length - 1);
    
    setHistory({
      past: newPast,
      present: previous,
      future: [history.present, ...history.future]
    });
    
    // Update last saved state
    lastSavedStateRef.current = previous;
    
    // Update preset states and trigger preview update
    setPresetStates(prev => ({
      ...prev,
      [preset]: previous
    }));
    
    // Update the preview if we have crop area
    if (previous.croppedAreaPixels && onCropChange) {
      const cropAreaFormat: CropArea = {
        x: previous.croppedAreaPixels.x,
        y: previous.croppedAreaPixels.y,
        width: previous.croppedAreaPixels.width,
        height: previous.croppedAreaPixels.height
      };
      onCropChange(cropAreaFormat);
    }
  }, [history, preset, onCropChange]);

  // Redo functionality
  const redo = useCallback(() => {
    if (history.future.length === 0) return;
    
    // Clear any pending history save
    if (historyTimerRef.current) {
      clearTimeout(historyTimerRef.current);
    }
    
    const next = history.future[0];
    const newFuture = history.future.slice(1);
    
    setHistory({
      past: [...history.past, history.present],
      present: next,
      future: newFuture
    });
    
    // Update last saved state
    lastSavedStateRef.current = next;
    
    // Update preset states and trigger preview update
    setPresetStates(prev => ({
      ...prev,
      [preset]: next
    }));
    
    // Update the preview if we have crop area
    if (next.croppedAreaPixels && onCropChange) {
      const cropAreaFormat: CropArea = {
        x: next.croppedAreaPixels.x,
        y: next.croppedAreaPixels.y,
        width: next.croppedAreaPixels.width,
        height: next.croppedAreaPixels.height
      };
      onCropChange(cropAreaFormat);
    }
  }, [history, preset, onCropChange]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Handle Tab key for preset cycling
      if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = presets.findIndex(p => p.id === preset);
        if (e.shiftKey) {
          // Shift+Tab: cycle backwards
          const newIndex = currentIndex > 0 ? currentIndex - 1 : presets.length - 1;
          onPresetChange(presets[newIndex].id);
        } else {
          // Tab: cycle forwards
          const newIndex = currentIndex < presets.length - 1 ? currentIndex + 1 : 0;
          onPresetChange(presets[newIndex].id);
        }
        return;
      }

      // Prevent default browser behavior for arrow keys
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
      }

      let newCrop = { ...crop };
      let newZoom = zoom;
      let shouldUpdate = false;

      switch (e.key) {
        case 'ArrowUp':
          if (e.ctrlKey || e.metaKey) {
            // Ctrl/Cmd + Up: Zoom in
            e.preventDefault();
            newZoom = Math.min(maxZoom, zoom + keyboardStep.zoom);
            handleZoomChange(newZoom, true); // Add to history for keyboard
          } else {
            // Just Up: Move crop up
            newCrop.y -= keyboardStep.position;
            shouldUpdate = true;
          }
          break;
        case 'ArrowDown':
          if (e.ctrlKey || e.metaKey) {
            // Ctrl/Cmd + Down: Zoom out
            e.preventDefault();
            newZoom = Math.max(1, zoom - keyboardStep.zoom);
            handleZoomChange(newZoom, true); // Add to history for keyboard
          } else {
            // Just Down: Move crop down
            newCrop.y += keyboardStep.position;
            shouldUpdate = true;
          }
          break;
        case 'ArrowLeft':
          newCrop.x -= keyboardStep.position;
          shouldUpdate = true;
          break;
        case 'ArrowRight':
          newCrop.x += keyboardStep.position;
          shouldUpdate = true;
          break;
        case 'z':
        case 'Z':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (e.shiftKey) {
              redo();
            } else {
              undo();
            }
          }
          break;
        case 'y':
        case 'Y':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            redo();
          }
          break;
      }

      if (shouldUpdate) {
        // Check if this movement would exceed boundaries
        const currentBoundary = checkIfAtBoundary();
        let blockMovement = false;
        
        // Determine which direction we're trying to move
        const deltaX = newCrop.x - crop.x;
        const deltaY = newCrop.y - crop.y;
        
        // In react-easy-crop, moving the crop position moves the viewport
        // Arrow keys move the image in the opposite direction
        // ArrowLeft (deltaX < 0) = image moves left = viewport moves right = right boundary
        if (deltaX < 0 && currentBoundary.directions.includes('right')) {
          blockMovement = true; // Image moving left, viewport at right boundary
        } else if (deltaX > 0 && currentBoundary.directions.includes('left')) {
          blockMovement = true; // Image moving right, viewport at left boundary
        }
        
        if (deltaY < 0 && currentBoundary.directions.includes('bottom')) {
          blockMovement = true; // Image moving up, viewport at bottom boundary
        } else if (deltaY > 0 && currentBoundary.directions.includes('top')) {
          blockMovement = true; // Image moving down, viewport at top boundary
        }
        
        if (blockMovement) {
          // Don't apply the movement, just show feedback
          triggerBoundaryFeedback();
          return;
        }
        
        // Apply the new crop position
        handleCropChange(newCrop);
        
        // Save to history after keyboard movement stops
        const newState: CropState = {
          ...history.present,
          crop: newCrop
        };
        saveToHistory(newState, false); // Debounced save for keyboard movement
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [crop, zoom, keyboardStep, preset, history.present, handleCropChange, handleZoomChange, undo, redo, onPresetChange, saveToHistory, triggerBoundaryFeedback, checkIfAtBoundary, currentCropPixels, file.dimensions, maxZoom]);

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4 gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Crop className="w-5 h-5" />
            Crop Settings
          </h2>
          {onCategoryChange && (
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-gray-400 hidden sm:inline">Mode</span>
              <div className="flex bg-gray-800 border border-gray-700 rounded-full p-0.5" role="group" aria-label="Photo category">
                {categoryOptions.map(option => {
                  const isActive = resolvedCategory === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        if (!isActive) {
                          onCategoryChange(option.value);
                        }
                      }}
                      className={`px-2 py-1 text-xs font-medium rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
                        isActive
                          ? 'bg-orange-500 text-white shadow-sm'
                          : 'text-gray-300 hover:text-white'
                      }`}
                      aria-pressed={isActive}
                      aria-label={`Switch to ${option.label.toLowerCase()} mode`}
                      title={`Use ${option.label} presets`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-1">
          <button
            onClick={undo}
            disabled={history.past.length === 0}
            className={`p-1.5 rounded transition-colors ${
              history.past.length === 0
                ? 'text-gray-600 cursor-not-allowed'
                : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
            title="Undo (Ctrl/Cmd + Z)"
            aria-label="Undo"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
            </svg>
          </button>
          <button
            onClick={redo}
            disabled={history.future.length === 0}
            className={`p-1.5 rounded transition-colors ${
              history.future.length === 0
                ? 'text-gray-600 cursor-not-allowed'
                : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
            title="Redo (Ctrl/Cmd + Shift + Z)"
            aria-label="Redo"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
            </svg>
          </button>
        </div>
      </div>
      
      {/* Preset Selection */}
      <div className="space-y-3 mb-6">
        <label className="text-sm font-medium text-gray-300">
          Select Crop Preset
        </label>
        
        <div className="flex gap-2">
          {presets.map((presetConfig) => (
            <button
              key={presetConfig.id}
              onClick={() => onPresetChange(presetConfig.id)}
              className={`
                flex-1 px-3 py-2 rounded-lg border-2 text-center transition-all text-sm font-medium
                ${preset === presetConfig.id
                  ? 'border-orange-500 bg-orange-500 text-white hover:bg-orange-600'
                  : 'border-gray-600 hover:border-gray-500 text-gray-300'
                }
              `}
            >
              {presetConfig.name}
              {presetConfig.id === 'headshot' && (
                <span className="ml-1 text-xs align-super">2</span>
              )}
            </button>
          ))}
        </div>
        
        {/* Selected preset details */}
        {currentPresetConfig && (
          <div className="p-3 bg-gray-700 rounded-lg">
            <p className="text-sm text-gray-300">
              {currentPresetConfig.description}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Aspect Ratio: {currentPresetConfig.aspectRatio[0]}:{currentPresetConfig.aspectRatio[1]}
              {currentPresetConfig.outputSizes && (
                <span className="ml-2">
                  • Sizes: {currentPresetConfig.outputSizes.map(s => `${s.size[0]}×${s.size[1]}`).join(', ')}
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Crop Canvas */}
      <div className={`relative bg-gray-800 rounded-lg overflow-hidden h-[300px] sm:h-[400px] md:h-[450px] ${showBoundaryFeedback ? 'boundary-feedback' : ''}`}>
        <Cropper
          image={file.url}
          crop={crop}
          zoom={zoom}
          rotation={rotation}
          minZoom={1}
          maxZoom={maxZoom}
          aspect={aspectRatio}
          onCropChange={handleCropChange}
          onZoomChange={handleZoomChange}
          onCropComplete={onCropCompleteHandler}
          restrictPosition={true}
          onCropAreaChange={(croppedArea, croppedAreaPixels) => {
            // This fires continuously during movement, including keyboard
            const cropAreaFormat: CropArea = {
              x: croppedAreaPixels.x,
              y: croppedAreaPixels.y,
              width: croppedAreaPixels.width,
              height: croppedAreaPixels.height
            };
            
            // Store current crop pixels for boundary detection
            setCurrentCropPixels(cropAreaFormat);
            
            if (onCropChange) {
              onCropChange(cropAreaFormat);
            }
          }}
          showGrid={true}
        />
      </div>

      {/* Zoom Controls */}
      <div className="mt-6 space-y-4">
        <div>
          <label className="text-sm font-medium text-gray-300 mb-2 block">
            Zoom
          </label>
          <div className="flex items-center space-x-2 sm:space-x-4">
            <button
              onClick={() => handleZoomChange(Math.max(1, zoom - 0.1), true)}
              className="p-1.5 sm:p-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors text-gray-300"
              aria-label="Zoom out"
            >
              <ZoomOut className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
            <Slider.Root
              className="relative flex items-center select-none touch-none w-full h-5"
              value={[zoom]}
              onValueChange={(value) => handleZoomChange(value[0], false)}
              max={maxZoom}
              min={1}
              step={0.01}
              aria-label="Zoom slider"
            >
              <Slider.Track className="bg-gray-700 relative grow rounded-full h-2">
                <Slider.Range className="absolute bg-orange-500 rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb className="block w-5 h-5 bg-white border-2 border-orange-500 rounded-full hover:bg-orange-50 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2" />
            </Slider.Root>
            <button
              onClick={() => handleZoomChange(Math.min(maxZoom, zoom + 0.1), true)}
              className="p-1.5 sm:p-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors text-gray-300"
              aria-label="Zoom in"
            >
              <ZoomIn className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
            <span className="text-xs sm:text-sm text-gray-400 min-w-[45px] sm:min-w-[60px] text-right">
              {Math.round(zoom * 100)}%
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
            <button
              type="button"
              onClick={() => setAllowUpscaleByPreset(prev => ({ ...prev, [preset]: !prev[preset] }))}
              className={`px-2 py-1 rounded border ${allowUpscale ? 'border-green-500 text-green-400' : 'border-gray-600 text-gray-400'} hover:border-orange-500 hover:text-orange-400 transition-colors`}
              title="Allow zooming beyond native resolution for this preset"
            >
              {allowUpscale ? 'Upscaling: On' : 'Upscaling: Off'}
            </button>
            <span>Max {Math.round(maxZoom * 100)}%</span>
          </div>
        </div>

        {/* File Info */}
        <div className="pt-4 border-t border-gray-600">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium text-gray-300">
              File Information
            </h3>
            <button
              onClick={() => window.location.reload()}
              className="text-xs text-orange-600 hover:text-orange-700 transition-colors"
              title="Upload a different image"
            >
              Change Image
            </button>
          </div>
          <div className="space-y-1 text-sm text-gray-400">
            <div>Name: {file.name}</div>
            <div>Size: {(file.size / 1024).toFixed(1)} KB</div>
            <div>Type: {file.type}</div>
            {file.dimensions && (
              <div>Dimensions: {file.dimensions.width} × {file.dimensions.height}px</div>
            )}
          </div>
        </div>

        {/* Keyboard Shortcuts Help */}
        <div className="text-xs text-gray-400 pt-4 border-t border-gray-600">
          <p className="font-medium mb-1">Keyboard shortcuts:</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
            <p>• Tab/Shift+Tab: Cycle presets</p>
            <p>• Ctrl/Cmd + Up/Down: Zoom</p>
            <p>• Arrow keys: Move crop</p>
            <p>• Ctrl/Cmd + Z: Undo/Redo</p>
          </div>
        </div>
      </div>
    </div>
  );
}
