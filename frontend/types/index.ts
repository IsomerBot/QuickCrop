export type CropPreset = 'headshot' | 'full_body' | 'website';
export type ExportSize = 'headshot' | 'avatar' | 'website' | 'full_body';

export interface CropPresetConfig {
  id: CropPreset;
  name: string;
  aspectRatio: [number, number];
  outputSizes?: Array<{
    id: ExportSize;
    name: string;
    size: [number, number];
  }>;
  description: string;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  uploadedAt?: Date;
  dimensions?: {
    width: number;
    height: number;
  };
  file_id?: string;
  upload_id?: string;
}

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ProcessingResult {
  fileId: string;
  preset: CropPreset;
  outputUrl: string;
  processingTime: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export const CROP_PRESETS: CropPresetConfig[] = [
  {
    id: 'headshot',
    name: 'Headshot',
    aspectRatio: [1, 1],
    outputSizes: [
      { id: 'headshot', name: 'Headshot', size: [2000, 2000] },
      { id: 'avatar', name: 'Avatar', size: [300, 300] }
    ],
    description: 'Square crop for professional headshots and avatars'
  },
  {
    id: 'full_body',
    name: 'Full Body',
    aspectRatio: [17, 20],
    outputSizes: [
      { id: 'full_body', name: 'Full Body', size: [3400, 4000] }
    ],
    description: 'Portrait crop (3400x4000) with full-figure framing for professional photos'
  },
  {
    id: 'website',
    name: 'Website',
    aspectRatio: [4, 5],
    outputSizes: [
      { id: 'website', name: 'Website', size: [1600, 2000] }
    ],
    description: 'Portrait crop (1600x2000) with upper-body framing for website headers'
  }
];