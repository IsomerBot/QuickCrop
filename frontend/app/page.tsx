'use client';

import { useRef, useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import CropEditor from '@/components/CropEditor';
import PreviewPanel from '@/components/PreviewPanel';
import ExportOptions from '@/components/ExportOptions';
import { UploadedFile, CropPreset, CropArea, CROP_PRESETS, PhotoCategory, getPresets } from '@/types';
import { apiClient } from '@/lib/api';

export default function Home() {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<CropPreset>('headshot');
  const [category, setCategory] = useState<PhotoCategory | null>(null);
  const [presetCropAreas, setPresetCropAreas] = useState<Record<string, CropArea>>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCropping, setIsCropping] = useState(false);
  const [suggestionsLoaded, setSuggestionsLoaded] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const categoryLockRef = useRef(false);
  const activeCategory = (category ?? 'employee') as PhotoCategory;
  const presets = getPresets(activeCategory);

  const applyCategory = (nextCategory: PhotoCategory, options?: { lock?: boolean }) => {
    const shouldLock = options?.lock ?? false;

    if (shouldLock) {
      categoryLockRef.current = true;
    } else if (categoryLockRef.current) {
      return;
    }

    const previousCategory = category;
    setCategory(nextCategory);

    if (previousCategory !== nextCategory) {
      const firstPreset = getPresets(nextCategory)[0]?.id as CropPreset | undefined;
      if (firstPreset) {
        setSelectedPreset(firstPreset);
      }
    }
  };

  const handleCategoryOverride = (nextCategory: PhotoCategory) => {
    applyCategory(nextCategory, { lock: true });
  };

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);
    setSuggestionsLoaded(false); // Reset suggestions state
    setPresetCropAreas({}); // Clear previous crop areas
    
    // Create a local preview URL for the UI immediately
    const url = URL.createObjectURL(file);
    const dimensions = await getImageDimensions(url);
    
    let fileId = Date.now().toString();
    
    // Set the uploaded file for local preview immediately
    const uploadedFileData = {
      id: fileId,
      name: file.name,
      url: url,
      size: file.size,
      type: file.type,
      dimensions: dimensions
    };
    setUploadedFile(uploadedFileData);
    // Reset category until classification completes
    categoryLockRef.current = false;
    setCategory(null);
    setIsProcessing(false);
    
    // Try to upload to backend and get AI crop suggestions
    setClassifying(true);
    apiClient.uploadSingle(file).then(async response => {
      if (response && response.file_id) {
        setUploadId(response.file_id);
        // Auto-select category based on face detection
        try {
          const isEmployee = (response.faces_detected ?? 0) > 0 || response.status === 'ready';
          const cat: PhotoCategory = isEmployee ? 'employee' : 'project';
          applyCategory(cat);
        } finally {
          setClassifying(false);
        }
        
        // Get AI crop suggestions based on our tuned MediaPipe rules
        try {
          const suggestions = await apiClient.getCropSuggestions(response.file_id);
          // Auto-classify based on face area percentage (> 3% = employee)
          try {
            const iw = suggestions?.image_dimensions?.width;
            const ih = suggestions?.image_dimensions?.height;
            const fd = suggestions?.face_detection;
            const fw = fd?.width;
            const fh = fd?.height;
            if (iw && ih && fw && fh) {
              const pct = (fw * fh) / (iw * ih) * 100;
              const cat: PhotoCategory = pct > 3 ? 'employee' : 'project';
              applyCategory(cat);
            } else {
              // Fallback if missing data
              const isEmployee = (response.faces_detected ?? 0) > 0 || response.status === 'ready';
              const cat: PhotoCategory = isEmployee ? 'employee' : 'project';
              applyCategory(cat);
            }
          } finally {
            setClassifying(false);
          }
          
          if (suggestions && suggestions.crop_suggestions) {
            // Apply the AI suggestions as initial crop areas
            const initialCropAreas: Record<string, CropArea> = {};
            
            for (const [preset, cropData] of Object.entries(suggestions.crop_suggestions)) {
              if (typeof cropData === 'object' && cropData !== null) {
                const crop = cropData as any;
                initialCropAreas[preset] = {
                  x: crop.x,
                  y: crop.y,
                  width: crop.width,
                  height: crop.height
                };
                
                // Calculate face position for reference
                const faceCenterInCrop = suggestions.face_detection.center_y - crop.y;
                const facePositionPercent = (faceCenterInCrop / crop.height) * 100;
              }
            }
            
            setPresetCropAreas(initialCropAreas);
            setSuggestionsLoaded(true);
          } else {
            // No suggestions available
          }
        } catch (error) {
          // Continue without suggestions if they fail; fallback to simple face presence
          const isEmployee = (response.faces_detected ?? 0) > 0 || response.status === 'ready';
          const cat: PhotoCategory = isEmployee ? 'employee' : 'project';
          applyCategory(cat);
          setClassifying(false);
        }
      }
    }).catch(error => {
      // Backend upload failed, but we can continue with local processing
      setClassifying(false);
    });
  };

  const getImageDimensions = (url: string): Promise<{ width: number; height: number }> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        resolve({ width: img.width, height: img.height });
      };
      img.src = url;
    });
  };

  const handleExport = async (exportSettings: any) => {
    if (!uploadedFile) return;
    
    setIsProcessing(true);
    try {
      // Map export sizes to backend preset format (employee)
      const sizeToPresetMap: Record<string, string> = {
        'headshot': 'headshot',
        'avatar': 'headshot',  // Avatar/thumbnail reuse headshot crop, just smaller outputs
        'thumbnail': 'headshot',
        'website': 'website',
        'full_body': 'full_body',
        'proj_header': 'proj_header',
        'proj_thumbnail': 'proj_thumbnail',
        'proj_description': 'proj_description',
      };

      // Use backend API when uploadId is available (Employee and Project)
      if (uploadId) {
        if (exportSettings.exportAll && exportSettings.selectedSizes.length > 0) {
          // Export each preset individually to get proper compressed images
          
          for (const size of exportSettings.selectedSizes) {
            const presetName = sizeToPresetMap[size] || size;
            
            try {
              // Reuse headshot crop for avatar/thumbnail outputs
              const cropPresetName = (size === 'avatar' || size === 'thumbnail') ? 'headshot' : presetName;
              
              const blob = await apiClient.exportImage(uploadId, {
                preset: size,  // Send the actual size (avatar/thumbnail use dedicated resolutions)
                format: exportSettings.format,
                quality: exportSettings.quality,
                optimize: exportSettings.optimize,
                auto_optimize: exportSettings.autoOptimize,
                crop_box: presetCropAreas[cropPresetName] || null  // Use headshot crop for avatar/thumbnail
              });
              
              // Trigger download
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              // Replace spaces with underscores and convert to lowercase
              const sanitizedName = exportSettings.employeeName.replace(/\s+/g, '_').toLowerCase();
              // Suffix mapping for project workflow
              const suffixMap: Record<string, string> = {
                'proj_header': 'header',
                'proj_thumbnail': 'thumbnail',
                'proj_description': 'description',
              };
              const suffix = (category === 'project') ? (suffixMap[size] || size) : size;
              a.download = `${sanitizedName}_${suffix}.${exportSettings.format}`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
              
              // Small delay between downloads
              await new Promise(resolve => setTimeout(resolve, 500));
            } catch (error) {
              // Continue with next export if one fails
            }
          }
        } else {
          // Single preset export
          
          const blob = await apiClient.exportImage(uploadId, {
            preset: selectedPreset,
            format: exportSettings.format,
            quality: exportSettings.quality,
            optimize: exportSettings.optimize,
            auto_optimize: exportSettings.autoOptimize,
            crop_box: presetCropAreas[selectedPreset] || null  // Send user's crop area
          });

          // Trigger download
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          // Replace spaces with underscores and convert to lowercase
          const sanitizedName = exportSettings.employeeName.replace(/\s+/g, '_').toLowerCase();
          const suffixMap: Record<string, string> = {
            'proj_header': 'header',
            'proj_thumbnail': 'thumbnail',
            'proj_description': 'description',
          };
          const suffix = (category === 'project') ? (suffixMap[selectedPreset] || String(selectedPreset)) : String(selectedPreset);
          a.download = `${sanitizedName}_${suffix}.${exportSettings.format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      } else {
        // Fallback to canvas-based export if no backend connection
        // No backend connection, using canvas export
        await canvasExport(exportSettings);
      }
    } catch (error) {
      // Fall back to canvas export on error
      await canvasExport(exportSettings);
    } finally {
      setIsProcessing(false);
    }
  };

  // Canvas-based fallback export
  const canvasExport = async (exportSettings: any) => {
    console.warn('USING CANVAS EXPORT - NOT TINIFY COMPRESSED!');
    if (!uploadedFile) return;
    
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    await new Promise((resolve) => {
      img.onload = resolve;
      img.src = uploadedFile.url;
    });

    // Process each selected preset
    const sizeToPresetMap: Record<string, string> = {
      'headshot': 'headshot',
      'avatar': 'headshot',  // Avatar/thumbnail reuse headshot crop locally too
      'thumbnail': 'headshot',
      'website': 'website',
      'full_body': 'full_body',
      'proj_header': 'proj_header',
      'proj_thumbnail': 'proj_thumbnail',
      'proj_description': 'proj_description',
    };
    
    for (const exportSize of (exportSettings.exportAll ? exportSettings.selectedSizes : [selectedPreset])) {
      const preset = sizeToPresetMap[exportSize] || exportSize;
      const cropArea = presetCropAreas[preset];
      
      if (!cropArea || !cropArea.width || !cropArea.height) {
        console.warn(`No valid crop area for preset: ${preset}`, cropArea);
        continue;
      }
      
      // Get preset config for dimensions using active preset set
      const presetConfig = presets.find(p => p.id === preset);
      if (!presetConfig) continue;
      
      // Find the right output size for this export
      let outputSize = [2000, 2000];
      if (exportSize === 'avatar') {
        outputSize = [300, 300];
      } else if (presetConfig.outputSizes) {
        const sizeConfig = presetConfig.outputSizes.find(s => s.id === exportSize);
        outputSize = sizeConfig?.size || presetConfig.outputSizes[0]?.size || [2000, 2000];
      }
      
      canvas.width = outputSize[0];
      canvas.height = outputSize[1];
      
      ctx?.drawImage(
        img,
        cropArea.x,
        cropArea.y,
        cropArea.width,
        cropArea.height,
        0,
        0,
        outputSize[0],
        outputSize[1]
      );
      
      // Export the canvas
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const sanitized = exportSettings.employeeName.replace(/\s+/g, '_').toLowerCase();
            const suffixMap: Record<string, string> = {
              'proj_header': 'header',
              'proj_thumbnail': 'thumbnail',
              'proj_description': 'description',
            };
            const suffix = (category === 'project') ? (suffixMap[exportSize as string] || String(exportSize)) : String(exportSize);
            a.download = `${sanitized}_${suffix}.${exportSettings.format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          }
        },
        `image/${exportSettings.format === 'png' ? 'png' : 'jpeg'}`,
        exportSettings.format === 'png' ? undefined : exportSettings.quality / 100
      );
      
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };

  const handleCropChange = (cropArea: CropArea) => {
    // Always update so the preview responds in real time
    setPresetCropAreas(prev => ({
      ...prev,
      [selectedPreset]: cropArea
    }));
  };

  const handlePresetChange = (preset: CropPreset) => {
    setSelectedPreset(preset);
  };

  const handleCroppingStateChange = (isCropping: boolean) => {
    setIsCropping(isCropping);
  };

  const showWorkspace = Boolean(uploadedFile && category);

  return (
    <main className="min-h-screen p-8 bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center justify-between">
            <button
              onClick={() => {
                setUploadedFile(null);
                setUploadId(null);
                setPresetCropAreas({});
                setCategory(null);
                categoryLockRef.current = false;
              }}
              className="cursor-pointer transition-transform hover:scale-105"
              aria-label="Return to upload"
            >
              <img 
                src="/isomer-logo.png" 
                alt="QuickCrop Logo" 
                className="h-16 w-auto"
              />
            </button>
            <h1 className="text-5xl text-white">
              QUICK CROP
            </h1>
          </div>
        </div>

        {/* Main Content */}
        {!uploadedFile ? (
          <div className="flex justify-center">
            <div className="w-full max-w-2xl">
              <ImageUploader onUpload={handleFileUpload} isProcessing={isProcessing} />
            </div>
          </div>
        ) : showWorkspace ? (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Left Column - Crop Editor */}
              <div className="space-y-6">
                <CropEditor
                  file={uploadedFile}
                  preset={selectedPreset}
                  onPresetChange={handlePresetChange}
                  onCropChange={handleCropChange}
                  cropArea={suggestionsLoaded ? presetCropAreas[selectedPreset] : undefined}
                  onCroppingStateChange={handleCroppingStateChange}
                  presets={presets}
                  category={activeCategory}
                  onCategoryChange={handleCategoryOverride}
                />
              </div>

              {/* Right Column - Preview Panel */}
              <div className="space-y-6">
                <PreviewPanel
                  key={category}
                  file={uploadedFile}
                  preset={selectedPreset}
                  cropArea={presetCropAreas[selectedPreset]}
                  showAllPresets={true}
                  onPresetSelect={handlePresetChange}
                  allCropAreas={presetCropAreas}
                  presets={presets}
                  enableComparison={activeCategory !== 'project'}
                  defaultShowComparison={activeCategory !== 'project'}
                  category={activeCategory}
                />
              </div>
            </div>

            {/* Full Width Export Options */}
            <div className="w-full">
              <ExportOptions
                file={uploadedFile}
                preset={selectedPreset}
                cropArea={presetCropAreas[selectedPreset]}
                allCropAreas={presetCropAreas}
                onExport={handleExport}
                isProcessing={isProcessing}
                onPresetSelect={handlePresetChange}
                presets={presets}
                nameLabel={activeCategory === 'project' ? 'Project Name' : 'Employee Name'}
              />
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-6">
            <div className="w-full max-w-2xl">
              <ImageUploader onUpload={handleFileUpload} isProcessing={isProcessing} />
            </div>
            <div className="w-full max-w-xl bg-gray-900/70 border border-gray-700 rounded-xl p-6 text-center">
              <div className="flex items-center justify-center gap-3 mb-2">
                {classifying ? (
                  <div className="h-5 w-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" aria-hidden />
                ) : (
                  <svg className="h-6 w-6 text-orange-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
                  </svg>
                )}
                <h2 className="text-lg font-semibold text-white">Analyzing photo</h2>
              </div>
              <p className="text-sm text-gray-300">
                {classifying
                  ? 'Identifying the best workflow for this photo…'
                  : 'We could not determine the workflow automatically. Please choose how you want to crop.'}
              </p>
              {!classifying && (
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  <button
                    className="px-4 py-2 text-sm font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600 focus:outline-none focus:ring-2 focus:ring-orange-400"
                    onClick={() => applyCategory('employee', { lock: true })}
                  >
                    Use Team Presets
                  </button>
                  <button
                    className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-800 text-gray-200 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-orange-400"
                    onClick={() => applyCategory('project', { lock: true })}
                  >
                    Use Project Presets
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
