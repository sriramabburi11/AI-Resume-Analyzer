import React, { useState, useEffect } from 'react';
import {
  History,
  FileText,
  Trash2,
  ExternalLink,
  Award,
  Calendar,
  Briefcase,
  AlertCircle,
  Loader2,
  RotateCcw,
  Search,
  ShieldCheck,
  Zap,
  LayoutGrid
} from 'lucide-react';
import { fetchHistory, fetchHistoryDetail, deleteHistoryItem } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function HistorySection({ onSelectAnalysis, onUploadNew }) {
  const { session } = useAuth();
  const token = session?.access_token;

  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [openingId, setOpeningId] = useState(null);

  const loadHistory = async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHistory(token);
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history:', err);
      setError(err.message || 'Could not retrieve your resume analysis history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [token]);

  const handleDelete = async (e, id, resumeName) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete the analysis record for "${resumeName || 'this resume'}"?`)) {
      return;
    }

    setDeletingId(id);
    try {
      await deleteHistoryItem(id, token);
      setHistory(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      alert(`Failed to delete record: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleOpen = async (id) => {
    setOpeningId(id);
    try {
      const detail = await fetchHistoryDetail(id, token);
      if (detail && detail.analysis_summary) {
        // Construct the full object for Dashboard consumption
        const fullAnalysis = {
          ...detail.analysis_summary,
          id: detail.id,
          filename: detail.resume_name || detail.analysis_summary.filename,
          saved_analysis_id: detail.id,
          saved_to_history: true
        };
        onSelectAnalysis(fullAnalysis);
      }
    } catch (err) {
      alert(`Could not open analysis: ${err.message}`);
    } finally {
      setOpeningId(null);
    }
  };

  // Filter history by search query
  const filteredHistory = history.filter(item => {
    const q = searchQuery.toLowerCase();
    const nameMatch = (item.resume_name || '').toLowerCase().includes(q);
    const roleMatch = (item.job_title || '').toLowerCase().includes(q);
    return nameMatch || roleMatch;
  });

  const getScoreColorClass = (score) => {
    if (score >= 80) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (score >= 65) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6 fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 flex items-center gap-1">
              <History className="w-3.5 h-3.5" /> Saved Analyses
            </span>
            <span className="text-xs text-slate-400">
              {history.length} {history.length === 1 ? 'record' : 'records'}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Analysis History
          </h1>
          <p className="text-xs sm:text-sm text-slate-500">
            View past ATS compatibility audits, structural breakdowns, and recommended changes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadHistory}
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition cursor-pointer"
            title="Refresh history"
          >
            <RotateCcw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={onUploadNew}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-sm transition cursor-pointer"
          >
            <FileText className="w-4 h-4" />
            <span>Analyze New Resume</span>
          </button>
        </div>
      </div>

      {/* Search Input Bar (if history > 0) */}
      {history.length > 0 && (
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search saved analyses by resume file name or targeted role..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
          />
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3 text-red-800 text-xs sm:text-sm">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Unable to load history</p>
            <p className="mt-0.5 text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="py-16 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-500">Loading analysis history...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && history.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <History className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">No Previous Analyses Yet</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Upload your first PDF resume to run a comprehensive ATS evaluation, calculate your keyword match, and get tailored improvements.
            </p>
          </div>
          <button
            type="button"
            onClick={onUploadNew}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/20 transition cursor-pointer"
          >
            <FileText className="w-4 h-4" />
            <span>Upload Resume Now</span>
          </button>
        </div>
      )}

      {/* History Grid */}
      {!loading && filteredHistory.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredHistory.map((item) => {
            const formattedDate = new Date(item.created_at).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            });

            const isOpeningThis = openingId === item.id;
            const isDeletingThis = deletingId === item.id;

            return (
              <div
                key={item.id}
                onClick={() => handleOpen(item.id)}
                className="bg-white rounded-2xl border border-slate-200/90 p-5 hover:border-blue-300 hover:shadow-md transition-all flex flex-col justify-between cursor-pointer group"
              >
                <div className="space-y-3">
                  {/* Top row: Filename & Delete Action */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 truncate">
                      <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                        <FileText className="w-4 h-4" />
                      </div>
                      <span className="font-bold text-sm text-slate-900 truncate" title={item.resume_name}>
                        {item.resume_name || 'Resume Analysis'}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, item.id, item.resume_name)}
                      disabled={isDeletingThis}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                      title="Delete record"
                    >
                      {isDeletingThis ? (
                        <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>

                  {/* Target role or inferred role */}
                  {item.job_title && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-600">
                      <Briefcase className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span className="truncate">{item.job_title}</span>
                    </div>
                  )}

                  {/* Score Pills Overview */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2 text-center">
                      <div className="text-[10px] uppercase font-bold text-slate-500">ATS</div>
                      <div className={`text-base font-extrabold ${item.ats_score >= 80 ? 'text-emerald-600' : item.ats_score >= 65 ? 'text-amber-600' : 'text-red-600'}`}>
                        {item.ats_score ?? '--'}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2 text-center">
                      <div className="text-[10px] uppercase font-bold text-slate-500">Structure</div>
                      <div className="text-base font-extrabold text-slate-800">
                        {item.structure_score ?? '--'}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2 text-center">
                      <div className="text-[10px] uppercase font-bold text-slate-500">Quality</div>
                      <div className="text-base font-extrabold text-slate-800">
                        {item.content_score ?? '--'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom row: Date & Open CTA */}
                <div className="pt-4 mt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{formattedDate}</span>
                  </div>

                  <span className="font-semibold text-blue-600 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    {isOpeningThis ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Opening...</span>
                      </>
                    ) : (
                      <>
                        <span>View</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </>
                    )}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* No search matches */}
      {!loading && history.length > 0 && filteredHistory.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
          No analyses matched your query "{searchQuery}".
        </div>
      )}
    </div>
  );
}
