/**
 * Tests for ImageUploader component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageUploader from '@/components/ImageUploader';
import { UploadedFile } from '@/types';

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: jest.fn(),
}));

describe('ImageUploader', () => {
  const mockOnUpload = jest.fn();
  
  beforeEach(() => {
    mockOnUpload.mockClear();
    // Reset react-dropzone mock
    const { useDropzone } = require('react-dropzone');
    useDropzone.mockReturnValue({
      getRootProps: jest.fn(() => ({ onClick: jest.fn() })),
      getInputProps: jest.fn(() => ({ type: 'file', accept: 'image/*' })),
      isDragActive: false,
    });
  });

  it('renders upload interface correctly', () => {
    render(<ImageUploader onUpload={mockOnUpload} />);
    
    expect(screen.getByText('Upload Image')).toBeInTheDocument();
    expect(screen.getByText(/Drag & drop an image here/)).toBeInTheDocument();
    expect(screen.getByText(/Supports: JPEG, PNG, WebP/)).toBeInTheDocument();
    expect(screen.getByText('Choose File')).toBeInTheDocument();
  });

  it('shows drag active state', () => {
    const { useDropzone } = require('react-dropzone');
    useDropzone.mockReturnValue({
      getRootProps: jest.fn(() => ({})),
      getInputProps: jest.fn(() => ({})),
      isDragActive: true,
    });

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    expect(screen.getByText('Drop the image here...')).toBeInTheDocument();
  });

  it('displays error for invalid file size', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    // Simulate file rejection for size
    const rejectedFiles = [{
      errors: [{ code: 'file-too-large' }]
    }];
    
    dropHandler([], rejectedFiles);
    
    await waitFor(() => {
      expect(screen.getByText('File size must be less than 50MB')).toBeInTheDocument();
    });
  });

  it('displays error for invalid file type', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    // Simulate file rejection for type
    const rejectedFiles = [{
      errors: [{ code: 'file-invalid-type' }]
    }];
    
    dropHandler([], rejectedFiles);
    
    await waitFor(() => {
      expect(screen.getByText(/Please upload a valid image file/)).toBeInTheDocument();
    });
  });

  it('shows upload progress', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    // Mock Image constructor
    global.Image = jest.fn().mockImplementation(() => ({
      onload: null,
      onerror: null,
      src: '',
      width: 1000,
      height: 800,
    }));
    
    global.URL.createObjectURL = jest.fn(() => 'blob:test-url');
    global.URL.revokeObjectURL = jest.fn();

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    
    dropHandler([file], []);
    
    // Trigger image load
    const imageInstance = (global.Image as any).mock.results[0].value;
    imageInstance.onload();
    
    await waitFor(() => {
      expect(screen.getByText('Uploading...')).toBeInTheDocument();
    });
  });

  it('validates minimum image dimensions', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    // Mock Image with small dimensions
    global.Image = jest.fn().mockImplementation(() => ({
      onload: null,
      onerror: null,
      src: '',
      width: 400, // Less than 500
      height: 400, // Less than 500
    }));
    
    global.URL.createObjectURL = jest.fn(() => 'blob:test-url');
    global.URL.revokeObjectURL = jest.fn();

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    
    dropHandler([file], []);
    
    // Trigger image load
    const imageInstance = (global.Image as any).mock.results[0].value;
    imageInstance.onload();
    
    await waitFor(() => {
      expect(screen.getByText('Image must be at least 500x500 pixels')).toBeInTheDocument();
    });
    
    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it('calls onUpload with correct file data', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    // Mock Image with valid dimensions
    global.Image = jest.fn().mockImplementation(() => ({
      onload: null,
      onerror: null,
      src: '',
      width: 1000,
      height: 800,
    }));
    
    global.URL.createObjectURL = jest.fn(() => 'blob:test-url');
    global.URL.revokeObjectURL = jest.fn();

    // Mock setInterval
    jest.useFakeTimers();

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    Object.defineProperty(file, 'size', { value: 1024 * 5 }); // 5KB
    
    dropHandler([file], []);
    
    // Trigger image load
    const imageInstance = (global.Image as any).mock.results[0].value;
    imageInstance.onload();
    
    // Fast-forward through upload progress
    jest.runAllTimers();
    
    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'test.jpg',
          size: 1024 * 5,
          type: 'image/jpeg',
          url: 'blob:test-url',
          dimensions: {
            width: 1000,
            height: 800
          }
        })
      );
    });
    
    jest.useRealTimers();
  });

  it('disables upload when processing', () => {
    const { useDropzone } = require('react-dropzone');
    const dropzoneMock = jest.fn();
    
    useDropzone.mockImplementation(dropzoneMock);

    render(<ImageUploader onUpload={mockOnUpload} isProcessing={true} />);
    
    expect(dropzoneMock).toHaveBeenCalledWith(
      expect.objectContaining({
        disabled: true
      })
    );
  });

  it('shows success message after upload', async () => {
    const { useDropzone } = require('react-dropzone');
    let dropHandler: any;
    
    useDropzone.mockImplementation(({ onDrop }) => {
      dropHandler = onDrop;
      return {
        getRootProps: jest.fn(() => ({})),
        getInputProps: jest.fn(() => ({})),
        isDragActive: false,
      };
    });

    // Mock Image
    global.Image = jest.fn().mockImplementation(() => ({
      onload: null,
      onerror: null,
      src: '',
      width: 1000,
      height: 800,
    }));
    
    global.URL.createObjectURL = jest.fn(() => 'blob:test-url');
    jest.useFakeTimers();

    render(<ImageUploader onUpload={mockOnUpload} />);
    
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
    
    dropHandler([file], []);
    
    // Trigger image load
    const imageInstance = (global.Image as any).mock.results[0].value;
    imageInstance.onload();
    
    // Fast-forward through upload
    jest.runAllTimers();
    
    await waitFor(() => {
      expect(screen.getByText('Image uploaded successfully!')).toBeInTheDocument();
    });
    
    jest.useRealTimers();
  });
});
