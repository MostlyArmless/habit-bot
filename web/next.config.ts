import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  ...(process.env.NEXT_TURBOPACK_ROOT && {
    turbopack: {
      root: process.env.NEXT_TURBOPACK_ROOT,
    },
  }),
};

export default nextConfig;
