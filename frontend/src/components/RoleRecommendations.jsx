import React from 'react';
import { Briefcase, Check, X, Award } from 'lucide-react';

export default function RoleRecommendations({ roles }) {
  if (!roles || roles.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500">
        No specific role recommendations generated.
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-lg flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
            <Award className="w-4 h-4" /> Role Match Engine
          </div>
          <h2 className="text-xl font-bold mt-1">Recommended Job Roles</h2>
          <p className="text-xs text-slate-400 mt-1">
            Roles prioritized based on multi-skill synthesis and technical stack evidence.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {roles.map((item, idx) => (
          <div
            key={idx}
            className="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-md transition p-6 flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                    <Briefcase className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">{item.role}</h3>
                    <p className="text-xs text-slate-500">{item.evidence || 'Skill alignment score'}</p>
                  </div>
                </div>
                <div className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-extrabold text-sm">
                  {item.match_percentage}% Match
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-100 rounded-full h-1.5 mt-3">
                <div
                  className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${item.match_percentage}%` }}
                />
              </div>

              {/* Reason */}
              <p className="text-xs sm:text-sm text-slate-600 mt-4 leading-relaxed">
                "{item.reason}"
              </p>

              {/* Matching Skills */}
              <div className="mt-4 space-y-2">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Matching Skills Found
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {item.matching_skills && item.matching_skills.length > 0 ? (
                    item.matching_skills.map((skill, sIdx) => (
                      <span
                        key={sIdx}
                        className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200"
                      >
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        {skill}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400">None detected</span>
                  )}
                </div>
              </div>

              {/* Missing Skills */}
              {item.missing_skills && item.missing_skills.length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Skills to Acquire / Strengthen
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {item.missing_skills.map((skill, mIdx) => (
                      <span
                        key={mIdx}
                        className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200"
                      >
                        <X className="w-3.5 h-3.5 text-slate-400" />
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
