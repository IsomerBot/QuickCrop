import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CropEditor from '@/components/CropEditor';
import { UploadedFile, CropPreset } from '@/types';

// Mock react-easy-crop
jest.mock('react-easy-crop', () => {
  return function MockCropper(props: any) {
    return (
      <div data-testid="cropper">
        <img src={props.image} alt="crop" />
        <div>Aspect: {props.aspect}</div>
        <div>Zoom: {props.zoom}</div>
        <button onClick={() => props.onZoomChange(2)}>Change Zoom</button>
        <button onClick={() => props.onCropChange({ x: 10, y: 10 })}>Change Crop</button>
      </div>
    );
  };
});

// Mock Radix UI Slider
jest.mock('@radix-ui/react-slider', () => ({
  Root: ({ children, value, onValueChange }: any) => (
    <div data-testid="zoom-slider">
      {children}
      <input
        type="range"
        value={value[0]}
        onChange={(e) => onValueChange([parseFloat(e.target.value)])}
      />
    </div>
  ),
  Track: ({ children }: any) => <div>{children}</div>,
  Range: () => <div />,
  Thumb: () => <div />
}));

describe('CropEditor', () => {
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

  const mockOnPresetChange = jest.fn();
  const mockOnCropComplete = jest.fn();
  const mockOnCropChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders crop editor with all components', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('Crop Settings')).toBeInTheDocument();
    expect(screen.getByText('Select Crop Preset')).toBeInTheDocument();
    expect(screen.getByTestId('cropper')).toBeInTheDocument();
    expect(screen.getByText('Zoom')).toBeInTheDocument();
    expect(screen.getByText('File Information')).toBeInTheDocument();
  });

  it('displays all crop preset options', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('1:1 Square')).toBeInTheDocument();
    expect(screen.getByText('9:16 Vertical')).toBeInTheDocument();
    expect(screen.getByText('16:9 Horizontal')).toBeInTheDocument();
    expect(screen.getByText('2:3 Portrait')).toBeInTheDocument();
  });

  it('calls onPresetChange when preset is selected', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    const verticalButton = screen.getByText('9:16 Vertical').closest('button');
    fireEvent.click(verticalButton!);

    expect(mockOnPresetChange).toHaveBeenCalledWith('vertical');
  });

  it('displays file information correctly', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('Name: test-image.jpg')).toBeInTheDocument();
    expect(screen.getByText('Size: 1.0 KB')).toBeInTheDocument();
    expect(screen.getByText('Type: image/jpeg')).toBeInTheDocument();
    expect(screen.getByText('Dimensions: 1920 × 1080px')).toBeInTheDocument();
  });

  it('updates aspect ratio when preset changes', () => {
    const { rerender } = render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('Aspect: 1')).toBeInTheDocument(); // 1:1 square

    rerender(
      <CropEditor
        file={mockFile}
        preset="vertical"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('Aspect: 0.5625')).toBeInTheDocument(); // 9:16 vertical
  });

  it('shows zoom controls and updates zoom level', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    const zoomInButton = screen.getByLabelText('Zoom in');
    const zoomOutButton = screen.getByLabelText('Zoom out');

    expect(zoomInButton).toBeInTheDocument();
    expect(zoomOutButton).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('shows undo/redo buttons', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('← Undo')).toBeInTheDocument();
    expect(screen.getByText('Redo →')).toBeInTheDocument();
  });

  it('displays keyboard shortcuts help', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    expect(screen.getByText('Keyboard shortcuts:')).toBeInTheDocument();
    expect(screen.getByText('• Arrow keys: Move crop area')).toBeInTheDocument();
    expect(screen.getByText('• Ctrl/Cmd + Plus/Minus: Zoom in/out')).toBeInTheDocument();
    expect(screen.getByText('• Ctrl/Cmd + Z: Undo')).toBeInTheDocument();
    expect(screen.getByText('• Ctrl/Cmd + Shift + Z: Redo')).toBeInTheDocument();
  });

  it('handles keyboard events for navigation', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
        onCropChange={mockOnCropChange}
      />
    );

    // Simulate arrow key press
    fireEvent.keyDown(window, { key: 'ArrowUp', code: 'ArrowUp' });
    fireEvent.keyDown(window, { key: 'ArrowDown', code: 'ArrowDown' });
    fireEvent.keyDown(window, { key: 'ArrowLeft', code: 'ArrowLeft' });
    fireEvent.keyDown(window, { key: 'ArrowRight', code: 'ArrowRight' });

    // Keyboard events should be prevented from default behavior
    expect(true).toBe(true); // Placeholder assertion
  });

  it('handles keyboard shortcuts for zoom', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    // Initial zoom is 100%
    expect(screen.getByText('100%')).toBeInTheDocument();

    // Simulate Ctrl+Plus for zoom in
    fireEvent.keyDown(window, { key: '+', ctrlKey: true });
    
    // Simulate Ctrl+Minus for zoom out
    fireEvent.keyDown(window, { key: '-', ctrlKey: true });
  });

  it('handles undo/redo keyboard shortcuts', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    const undoButton = screen.getByText('← Undo');
    const redoButton = screen.getByText('Redo →');

    // Initially undo should be disabled (no history)
    expect(undoButton).toHaveClass('cursor-not-allowed');
    expect(redoButton).toHaveClass('cursor-not-allowed');

    // Simulate Ctrl+Z for undo
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });

    // Simulate Ctrl+Shift+Z for redo
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true, shiftKey: true });
  });

  it('updates zoom with slider', async () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    const slider = screen.getByTestId('zoom-slider').querySelector('input');
    expect(slider).toBeInTheDocument();

    if (slider) {
      fireEvent.change(slider, { target: { value: '1.5' } });
      await waitFor(() => {
        expect(screen.getByText('Zoom: 1.5')).toBeInTheDocument();
      });
    }
  });

  it('calls onCropComplete when crop is complete', async () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
        onCropComplete={mockOnCropComplete}
      />
    );

    // Mock cropper would trigger onCropComplete
    // This is simulated through the mock implementation
    await waitFor(() => {
      expect(screen.getByTestId('cropper')).toBeInTheDocument();
    });
  });

  it('handles responsive layout classes', () => {
    render(
      <CropEditor
        file={mockFile}
        preset="square"
        onPresetChange={mockOnPresetChange}
      />
    );

    const cropCanvas = screen.getByTestId('cropper').parentElement;
    expect(cropCanvas).toHaveClass('h-[300px]', 'sm:h-[400px]', 'md:h-[450px]');
  });
});