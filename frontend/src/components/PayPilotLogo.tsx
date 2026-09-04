import React from 'react';

interface PayPilotLogoProps {
  size?: number;
  className?: string;
}

export default function PayPilotLogo({ size = 28, className = '' }: PayPilotLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
    >
      {/* Outer rounded container background */}
      <rect width="40" height="40" rx="10" fill="#0EA5E9" />
      
      {/* Shield/Pilot Wings & Payment Pulse Vector */}
      <path
        d="M20 7L31 12V21C31 27.5 26.3 33.4 20 35C13.7 33.4 9 27.5 9 21V12L20 7Z"
        fill="#0284C7"
      />
      
      {/* Upward Growth / Recovery Surge Arrow */}
      <path
        d="M15 24L20 18L25 24H21V28H19V24H15Z"
        fill="#FFFFFF"
      />
      
      {/* Sparkle/Pulse Node */}
      <circle cx="20" cy="14" r="2.5" fill="#38BDF8" />
    </svg>
  );
}
