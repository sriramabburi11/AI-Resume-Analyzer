import React from 'react';
import { AlertTriangle, CheckCircle2, XCircle, ShieldAlert, Info } from 'lucide-react';

export default function AtsAnalysis({ score, issues }) {
  const getStatusIcon = (type) => {
    const t = (type || 'warning').toLowerCase();
    if (t === 'pass') {
      return <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />;
    }
    if (t === 'fail') {
      return <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />;
    }
    return <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />;
  };

  const getStatusBadge = (type) => {
    const t = (type || 'warning').toLowerCase();
    if (t === 'pass') return <span className="text-xs font-bold text-emerald-700 bg-emerald-100/80 px-2.5 py-0.5 rounded">PASS</span>;
    if (t === 'fail') return <span className="text-xs font-bold text-rose-700 bg-rose-100/80 px-2.5 py-0.5 rounded">FAIL</span>;
    return <span className="text-xs font-bold text-amber-800 bg-amber-100/80 px-2.5 py-0.5 rounded">WARNING</span>;
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Disclaimer Card */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-3 text-amber-900">
        <ShieldAlert className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="font-bold text-base text-amber-950">Estimated ATS Compatibility</h3>
          <p className="text-xs sm:text-sm text-amber-800 mt-1 leading-relaxed">
            This estimation checks for structural parsing hurdles in Applicant Tracking Systems (e.g., multi-column layouts, non-standard section titles, contact readability). Note: High scores improve parsing accuracy but do not guarantee passing an automated screen.
          </p>
        </div>
      </div>

      {/* Score overview bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">ATS Parsing Readiness</span>
          <h4 className="text-2xl font-black text-slate-900 mt-0.5">Estimated ATS Score: {score}/100</h4>
        </div>
        <div className="w-full sm:w-1/2">
          <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
            <span>Parsing Risk</span>
            <span>{score >= 85 ? 'Low Risk' : score >= 70 ? 'Moderate Risk' : 'High Risk'}</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
            <div
              className={`h-3 rounded-full transition-all duration-700 ${
                score >= 85 ? 'bg-emerald-500' : score >= 70 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>
      </div>

      {/* Issues Breakdown List */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
        <h4 className="font-bold text-slate-900 text-lg flex items-center gap-2">
          <Info className="w-5 h-5 text-blue-600" />
          ATS Checkpoint Audit
        </h4>

        <div className="divide-y divide-slate-100">
          {issues && issues.length > 0 ? (
            issues.map((item, idx) => (
              <div key={idx} className="py-4 first:pt-0 last:pb-0 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  {getStatusIcon(item.type)}
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-slate-900 text-sm">{item.issue}</p>
                    </div>
                    {item.detail && (
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">{item.detail}</p>
                    )}
                  </div>
                </div>
                <div className="flex-shrink-0">
                  {getStatusBadge(item.type)}
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 py-2">No critical ATS issues detected.</p>
          )}
        </div>
      </div>
    </div>
  );
}
