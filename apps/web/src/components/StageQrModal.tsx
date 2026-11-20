"use client";

/**
 * StageQrModal — scannable QR of the live target URL so judges' phones become
 * the buyer persona. TODO(T9): polish backdrop/animation.
 */
import { QRCodeSVG } from "qrcode.react";

interface StageQrModalProps {
  open: boolean;
  onClose: () => void;
}

const TARGET = process.env.NEXT_PUBLIC_STAGE_TARGET_URL ?? "http://localhost:8001";

export default function StageQrModal({ open, onClose }: StageQrModalProps) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-obsidian/80"
      onClick={onClose}
    >
      <div
        className="flex flex-col items-center gap-4 rounded-lg border border-line bg-elevated p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <QRCodeSVG value={TARGET} size={220} bgColor="#EDEFF5" fgColor="#07080C" />
        <p className="font-mono text-sm text-ink-secondary">{TARGET}</p>
        <p className="font-mono text-xs text-accent-violet">
          SCAN FROM A PHONE → BECOME THE BUYER PERSONA
        </p>
      </div>
    </div>
  );
}
