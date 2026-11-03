export function PhonwaLogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <defs>
        <filter id="logoGrain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="1.2" />
        </filter>
      </defs>
      <g filter="url(#logoGrain)">
        <ellipse cx="32" cy="36" rx="18" ry="16" fill="#10A3A4" stroke="#2A2218" strokeWidth="2.2" />
        <circle cx="32" cy="24" r="12" fill="#FFE8C8" stroke="#2A2218" strokeWidth="2.2" />
        <path
          d="M18 24c-5 1-8 6-7 10 2 2 5 1 7-1"
          fill="none"
          stroke="#FF9933"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <path
          d="M46 24c5 1 8 6 7 10-2 2-5 1-7-1"
          fill="none"
          stroke="#FF9933"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="27" cy="23" r="2.2" fill="#2A2218" />
        <circle cx="37" cy="23" r="2.2" fill="#2A2218" />
        <path d="M27 29c2.4 2 7.6 2 10 0" fill="none" stroke="#2A2218" strokeWidth="1.8" strokeLinecap="round" />
        <rect x="27" y="40" width="10" height="8" rx="2" fill="#FF9933" stroke="#2A2218" strokeWidth="1.6" />
        <path d="M22 12l3-6M32 9l0-6M42 12l-2-6" stroke="#FFC83B" strokeWidth="2" strokeLinecap="round" />
      </g>
    </svg>
  );
}

export function RobotAssistant({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 360 420" className={className} role="img" aria-label="Friendly Phonwa AI assistant waving">
      <defs>
        <filter id="crayon">
          <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="2" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.6" xChannelSelector="R" yChannelSelector="G" />
        </filter>
        <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#E8EEF5" />
          <stop offset="100%" stopColor="#A8B6C8" />
        </linearGradient>
      </defs>

      {/* doodle accents */}
      <g opacity="0.9" fill="none" stroke="#1E5A9B" strokeWidth="2.4" strokeLinecap="round">
        <path d="M42 120c18-10 28-8 38 4" />
        <path d="M48 136c14-6 24-4 34 6" />
        <path d="M300 150c-16-12-28-10-40 2" />
        <path d="M308 168c-12-8-24-6-34 4" />
      </g>
      <g fill="#FFC83B">
        <path d="M68 68l3 9 9 3-9 3-3 9-3-9-9-3 9-3z" />
        <path d="M300 78l2.5 7 7 2.5-7 2.5-2.5 7-2.5-7-7-2.5 7-2.5z" />
        <path d="M310 250l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" />
      </g>
      <g stroke="#C45C26" strokeWidth="2" fill="none" strokeLinecap="round">
        <rect x="36" y="250" width="34" height="48" rx="8" transform="rotate(-12 53 274)" />
        <circle cx="53" cy="266" r="5" />
        <path d="M45 286h16M45 294h12" />
      </g>

      <g filter="url(#crayon)" className="origin-center">
        {/* body */}
        <ellipse cx="180" cy="275" rx="78" ry="90" fill="#D7E8F0" stroke="#2A2218" strokeWidth="3" />
        {/* Nehru jacket / vest */}
        <path
          d="M128 230c10 55 20 90 52 98 32-8 42-43 52-98-18 10-34 14-52 14s-34-4-52-14z"
          fill="#FF9933"
          stroke="#2A2218"
          strokeWidth="3"
        />
        <path d="M180 244v84" stroke="#2A2218" strokeWidth="2.2" />
        <circle cx="168" cy="268" r="4" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.4" />
        <circle cx="192" cy="268" r="4" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.4" />

        {/* arms */}
        <path
          d="M108 250c-28 8-42 34-34 58"
          fill="none"
          stroke="#2A2218"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M108 250c-28 8-42 34-34 58"
          fill="none"
          stroke="#C5D7E4"
          strokeWidth="6"
          strokeLinecap="round"
        />
        {/* waving arm */}
        <path
          d="M252 248c36-28 58-18 62 10"
          fill="none"
          stroke="#2A2218"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M252 248c36-28 58-18 62 10"
          fill="none"
          stroke="#C5D7E4"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <circle cx="318" cy="258" r="14" fill="#FFE8C8" stroke="#2A2218" strokeWidth="2.5" />

        {/* head */}
        <circle cx="180" cy="150" r="72" fill="#F4F7FA" stroke="#2A2218" strokeWidth="3.2" />
        <ellipse cx="180" cy="158" rx="54" ry="48" fill="#FFEFD8" stroke="#2A2218" strokeWidth="2" opacity="0.55" />

        {/* headphones */}
        <path
          d="M108 150c0-44 32-74 72-74s72 30 72 74"
          fill="none"
          stroke="#1E5A9B"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <rect x="88" y="138" width="28" height="40" rx="12" fill="#10A3A4" stroke="#2A2218" strokeWidth="2.4" />
        <rect x="244" y="138" width="28" height="40" rx="12" fill="#10A3A4" stroke="#2A2218" strokeWidth="2.4" />
        <path d="M258 178c18 22 20 42 8 58" fill="none" stroke="#2A2218" strokeWidth="3" strokeLinecap="round" />
        <circle cx="262" cy="244" r="10" fill="#FFC83B" stroke="#2A2218" strokeWidth="2.2" />

        {/* face */}
        <circle cx="158" cy="148" r="8" fill="#2A2218" />
        <circle cx="202" cy="148" r="8" fill="#2A2218" />
        <circle cx="160.5" cy="145.5" r="2.4" fill="#fff" />
        <circle cx="204.5" cy="145.5" r="2.4" fill="#fff" />
        <path d="M164 172c10 12 24 12 34 0" fill="none" stroke="#C45C26" strokeWidth="3.2" strokeLinecap="round" />
        <circle cx="146" cy="164" r="7" fill="#FFB4A2" opacity="0.7" />
        <circle cx="214" cy="164" r="7" fill="#FFB4A2" opacity="0.7" />

        {/* antenna */}
        <path d="M180 78v-18" stroke="#2A2218" strokeWidth="3" strokeLinecap="round" />
        <circle cx="180" cy="52" r="8" fill="#FF9933" stroke="#2A2218" strokeWidth="2.2" />
      </g>

      {/* speech bubbles */}
      <g className="animate-phonwa-pop" style={{ transformOrigin: "70px 90px" }}>
        <path
          d="M28 48h86c10 0 16 7 16 16v22c0 9-6 16-16 16H70l-14 14v-14H28c-10 0-16-7-16-16V64c0-9 6-16 16-16z"
          fill="#FFF8E8"
          stroke="#2A2218"
          strokeWidth="2.4"
        />
        <text x="40" y="88" fontFamily="Nunito, sans-serif" fontSize="16" fontWeight="700" fill="#1E5A9B">
          Namaste!
        </text>
      </g>
      <g>
        <path
          d="M250 42h78c9 0 14 6 14 13v18c0 7-5 13-14 13h-28l-10 10v-10h-40c-9 0-14-6-14-13V55c0-7 5-13 14-13z"
          fill="#FFF1D6"
          stroke="#2A2218"
          strokeWidth="2.2"
        />
        <text x="262" y="74" fontFamily="Nunito, sans-serif" fontSize="14" fontWeight="700" fill="#C45C26">
          Haanji!
        </text>
      </g>
      <g>
        <path
          d="M248 320h86c9 0 14 6 14 13v18c0 7-5 13-14 13h-34l-12 12v-12h-40c-9 0-14-6-14-13v-18c0-7 5-13 14-13z"
          fill="#E7F7F7"
          stroke="#2A2218"
          strokeWidth="2.2"
        />
        <text x="262" y="352" fontFamily="Nunito, sans-serif" fontSize="14" fontWeight="700" fill="#10A3A4">
          Suno Ji!
        </text>
      </g>
    </svg>
  );
}

export function MarketplaceScene({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 560 420" className={className} role="img" aria-label="Indian kirana shop with Phonwa AI on the counter">
      <defs>
        <filter id="marketCrayon">
          <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="1.4" />
        </filter>
      </defs>

      {/* sky wash */}
      <rect width="560" height="420" fill="#FDFBF7" />
      <path d="M0 250h560" stroke="#E8DFCF" strokeWidth="2" />

      <g filter="url(#marketCrayon)">
        {/* buildings */}
        <rect x="20" y="120" width="90" height="140" fill="#F3D7B5" stroke="#2A2218" strokeWidth="2.2" />
        <rect x="34" y="138" width="22" height="22" fill="#FFF8E8" stroke="#2A2218" strokeWidth="1.6" />
        <rect x="70" y="138" width="22" height="22" fill="#FFF8E8" stroke="#2A2218" strokeWidth="1.6" />
        <rect x="34" y="176" width="22" height="22" fill="#D6EEF2" stroke="#2A2218" strokeWidth="1.6" />
        <text x="28" y="118" fontFamily="Nunito, sans-serif" fontSize="11" fontWeight="700" fill="#1E5A9B">
          Cyber Cafe
        </text>

        <rect x="430" y="140" width="110" height="120" fill="#E8C9A8" stroke="#2A2218" strokeWidth="2.2" />
        <rect x="448" y="158" width="28" height="24" fill="#FFF8E8" stroke="#2A2218" strokeWidth="1.6" />
        <rect x="492" y="158" width="28" height="24" fill="#FFF8E8" stroke="#2A2218" strokeWidth="1.6" />
        <path d="M430 140h110l-12-22H442z" fill="#C45C26" stroke="#2A2218" strokeWidth="2" />

        {/* trees */}
        <circle cx="130" cy="220" r="18" fill="#7CB89A" stroke="#2A2218" strokeWidth="2" />
        <path d="M130 230v30" stroke="#2A2218" strokeWidth="3" />
        <circle cx="410" cy="230" r="16" fill="#6AAA88" stroke="#2A2218" strokeWidth="2" />
        <path d="M410 238v22" stroke="#2A2218" strokeWidth="3" />

        {/* bunting */}
        <path d="M150 108c40 18 80 18 120 0 40 18 80 18 120 0" fill="none" stroke="#2A2218" strokeWidth="2" />
        <path d="M170 112l8 16 8-16" fill="#FF9933" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M210 118l8 16 8-16" fill="#10A3A4" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M250 112l8 16 8-16" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M290 118l8 16 8-16" fill="#1E5A9B" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M330 112l8 16 8-16" fill="#C45C26" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M370 118l8 16 8-16" fill="#FF9933" stroke="#2A2218" strokeWidth="1.2" />

        {/* couple walking */}
        <g transform="translate(400 250)">
          <circle cx="0" cy="0" r="8" fill="#F4C7A5" stroke="#2A2218" strokeWidth="1.6" />
          <path d="M0 8v28M-10 18l10 6 10-8" stroke="#2A2218" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M-6 36l-4 18M6 36l6 18" stroke="#2A2218" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M-12 12h24v20h-24z" fill="#1E5A9B" opacity="0.85" />
          <circle cx="28" cy="-2" r="8" fill="#F4C7A5" stroke="#2A2218" strokeWidth="1.6" />
          <path d="M28 6v28M18 16l10 6 10-6" stroke="#2A2218" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M22 34l-2 18M34 34l4 18" stroke="#2A2218" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M16 10h24v24H16z" fill="#FF9933" opacity="0.9" />
        </g>

        {/* auto rickshaw */}
        <g className="animate-phonwa-rickshaw" style={{ transformOrigin: "80px 320px" }}>
          <path d="M40 320h70l18-28h36v44H40z" fill="#FFC83B" stroke="#2A2218" strokeWidth="2.4" />
          <path d="M128 292h34l12 20v24h-46z" fill="#2F9E44" stroke="#2A2218" strokeWidth="2.4" />
          <circle cx="62" cy="348" r="14" fill="#2A2218" />
          <circle cx="62" cy="348" r="6" fill="#E8DFCF" />
          <circle cx="150" cy="348" r="14" fill="#2A2218" />
          <circle cx="150" cy="348" r="6" fill="#E8DFCF" />
          <rect x="136" y="300" width="18" height="14" rx="2" fill="#D6EEF2" stroke="#2A2218" strokeWidth="1.4" />
        </g>

        {/* kirana shop */}
        <rect x="160" y="170" width="230" height="150" fill="#FFF4E0" stroke="#2A2218" strokeWidth="3" />
        <path d="M148 170h254l-16-34H164z" fill="#1E5A9B" stroke="#2A2218" strokeWidth="2.6" />
        <text
          x="178"
          y="156"
          fontFamily="Playpen Sans, cursive"
          fontSize="22"
          fontWeight="700"
          fill="#FFF8E8"
        >
          Sharma Kirana
        </text>

        {/* shelves / jars / packets */}
        <rect x="176" y="190" width="70" height="56" fill="#F7E2C2" stroke="#2A2218" strokeWidth="1.8" />
        <rect x="182" y="198" width="16" height="22" rx="3" fill="#FF9933" stroke="#2A2218" strokeWidth="1.2" />
        <rect x="202" y="198" width="16" height="22" rx="3" fill="#10A3A4" stroke="#2A2218" strokeWidth="1.2" />
        <rect x="222" y="198" width="16" height="22" rx="3" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.2" />
        <path d="M186 228h10M206 228h10M226 228h10" stroke="#C45C26" strokeWidth="3" strokeLinecap="round" />

        <rect x="260" y="188" width="54" height="64" fill="#EAF6F6" stroke="#2A2218" strokeWidth="1.8" />
        <ellipse cx="274" cy="210" rx="8" ry="14" fill="#E36A6A" stroke="#2A2218" strokeWidth="1.2" />
        <ellipse cx="292" cy="210" rx="8" ry="14" fill="#6AAA88" stroke="#2A2218" strokeWidth="1.2" />
        <rect x="268" y="230" width="38" height="12" rx="2" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.2" />

        {/* hanging snack packets */}
        <g>
          <path d="M330 186v18" stroke="#2A2218" strokeWidth="1.5" />
          <rect x="320" y="204" width="20" height="26" rx="3" fill="#FF9933" stroke="#2A2218" strokeWidth="1.5" />
          <path d="M356 186v18" stroke="#2A2218" strokeWidth="1.5" />
          <rect x="346" y="204" width="20" height="26" rx="3" fill="#1E5A9B" stroke="#2A2218" strokeWidth="1.5" />
          <path d="M330 186h26" stroke="#2A2218" strokeWidth="1.5" />
        </g>

        {/* counter */}
        <rect x="168" y="268" width="214" height="42" fill="#E0B58A" stroke="#2A2218" strokeWidth="2.4" />
        <rect x="168" y="300" width="214" height="20" fill="#C99664" stroke="#2A2218" strokeWidth="2" />

        {/* shopkeeper */}
        <g transform="translate(220 230)">
          <circle cx="0" cy="0" r="16" fill="#F0C3A0" stroke="#2A2218" strokeWidth="2" />
          <path d="M-18 -4c4-18 32-18 36 0" fill="#E4572E" stroke="#2A2218" strokeWidth="2" />
          <path d="M-18 -2c8-10 28-10 36 0" fill="none" stroke="#FFC83B" strokeWidth="3" />
          <path d="M-10 6h8M2 6h8" stroke="#2A2218" strokeWidth="2" strokeLinecap="round" />
          <path d="M-6 14c4 4 10 4 14 0" fill="none" stroke="#2A2218" strokeWidth="2" strokeLinecap="round" />
          <path d="M-14 10c-4 2-8 2-10 0" stroke="#2A2218" strokeWidth="2" strokeLinecap="round" />
          <path d="M14 10c4 2 8 2 10 0" stroke="#2A2218" strokeWidth="2" strokeLinecap="round" />
          <path d="M-22 20h44v48H-22z" fill="#1E5A9B" stroke="#2A2218" strokeWidth="2" />
          <path d="M-8 20v20M8 20v20" stroke="#FFC83B" strokeWidth="2" />
        </g>

        {/* customer */}
        <g transform="translate(320 248)">
          <circle cx="0" cy="0" r="13" fill="#E8B892" stroke="#2A2218" strokeWidth="2" />
          <path d="M-16 14h32v40H-16z" fill="#10A3A4" stroke="#2A2218" strokeWidth="2" />
          <path d="M-10 8c4 5 16 5 20 0" fill="none" stroke="#2A2218" strokeWidth="2" strokeLinecap="round" />
        </g>

        {/* tiny robot on counter + phone */}
        <g transform="translate(350 248)">
          <rect x="0" y="20" width="22" height="32" rx="4" fill="#2A2218" stroke="#2A2218" strokeWidth="1.5" />
          <rect x="2" y="22" width="18" height="24" rx="2" fill="#9FD8DA" />
          <circle cx="48" cy="8" r="14" fill="#F4F7FA" stroke="#2A2218" strokeWidth="2" />
          <rect x="36" y="22" width="24" height="28" rx="6" fill="#FF9933" stroke="#2A2218" strokeWidth="2" />
          <path d="M34 8c0-12 8-18 14-18s14 6 14 18" fill="none" stroke="#1E5A9B" strokeWidth="4" strokeLinecap="round" />
          <circle cx="43" cy="7" r="2" fill="#2A2218" />
          <circle cx="53" cy="7" r="2" fill="#2A2218" />
          <path d="M44 13c3 3 8 3 11 0" fill="none" stroke="#C45C26" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="62" cy="18" r="4" fill="#FFC83B" stroke="#2A2218" strokeWidth="1.2" />
        </g>
      </g>

      {/* ground scribble */}
      <path
        d="M16 360c40-8 80 8 120 0s80 8 120 0 80 8 120 0 80 8 120 0"
        fill="none"
        stroke="#D9CFBE"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
