import React from 'react';
import { Target, CheckCircle2, XCircle, AlertTriangle, Tag, Sparkles, AlertCircle } from 'lucide-react';

export default function JobMatchAnalysis({ jobMatchScore, jobMatchDetails, keywords }) {
  const hasJobMatch = jobMatchScore !== null && jobMatchScore !== undefined;

  return (
    <div className="space-y-6 fade-in">
      {/* Job Match Section (if supplied) */}
      {hasJobMatch ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-600 uppercase tracking-wider">
                <Target className="w-4 h-4" /> Targeted Job Description Audit
              </div>
              <h3 className="text-2xl font-black text-slate-900 mt-1">
                Job Match Score: {jobMatchScore}%
              </h3>
            </div>
            <div className="px-4 py-2 rounded-xl bg-blue-50 text-blue-800 font-extrabold text-base border border-blue-200">
              {jobMatchScore >= 80 ? 'High Relevance' : jobMatchScore >= 60 ? 'Moderate Match' : 'Low Keyword Alignment'}
            </div>
          </div>

          {/* Matched / Missing / Partial Skills Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Matched Skills */}
            <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 font-bold text-emerald-900 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Matched Skills ({jobMatchDetails?.matched_skills?.length || 0})
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {jobMatchDetails?.matched_skills && jobMatchDetails.matched_skills.length > 0 ? (
                  jobMatchDetails.matched_skills.map((skill, idx) => (
                    <span key={idx} className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2 py-0.5 rounded">
                      ✓ {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400">None detected</span>
                )}
              </div>
            </div>

            {/* Missing Skills */}
            <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 font-bold text-rose-900 text-sm">
                <XCircle className="w-4 h-4 text-rose-600" />
                Missing Skills ({jobMatchDetails?.missing_skills?.length || 0})
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {jobMatchDetails?.missing_skills && jobMatchDetails.missing_skills.length > 0 ? (
                  jobMatchDetails.missing_skills.map((skill, idx) => (
                    <span key={idx} className="bg-rose-100 text-rose-800 text-xs font-semibold px-2 py-0.5 rounded">
                      ✗ {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400">None missing</span>
                )}
              </div>
            </div>

            {/* Partial Matches */}
            <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2 font-bold text-amber-900 text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Partial Matches ({jobMatchDetails?.partial_matches?.length || 0})
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {jobMatchDetails?.partial_matches && jobMatchDetails.partial_matches.length > 0 ? (
                  jobMatchDetails.partial_matches.map((skill, idx) => (
                    <span key={idx} className="bg-amber-100 text-amber-900 text-xs font-semibold px-2 py-0.5 rounded">
                      ⚠ {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400">None</span>
                )}
              </div>
            </div>
          </div>

          {/* Warning Banner */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-slate-600">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <p>
              <strong className="text-slate-800">Authenticity Reminder:</strong> Never invent skills or perform dishonest keyword stuffing. Only add missing technical skills to your resume if you genuinely have project or professional experience with them.
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-6 text-center text-slate-600 space-y-2">
          <Target className="w-8 h-8 mx-auto text-slate-400" />
          <h4 className="font-bold text-slate-800">No Target Job Description Provided</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Paste a targeted job description on the upload screen to unlock tailored match scores, missing skill alerts, and job keyword comparison.
          </p>
        </div>
      )}

      {/* Feature 8: Categorized Keyword Extraction */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
        <h4 className="font-bold text-slate-900 text-lg flex items-center gap-2">
          <Tag className="w-5 h-5 text-blue-600" />
          Extracted Technical Keyword Categorization
        </h4>

        {keywords?.categorized && Object.keys(keywords.categorized).length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(keywords.categorized).map(([category, list], cIdx) => (
              <div key={cIdx} className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-2">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  {category}
                </span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {list && list.length > 0 ? (
                    list.map((kw, kIdx) => (
                      <span key={kIdx} className="bg-white text-slate-800 border border-slate-200 text-xs font-medium px-2.5 py-1 rounded-lg">
                        {kw}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">None detected</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {keywords?.matched && keywords.matched.map((kw, idx) => (
              <span key={idx} className="bg-blue-50 text-blue-800 border border-blue-200 text-xs font-semibold px-2.5 py-1 rounded-lg">
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
