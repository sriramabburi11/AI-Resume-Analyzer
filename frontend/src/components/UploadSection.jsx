import React, { useState, useRef } from 'react';
import { UploadCloud, FileCheck, X, AlertCircle, ArrowRight, Briefcase, Sparkles, Loader2 } from 'lucide-react';

const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadSection({ onAnalyze, isLoading, error, setError }) {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const validateAndSetFile = (selectedFile) => {
    setError(null);
    if (!selectedFile) return;

    if (selectedFile.type !== 'application/pdf' && !selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed. Please select a valid .pdf file.');
      return;
    }

    if (selectedFile.size > MAX_SIZE_BYTES) {
      setError(`File size exceeds ${MAX_SIZE_MB}MB limit. Please upload a smaller PDF.`);
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please upload a PDF resume before analyzing.');
      return;
    }
    onAnalyze(file, jobDescription);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Hero Header */}
      <div className="text-center mb-10 space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200/80 text-blue-700 text-xs font-medium">
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          <span>Next-Gen ATS Compatibility & Role Optimizer</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          AI Resume Analyzer & ATS Optimizer
        </h1>
        <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto font-normal">
          Analyze your resume, improve ATS compatibility score, and discover the exact roles that match your technical skills.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/50 p-6 sm:p-8 space-y-6">
        {/* PDF Upload Dropzone */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">
            Upload PDF Resume <span className="text-red-500">*</span>
          </label>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".pdf,application/pdf"
            className="hidden"
            id="pdf-upload-input"
          />

          {!file ? (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 sm:p-10 text-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? 'border-blue-500 bg-blue-50/50 scale-[1.005]'
                  : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50/80 bg-slate-50/30'
              }`}
            >
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-blue-100/80 flex items-center justify-center text-blue-600">
                <UploadCloud className="w-7 h-7" />
              </div>
              <p className="text-base font-semibold text-slate-800 mb-1">
                Drag and drop your PDF resume here, or <span className="text-blue-600 underline underline-offset-2">browse files</span>
              </p>
              <p className="text-xs text-slate-500">
                PDF format only. Maximum file size: {MAX_SIZE_MB}MB.
              </p>
            </div>
          ) : (
            <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 flex items-center justify-between transition-all fade-in">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-600 text-white flex items-center justify-center">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900">{file.name}</p>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      Uploaded successfully
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for analysis
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleRemoveFile}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-emerald-100 rounded-lg transition-colors"
                title="Remove file"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {/* Optional Job Description Area */}
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <label htmlFor="jd-textarea" className="block text-sm font-semibold text-slate-900 flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-slate-500" />
              Paste Target Job Description <span className="text-slate-400 text-xs font-normal">(Optional)</span>
            </label>
          </div>
          <p className="text-xs text-slate-500">
            Providing a job description enables detailed role-specific keyword comparison and match percentages.
          </p>
          <textarea
            id="jd-textarea"
            rows={4}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the target job requirements, qualifications, or tech stack here (optional)..."
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 resize-y transition"
          />
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 flex items-start gap-3 text-red-800 text-xs sm:text-sm fade-in">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Error processing request</p>
              <p className="mt-0.5 text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Action button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!file || isLoading}
            className={`w-full py-3.5 px-6 rounded-xl font-semibold text-white text-base shadow-lg transition-all flex items-center justify-center gap-2 ${
              !file || isLoading
                ? 'bg-slate-300 shadow-none cursor-not-allowed text-slate-500'
                : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.99] shadow-blue-500/25 cursor-pointer'
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Extracting Text & Analyzing Resume...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>Analyze Resume</span>
                <ArrowRight className="w-5 h-5 ml-1" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
