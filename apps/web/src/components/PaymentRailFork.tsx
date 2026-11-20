"use client";

/**
 * PaymentRailFork — animated SVG 2-track diagram: the DECLARED rail shown to
 * reviewers vs the HIJACKED rail buyers actually ride to a different gateway.
 * TODO(T8): richer node art + animated dash-flow along both paths.
 */
import { motion } from "framer-motion";

import type { DivergenceReport } from "@/lib/types";

interface PaymentRailForkProps {
  divergence: DivergenceReport | null;
}

export default function PaymentRailFork({ divergence }: PaymentRailForkProps) {
  const declared = divergence?.claimed_gateway ?? "declared gateway";
  const hijacked = divergence?.buyer_gateway ?? "hidden gateway";
  const declaredDesc = divergence?.claimed_descriptor ?? "—";
  const hijackedDesc = divergence?.buyer_descriptor ?? "—";

  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <h3 className="mb-3 font-mono text-xs font-bold tracking-widest text-ink-secondary">
        PAYMENT-RAIL FORK
      </h3>
      <svg viewBox="0 0 640 240" className="w-full">
        {/* declared rail (top, cyan) */}
        <motion.path
          d="M 80 120 C 220 120 240 60 420 60"
          fill="none"
          stroke="#37E0D8"
          strokeWidth="2"
          pathLength={1}
          strokeDasharray={1}
          initial={{ strokeDashoffset: 1 }}
          animate={{ strokeDashoffset: 0 }}
          transition={{ duration: 1.2 }}
        />
        {/* hijacked rail (bottom, crimson) */}
        <motion.path
          d="M 80 120 C 220 120 240 180 420 180"
          fill="none"
          stroke="#FF3B5C"
          strokeWidth="2"
          pathLength={1}
          strokeDasharray={1}
          initial={{ strokeDashoffset: 1 }}
          animate={{ strokeDashoffset: 0 }}
          transition={{ duration: 1.2, delay: 0.2 }}
        />
        {/* source node */}
        <circle cx="80" cy="120" r="8" fill="#141824" stroke="#EDEFF5" strokeWidth="2" />
        <text x="80" y="150" textAnchor="middle" fill="#9AA3B8" fontSize="11" fontFamily="monospace">
          CHECKOUT
        </text>
        {/* declared gateway node */}
        <rect x="420" y="40" width="190" height="40" rx="6" fill="#0D0F16" stroke="#37E0D8" />
        <text x="515" y="58" textAnchor="middle" fill="#37E0D8" fontSize="11" fontFamily="monospace">
          DECLARED: {declared}
        </text>
        <text x="515" y="73" textAnchor="middle" fill="#9AA3B8" fontSize="10" fontFamily="monospace">
          {declaredDesc}
        </text>
        {/* hijacked gateway node */}
        <rect x="420" y="160" width="190" height="40" rx="6" fill="#0D0F16" stroke="#FF3B5C" />
        <text x="515" y="178" textAnchor="middle" fill="#FF3B5C" fontSize="11" fontFamily="monospace">
          HIJACKED: {hijacked}
        </text>
        <text x="515" y="193" textAnchor="middle" fill="#9AA3B8" fontSize="10" fontFamily="monospace">
          {hijackedDesc}
        </text>
      </svg>
    </div>
  );
}
