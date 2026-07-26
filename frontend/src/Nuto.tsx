type NutoPose = "hero" | "running" | "success" | "cautious";

export function Nuto({
  pose = "hero",
  className = "",
  label,
}: {
  pose?: NutoPose;
  className?: string;
  label?: string;
}) {
  const cautious = pose === "cautious";
  const success = pose === "success";
  const running = pose === "running";

  return (
    <svg
      className={`nuto nuto-${pose} ${className}`}
      viewBox="0 0 360 420"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <ellipse className="nuto-shadow" cx="180" cy="398" rx="104" ry="12" />
      <g className="nuto-leg">
        <path d="M133 319c-5 31-11 48-22 67M111 386c-13 1-25 5-29 14 17 7 38 6 51-1" />
        <path d="M226 319c5 31 11 48 22 67M248 386c13 1 25 5 29 14-17 7-38 6-51-1" />
      </g>
      <path className="nuto-body" d="M79 155c0-75 45-117 101-117s101 42 101 117c0 91-48 172-101 194-53-22-101-103-101-194Z" />
      <path className="nuto-face" d="M112 161c11-40 42-60 68-60s57 20 68 60c-5 69-35 116-68 132-33-16-63-63-68-132Z" />
      <g className="nuto-cap">
        <path d="M70 135c-4-67 42-111 110-111s114 44 110 111c-58-29-162-29-220 0Z" />
        <path d="M167 27c-4-15 1-25 14-34 16 12 21 24 14 37" />
        <path className="cap-detail" d="M92 105c12-17 24-17 36 0 12-17 24-17 36 0 12-17 24-17 36 0 12-17 24-17 36 0 12-17 24-17 36 0M111 73c11-15 22-15 33 0 11-15 22-15 33 0 11-15 22-15 33 0 11-15 22-15 33 0" />
      </g>
      <g className="nuto-eyes">
        <path className="nuto-brow" d={cautious ? "M139 170q15-11 28 1m27 0q13-12 28 0" : running ? "M137 174q15-15 29-2m28 0q14-13 29 2" : "M138 169q14-8 28 0m28 0q14-8 28 0"} />
        {success ? (
          <path d="M143 187q11 13 22 0m32 0q11 13 22 0" />
        ) : (
          <>
            <ellipse cx="155" cy="190" rx="8" ry="12" />
            <ellipse cx="207" cy="190" rx="8" ry="12" />
          </>
        )}
        <path className="nuto-mouth" d={cautious ? "M166 229q15-12 29 0" : "M164 216q16 20 33 0"} />
      </g>
      <g className="kernel-mark">
        <path d="M180 276c-24-26-35-10-30 12 4 18 17 29 30 36ZM180 276c24-26 35-10 30 12-4 18-17 29-30 36Z" />
        <path d="M180 279v40" />
      </g>

      {pose === "hero" && (
        <g className="nuto-arms">
          <path d="M88 213c-28 8-44 24-49 45M39 258l-10-11m10 11 3-15" />
          <path d="M269 207c30-4 51-18 65-39M334 168l-1-16m1 16 15-7" />
        </g>
      )}
      {running && (
        <g className="nuto-arms">
          <path d="M90 210c-24 14-36 38-36 68M270 210c24 14 36 38 36 68" />
          <rect className="press-top" x="55" y="266" width="250" height="24" rx="10" />
          <path className="press-handle" d="M180 266v-37m-28 0h56" />
          <path className="context-page" d="M100 301h160l-18 25H118Z" />
          <path className="context-lines" d="M129 312h101m-87 9h72" />
        </g>
      )}
      {success && (
        <g className="nuto-arms">
          <path d="M91 217c-31 5-48 25-54 52M269 217c31 5 48 25 54 52" />
          <path d="M37 269l-9-15m9 15 11-12m275 12 9-15m-9 15-11-12" />
          <path className="success-ray" d="M180 1v-19m-51 31-12-17m114 17 12-17" />
        </g>
      )}
      {cautious && (
        <g className="nuto-arms">
          <path d="M91 218c-30 2-50 20-63 44M28 262l-3-17m3 17 16-6" />
          <path d="M269 218c24 10 37 24 42 43M311 261l-10-11m10 11 4-15" />
          <path className="warning-mark" d="M313 127v-28m0 46v2" />
        </g>
      )}
    </svg>
  );
}

export function NutoMark({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <path fill="#b96f3f" stroke="#160f0a" strokeWidth="4" d="M14 27c0-14 8-23 18-23s18 9 18 23c0 16-9 29-18 34-9-5-18-18-18-34Z" />
      <path fill="#382318" stroke="#160f0a" strokeWidth="4" d="M11 25C9 13 18 5 32 5s23 8 21 20c-12-6-30-6-42 0Z" />
      <path fill="#f4e4c8" d="M21 30c2-8 7-12 11-12s9 4 11 12c-1 10-6 17-11 20-5-3-10-10-11-20Z" />
      <circle cx="27" cy="31" r="2.4" fill="#160f0a" />
      <circle cx="37" cy="31" r="2.4" fill="#160f0a" />
      <path d="M27 38q5 5 10 0" fill="none" stroke="#160f0a" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
