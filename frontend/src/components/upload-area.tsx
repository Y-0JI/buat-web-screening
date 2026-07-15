"use client";

import { useRef, useState, useEffect } from "react";

interface UploadAreaProps {
  onFileSelect: (file: File) => void;
  disabled: boolean;
}

export function UploadArea({ onFileSelect, disabled }: UploadAreaProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/jpg"].includes(file.type)) {
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(file));
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="mt-4">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => !disabled && inputRef.current?.click()}
        className="border-2 border-dashed border-zinc-700 hover:border-blue-600 rounded-2xl p-4 text-center cursor-pointer transition-colors"
      >
        {preview ? (
          <img
            src={preview}
            alt="Preview"
            className="max-h-48 mx-auto rounded-xl object-contain"
          />
        ) : (
          <div className="text-zinc-500 text-sm py-2">
            <span className="block text-emerald-400 text-lg mb-1">+</span>
            Upload chart atau order book (PNG/JPG)
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          className="hidden"
          disabled={disabled}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}
