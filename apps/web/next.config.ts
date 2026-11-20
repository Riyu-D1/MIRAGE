import path from "path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },
  // Keep tracing inside apps/web even if stray lockfiles exist in parent dirs.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
