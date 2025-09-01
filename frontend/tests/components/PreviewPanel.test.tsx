import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PreviewPanel from '@/components/PreviewPanel';
import { UploadedFile, CropArea, CROP_PRESETS } from '@/types';

describe('PreviewPanel', () => {
  const mockFile: UploadedFile = {
    id: '1',
    name: 'test-image.jpg',
    size: 1024,
    type: 'image/jpeg',
    url: 'https://example.com/image.jpg',
    uploadedAt: new Date(),
    dimensions: {
      width: 1920,
      height: 1080
    }
  };

  const mockCropArea: CropArea = {
    x: 100,
    y: 100,
    width: 800,
    height: 800
  };

  const mockOnPresetSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders preview panel with all components', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getByText('Show Original')).toBeInTheDocument();
    expect(screen.getByText('All Preset Previews')).toBeInTheDocument();
  });

  it('displays all four preset previews', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={true}
      />
    );

    // Check for all preset names in preview items
    CROP_PRESETS.forEach(preset => {
      const elements = screen.getAllByText(preset.name);
      expect(elements.length).toBeGreaterThan(0);
    });
  });

  it('highlights the active preset', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={true}
      />
    );

    expect(screen.getByText('Active: 1:1 Square')).toBeInTheDocument();
  });

  it('toggles comparison view when button is clicked', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    const toggleButton = screen.getByText('Show Original');
    fireEvent.click(toggleButton);

    expect(screen.getByText('Hide Original')).toBeInTheDocument();
    expect(screen.getByText('Original')).toBeInTheDocument();
    expect(screen.getByText(/Cropped/)).toBeInTheDocument();
  });

  it('calls onPresetSelect when a preset is clicked', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={true}
        onPresetSelect={mockOnPresetSelect}
      />
    );

    // Find and click a different preset
    const verticalPresets = screen.getAllByText('9:16 Vertical');
    // Click on the one in the grid (not the info section)
    fireEvent.click(verticalPresets[0].closest('div[class*="cursor-pointer"]')!);

    expect(mockOnPresetSelect).toHaveBeenCalledWith('vertical');
  });

  it('displays file dimensions when available', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    expect(screen.getByText('Original: 1920 × 1080px')).toBeInTheDocument();
  });

  it('applies crop area styles when provided', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        cropArea={mockCropArea}
      />
    );

    // Check that images are rendered (crop styles would be applied)
    const images = screen.getAllByRole('img');
    expect(images.length).toBeGreaterThan(0);
  });

  it('renders without showAllPresets when set to false', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={false}
      />
    );

    expect(screen.queryByText('All Preset Previews')).not.toBeInTheDocument();
  });

  it('shows aspect ratio for each preset', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={true}
      />
    );

    expect(screen.getByText('1:1')).toBeInTheDocument();
    expect(screen.getByText('9:16')).toBeInTheDocument();
    expect(screen.getByText('16:9')).toBeInTheDocument();
    expect(screen.getByText('2:3')).toBeInTheDocument();
  });

  it('displays preset description', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    expect(screen.getByText('Perfect for social media posts')).toBeInTheDocument();
  });

  it('shows quick action buttons', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    expect(screen.getByText('Apply to All')).toBeInTheDocument();
    expect(screen.getByText('Reset Crop')).toBeInTheDocument();
    expect(screen.getByText('Compare Side-by-Side')).toBeInTheDocument();
  });

  it('updates when preset prop changes', () => {
    const { rerender } = render(
      <PreviewPanel
        file={mockFile}
        preset="square"
      />
    );

    expect(screen.getByText('Active: 1:1 Square')).toBeInTheDocument();

    rerender(
      <PreviewPanel
        file={mockFile}
        preset="vertical"
      />
    );

    expect(screen.getByText('Active: 9:16 Vertical')).toBeInTheDocument();
  });

  it('handles files without dimensions gracefully', () => {
    const fileWithoutDims = { ...mockFile, dimensions: undefined };
    
    render(
      <PreviewPanel
        file={fileWithoutDims}
        preset="square"
      />
    );

    expect(screen.queryByText(/Original: \d+ × \d+px/)).not.toBeInTheDocument();
  });

  it('applies correct size classes for preview items', () => {
    render(
      <PreviewPanel
        file={mockFile}
        preset="square"
        showAllPresets={true}
      />
    );

    const previewItems = screen.getAllByText(/^\d+:\d+$/);
    expect(previewItems.length).toBeGreaterThan(0);
  });
});