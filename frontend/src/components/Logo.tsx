export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg
      className="logo"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="DataLoom logo"
    >
      <defs>
        <linearGradient id="loom-gradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8b87ff" />
          <stop offset="1" stopColor="#d6c7ff" />
        </linearGradient>
      </defs>
      <rect x="14" y="14" width="9" height="36" rx="4" fill="url(#loom-gradient)" />
      <rect x="14" y="14" width="36" height="9" rx="4" fill="url(#loom-gradient)" opacity=".82" />
      <rect x="27" y="23" width="23" height="8" rx="4" fill="#ffffff" opacity=".94" />
      <rect x="41" y="23" width="9" height="27" rx="4" fill="url(#loom-gradient)" opacity=".7" />
      <rect x="23" y="37" width="27" height="8" rx="4" fill="#ffffff" opacity=".55" />
    </svg>
  );
}

