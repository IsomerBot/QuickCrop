'use client';

import React from 'react';
import type { PhotoCategory } from '@/types';

interface CategoryModalProps {
  open: boolean;
  onSelect: (category: PhotoCategory) => void;
  onCancel?: () => void;
}

export default function CategoryModal({ open, onSelect, onCancel }: CategoryModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-xl font-semibold text-white mb-2">What kind of photo is this?</h2>
        <p className="text-gray-400 text-sm mb-5">Choose the workflow so we can apply the right presets and naming.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            onClick={() => onSelect('employee')}
            className="p-4 rounded-lg border border-gray-600 hover:border-orange-500 hover:bg-gray-800 text-left transition-colors"
          >
            <div className="text-white font-medium">Employee</div>
            <div className="text-gray-400 text-sm">Headshot, Website, Full Body</div>
          </button>
          <button
            onClick={() => onSelect('project')}
            className="p-4 rounded-lg border border-gray-600 hover:border-orange-500 hover:bg-gray-800 text-left transition-colors"
          >
            <div className="text-white font-medium">Project</div>
            <div className="text-gray-400 text-sm">Website Header, Website Thumbnail, Project Description</div>
          </button>
        </div>
        <div className="mt-4 text-right">
          <button onClick={onCancel} className="text-sm text-gray-400 hover:text-gray-200">Cancel</button>
        </div>
      </div>
    </div>
  );
}
