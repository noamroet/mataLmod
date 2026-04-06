import createNextIntlPlugin from 'next-intl/plugin';
import type { NextConfig } from 'next';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  // ── Output ─────────────────────────────────────────────────────────────────
  // 'standalone' bundles only what's needed — ideal for Docker / Railway.
  // Vercel ignores this (it manages bundling itself).
  output: process.env.NEXT_OUTPUT === 'standalone' ? 'standalone' : undefined,

  // ── Image optimisation ─────────────────────────────────────────────────────
  images: {
    // Allow images served from the API origin (institution logos if added later)
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.railway.app',
      },
      {
        protocol: 'https',
        hostname: '**.vercel.app',
      },
    ],
    // Serve next-gen formats
    formats: ['image/avif', 'image/webp'],
  },

  // ── Experimental ───────────────────────────────────────────────────────────
  experimental: {
    typedRoutes: true,
  },

  // ── Headers ────────────────────────────────────────────────────────────────
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Prevent embedding in iframes (clickjacking protection)
          { key: 'X-Frame-Options',       value: 'DENY'              },
          // Block MIME-type sniffing
          { key: 'X-Content-Type-Options', value: 'nosniff'           },
          // Enable strict HTTPS (1 year)
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
          // Referrer policy
          { key: 'Referrer-Policy',        value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
