import React from 'react';
import { ArrowDown, AlertTriangle, CheckCircle2, Zap, AlertCircle } from 'lucide-react';

export default function ExactImprovements({ improvements }) {
  if (!improvements || improvements.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500">
        No specific improvements generated.
      </div>
    );
  }

  const getPriorityBadge = (priority) => {
    const p = (priority || 'medium').toLowerCase();
    if (p === 'high') {
      return (
        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200 flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
          HIGH PRIORITY
        </span>
      );
    }
    if (p === 'medium') {
      return (
        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          MEDIUM PRIORITY
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1">
        <Zap className="w-3.5 h-3.5 text-blue-600" />
        LOW PRIORITY
      </span>
    );
  };

  return (
    <div className="space-y-6 fade-in">
      <div className="bg-blue-50/70 border border-blue-200 rounded-xl p-4 flex items-start gap-3 text-blue-900 text-xs sm:text-sm">
        <Zap className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-slate-900">Exact Resume Improvements</p>
          <p className="text-slate-600 mt-0.5">
            These actionable recommendations compare your current resume statements against recruiter standards. 
            <span className="font-semibold text-slate-800"> Note:</span> Add recommended experience only if you genuinely possess that background.
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {improvements.map((item, idx) => (
          <div key={idx} className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-4 hover:shadow-md transition">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Recommendation #{idx + 1}
              </span>
              {getPriorityBadge(item.priority)}
            </div>

            {/* Step 1: CURRENT */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                Current Statement in Resume
              </div>
              <div className="bg-slate-50 rounded-xl p-3 text-sm text-slate-700 italic border border-slate-200/60 font-mono">
                "{item.current}"
              </div>
            </div>

            <div className="flex justify-center my-1 text-slate-300">
              <ArrowDown className="w-4 h-4 text-slate-400" />
            </div>

            {/* Step 2: PROBLEM */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-rose-600 uppercase tracking-wider">
                <AlertCircle className="w-3.5 h-3.5" />
                Problem
              </div>
              <p className="text-sm text-slate-700 bg-rose-50/50 p-3 rounded-xl border border-rose-100">
                {item.problem}
              </p>
            </div>

            <div className="flex justify-center my-1 text-slate-300">
              <ArrowDown className="w-4 h-4 text-slate-400" />
            </div>

            {/* Step 3: RECOMMENDED CHANGE */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-700 uppercase tracking-wider">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Recommended Change
              </div>
              <div className="bg-emerald-50/80 rounded-xl p-3.5 text-sm font-medium text-emerald-950 border border-emerald-200 shadow-xs">
                {item.recommended_change}
              </div>
            </div>

            <div className="flex justify-center my-1 text-slate-300">
              <ArrowDown className="w-4 h-4 text-slate-400" />
            </div>

            {/* Step 4: REASON */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                Reason & Value
              </div>
              <p className="text-xs sm:text-sm text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200">
                {item.reason}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
