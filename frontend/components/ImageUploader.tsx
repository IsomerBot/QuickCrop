'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadedFile } from '@/types';

interface ImageUploaderProps {
  onUpload: (file: File) => void;
  isProcessing?: boolean;
}

export default function ImageUploader({ onUpload, isProcessing = false }: ImageUploaderProps) {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Reset error state
    setUploadError(null);
    
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      if (rejection.errors[0]?.code === 'file-too-large') {
        setUploadError('File size must be less than 10MB');
      } else if (rejection.errors[0]?.code === 'file-invalid-type') {
        setUploadError('Please upload a valid image file (JPEG, PNG, or WebP)');
      } else {
        setUploadError('Invalid file. Please try again.');
      }
      return;
    }

    const file = acceptedFiles[0];
    if (!file) return;

    // Validate image dimensions
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);
    
    img.onload = () => {
      // Check minimum dimensions
      if (img.width < 500 || img.height < 500) {
        setUploadError('Image must be at least 500x500 pixels');
        URL.revokeObjectURL(objectUrl);
        return;
      }

      // Set preview
      setPreviewUrl(objectUrl);
      
      // Simulate upload progress
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        setUploadProgress(progress);
        
        if (progress >= 100) {
          clearInterval(interval);
          
          // Call onUpload with the File object
          onUpload(file);
          
          // Reset progress after a short delay
          setTimeout(() => {
            setUploadProgress(0);
            setPreviewUrl(null);
          }, 500);
        }
      }, 100);
    };
    
    img.onerror = () => {
      setUploadError('Failed to load image. Please try another file.');
      URL.revokeObjectURL(objectUrl);
    };
    
    img.src = objectUrl;
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpeg', '.jpg'],
      'image/png': ['.png'],
      'image/webp': ['.webp']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
    disabled: isProcessing || uploadProgress > 0,
    noClick: false,
    noKeyboard: false
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Upload Image</h2>
      
      {/* Error Message */}
      {uploadError && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400 text-sm">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {uploadError}
          </div>
        </div>
      )}
      
      {/* Upload Progress */}
      {uploadProgress > 0 && uploadProgress < 100 && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Uploading...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div 
              className="bg-orange-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Preview */}
      {previewUrl && uploadProgress === 100 && (
        <div className="mb-4 p-3 bg-green-900/20 border border-green-800 rounded-lg">
          <div className="flex items-center text-green-400">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-sm">Image uploaded successfully!</span>
          </div>
        </div>
      )}
      
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center
          transition-all duration-200
          ${isProcessing || uploadProgress > 0 
            ? 'cursor-not-allowed opacity-50' 
            : 'cursor-pointer'
          }
          ${isDragActive 
            ? 'border-orange-500 bg-orange-50 scale-[1.02]' 
            : 'border-gray-600 hover:border-gray-500'
          }
        `}
      >
        <input {...getInputProps()} />
        
        {uploadProgress > 0 && uploadProgress < 100 ? (
          <>
            <div className="mx-auto h-12 w-12 flex items-center justify-center mb-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-500"></div>
            </div>
            <p className="text-gray-300">Processing image...</p>
          </>
        ) : (
          <>
            <svg
              className="mx-auto h-12 w-12 text-gray-500 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            
            {isDragActive ? (
              <p className="text-orange-600 font-medium">Drop the image here...</p>
            ) : (
              <>
                <p className="text-gray-300 mb-2">
                  Drag & drop an image here, or click to select
                </p>
                <p className="text-sm text-gray-400">
                  Supports: JPEG, PNG, WebP (max 10MB, min 500x500px)
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    open();
                  }}
                  className="mt-4 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                  disabled={isProcessing || uploadProgress > 0}
                >
                  Choose File
                </button>
              </>
            )}
          </>
        )}
      </div>
      
      {/* File Info */}
      {previewUrl && (
        <div className="mt-4 p-3 bg-gray-700 rounded-lg">
          <h3 className="text-sm font-medium text-gray-300 mb-2">Preview</h3>
          <div className="flex items-center space-x-4">
            <img 
              src={previewUrl} 
              alt="Preview" 
              className="w-20 h-20 object-cover rounded-lg"
            />
            <div className="text-sm text-gray-300">
              <p>Ready for processing</p>
              <p className="text-xs text-gray-400 mt-1">Waiting for AI crop suggestions</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}