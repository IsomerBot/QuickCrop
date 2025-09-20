export type PhotoCategory = 'employee' | 'project';

// Preset identifiers (include both employee and project)
export type PresetId =
  | 'headshot'
  | 'full_body'
  | 'website'
  | 'proj_header'
  | 'proj_thumbnail'
  | 'proj_description';

export type ExportSize =
  | 'headshot'
  | 'avatar'
  | 'thumbnail'
  | 'website'
  | 'full_body'
  | 'proj_banner'
  | 'proj_thumbnail'
  | 'proj_description';

export interface CropPresetConfig {
  id: PresetId;
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
  preset: PresetId;
  outputUrl: string;
  processingTime: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Employee presets (existing behavior)
export const EMPLOYEE_PRESETS: CropPresetConfig[] = [
  {
    id: 'headshot',
    name: 'Headshot',
    aspectRatio: [1, 1],
    outputSizes: [
      { id: 'headshot', name: 'Headshot', size: [2000, 2000] },
      { id: 'thumbnail', name: 'Thumbnail', size: [500, 500] },
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
    description: 'Portrait crop with full-figure framing for marketing use'
  },
  {
    id: 'website',
    name: 'Website',
    aspectRatio: [4, 5],
    outputSizes: [
      { id: 'website', name: 'Website', size: [1600, 2000] }
    ],
    description: 'Portrait crop with upper-body framing for website use'
  }
];

// Project presets (new)
export const PROJECT_PRESETS: CropPresetConfig[] = [
  {
    id: 'proj_header',
    name: 'Website Header',
    aspectRatio: [16, 9],
    outputSizes: [
      { id: 'proj_header', name: 'Website Header', size: [2560, 1440] }
    ],
    description: 'Header image for experience page on website'
  },
  {
    id: 'proj_thumbnail',
    name: 'Website Thumbnail',
    aspectRatio: [1, 1],
    outputSizes: [
      { id: 'proj_thumbnail', name: 'Website Thumbnail', size: [500, 500] }
    ],
    description: 'Square image for experience navigation on website'
  },
  {
    id: 'proj_description',
    name: 'Project Description',
    aspectRatio: [11, 10],
    outputSizes: [
      { id: 'proj_description', name: 'Project Description', size: [1100, 1000] }
    ],
    description: 'Horizontal image for use in powerpoint project descriptions'
  }
];

export const PRESETS: Record<PhotoCategory, CropPresetConfig[]> = {
  employee: EMPLOYEE_PRESETS,
  project: PROJECT_PRESETS,
};

// Backwards compatibility for existing imports
export type CropPreset = PresetId;
export const CROP_PRESETS: CropPresetConfig[] = EMPLOYEE_PRESETS;

export function getPresets(category: PhotoCategory): CropPresetConfig[] {
  return PRESETS[category] || EMPLOYEE_PRESETS;
}
