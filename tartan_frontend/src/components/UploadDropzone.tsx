/**
 * =============================================================================
 * UPLOAD DROPZONE COMPONENT
 * =============================================================================
 *
 * A drag-and-drop file upload area with file list display.
 *
 * FEATURES:
 * - Drag and drop files into the zone
 * - Click to browse files
 * - File type validation (pdf, doc, docx, txt, md)
 * - File size validation (max 20MB)
 * - Display uploaded files with remove button
 * - Error states for invalid files
 *
 * PROPS:
 * - files: array of currently uploaded files
 * - onFilesChange: function to update the files array
 * - disabled: boolean to disable uploads during loading
 * =============================================================================
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import "./UploadDropzone.css";

// -----------------------------------------------------------------------------
// CONSTANTS
// -----------------------------------------------------------------------------

/** Maximum file size in bytes (20MB) */
const MAX_FILE_SIZE = 20 * 1024 * 1024;

/** Allowed file extensions */
const ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "txt", "md"];

/** Allowed MIME types */
const ALLOWED_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
];

// -----------------------------------------------------------------------------
// TYPE DEFINITIONS
// -----------------------------------------------------------------------------

export type UploadedFile = {
  id: string;
  name: string;
  size: number;
  type: string;
};

export interface UploadDropzoneProps {
  /** Currently uploaded files */
  files: UploadedFile[];
  /** Function to update files (add/remove) */
  onFilesChange: (files: UploadedFile[]) => void;
  /** Disable uploads during loading */
  disabled?: boolean;
}

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------------------------

/**
 * Format file size for display (e.g., "1.5 MB")
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Get file extension from filename
 */
function getFileExtension(filename: string): string {
  return filename.split(".").pop()?.toLowerCase() || "";
}

/**
 * Check if a file type is allowed
 */
function isFileTypeAllowed(file: File): boolean {
  const extension = getFileExtension(file.name);
  return ALLOWED_EXTENSIONS.includes(extension) || ALLOWED_TYPES.includes(file.type);
}

/**
 * Generate a stable id (works even if crypto.randomUUID is unavailable)
 */
function makeId(): string {
  // Prefer crypto.randomUUID when available
  const c: any = globalThis as any;
  if (c?.crypto?.randomUUID) return c.crypto.randomUUID();
  // Fallback
  return `f_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

// -----------------------------------------------------------------------------
// COMPONENT
// -----------------------------------------------------------------------------

export function UploadDropzone({ files, onFilesChange, disabled = false }: UploadDropzoneProps) {
  // State: is user dragging over the dropzone?
  const [isDragOver, setIsDragOver] = useState(false);

  // State: error message to display
  const [error, setError] = useState<string | null>(null);

  // Ref: hidden file input element
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Ref: error timer so we can clear it
  const errTimerRef = useRef<number | null>(null);

  const acceptAttr = useMemo(() => ".pdf,.doc,.docx,.txt,.md", []);

  useEffect(() => {
    return () => {
      if (errTimerRef.current) {
        window.clearTimeout(errTimerRef.current);
        errTimerRef.current = null;
      }
    };
  }, []);

  function setTimedError(msg: string) {
    setError(msg);
    if (errTimerRef.current) window.clearTimeout(errTimerRef.current);
    errTimerRef.current = window.setTimeout(() => setError(null), 5000);
  }

  // ---------------------------------------------------------------------------
  // FILE VALIDATION & PROCESSING
  // ---------------------------------------------------------------------------

  /**
   * Validate and process files before adding them
   */
  const processFiles = (fileList: FileList | File[]) => {
    const newFiles: UploadedFile[] = [];
    const errors: string[] = [];

    Array.from(fileList).forEach((file) => {
      // Check file type
      if (!isFileTypeAllowed(file)) {
        errors.push(`"${file.name}" is not a supported file type`);
        return;
      }

      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`"${file.name}" exceeds 20MB limit`);
        return;
      }

      // Check for duplicates (by name)
      if (files.some((f) => f.name === file.name)) {
        errors.push(`"${file.name}" is already uploaded`);
        return;
      }

      // File is valid, add it
      newFiles.push({
        id: makeId(),
        name: file.name,
        size: file.size,
        type: file.type,
      });
    });

    if (errors.length > 0) setTimedError(errors.join(". "));

    if (newFiles.length > 0) {
      onFilesChange([...files, ...newFiles]);
    }
  };

  // ---------------------------------------------------------------------------
  // EVENT HANDLERS
  // ---------------------------------------------------------------------------

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) processFiles(droppedFiles);
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles && selectedFiles.length > 0) processFiles(selectedFiles);
    e.target.value = "";
  };

  const handleBrowseClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleRemoveFile = (fileId: string) => {
    onFilesChange(files.filter((f) => f.id !== fileId));
    setError(null);
  };

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------

  return (
    <div className="upload-dropzone">
      <label className="upload-dropzone__label">Additional Context (Optional)</label>

      <div
        className={[
          "upload-dropzone__zone",
          isDragOver ? "upload-dropzone__zone--drag-over" : "",
          disabled ? "upload-dropzone__zone--disabled" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload files by dragging or clicking"
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleBrowseClick();
          }
        }}
      >
        <svg
          className="upload-dropzone__icon"
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>

        <p className="upload-dropzone__text">
          <span className="upload-dropzone__text-primary">Drag & drop files here</span>
          <span className="upload-dropzone__text-secondary">or click to browse</span>
        </p>

        <p className="upload-dropzone__hint">Supports PDF, DOC, DOCX, TXT, MD (max 20MB each)</p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="upload-dropzone__input"
        onChange={handleFileInputChange}
        accept={acceptAttr}
        multiple
        disabled={disabled}
        aria-hidden="true"
      />

      {error && (
        <div className="upload-dropzone__error" role="alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {files.length > 0 && (
        <div className="upload-dropzone__files">
          <h4 className="upload-dropzone__files-title">Uploaded Files ({files.length})</h4>
          <ul className="upload-dropzone__file-list">
            {files.map((file) => (
              <li key={file.id} className="upload-dropzone__file-item">
                <svg
                  className="upload-dropzone__file-icon"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>

                <div className="upload-dropzone__file-info">
                  <span className="upload-dropzone__file-name">{file.name}</span>
                  <span className="upload-dropzone__file-size">{formatFileSize(file.size)}</span>
                </div>

                <button
                  type="button"
                  className="upload-dropzone__file-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile(file.id);
                  }}
                  disabled={disabled}
                  aria-label={`Remove ${file.name}`}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
