import React from 'react';
import { LayoutGrid, CheckCircle2, XCircle, AlertCircle, ArrowRight } from 'lucide-react';

export default function StructureAnalysis({ score, sectionDetails, sectionsMap }) {
  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-blue-600 uppercase tracking-wider">
            <LayoutGrid className="w-4 h-4" /> Section Completeness & Layout
          </div>
          <h3 className="text-2xl font-black text-slate-900 mt-1">Structure Score: {score}/100</h3>
        </div>
        <div className="px-4 py-2 rounded-xl bg-blue-50 text-blue-800 font-bold text-sm border border-blue-200">
          {score >= 85 ? 'Well Organized' : 'Needs Better Standardization'}
        </div>
      </div>

      {/* Sections Checklist Grid */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
        <h4 className="font-bold text-slate-900 text-lg">Detected Resume Sections</h4>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sectionDetails && sectionDetails.length > 0 ? (
            sectionDetails.map((sec, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border flex items-center justify-between transition ${
                  sec.found
                    ? 'bg-emerald-50/60 border-emerald-200 text-slate-900'
                    : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {sec.found ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  )}
                  <div>
                    <span className="text-sm font-bold">{sec.name}</span>
                    {sec.heading_used && sec.heading_used.toLowerCase() !== sec.name.toLowerCase() && (
                      <p className="text-xs text-amber-700 font-mono mt-0.5">
                        Header: "{sec.heading_used}"
                      </p>
                    )}
                  </div>
                </div>

                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    sec.found
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {sec.found ? 'Present' : 'Missing'}
                </span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">No section details available.</p>
          )}
        </div>
      </div>

      {/* Non-standard Heading Recommendations */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
        <h4 className="font-bold text-slate-900 text-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          Heading Standardization Recommendations
        </h4>

        <div className="space-y-3">
          {sectionDetails &&
          sectionDetails.filter((s) => s.recommendation).length > 0 ? (
            sectionDetails
              .filter((s) => s.recommendation)
              .map((s, idx) => (
                <div key={idx} className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 text-xs sm:text-sm text-amber-950 space-y-1">
                  <div className="flex items-center gap-2 font-bold text-slate-900">
                    <span>{s.name} Section</span>
                    <ArrowRight className="w-4 h-4 text-amber-600" />
                    <span className="text-amber-800 font-medium">{s.recommendation}</span>
                  </div>
                  <p className="text-slate-600 text-xs mt-1 leading-relaxed">
                    Recruiters and automated ATS scanners look for conventional section headings to parse information without data misclassification.
                  </p>
                </div>
              ))
          ) : (
            <p className="text-xs text-emerald-700 font-medium bg-emerald-50 p-3 rounded-xl border border-emerald-200">
              ✓ All detected section titles conform to standard resume naming conventions.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
