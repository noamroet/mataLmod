import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'standalone' bundles only what's needed — ideal for Docker / Railway.
  output: process.env.NEXT_OUTPUT === 'standalone' ? 'standalone' : undefined,

  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**.railway.app' },
      { protocol: 'https', hostname: '**.vercel.app' },
    ],
    formats: ['image/avif', 'image/webp'],
  },

  experimental: {
    typedRoutes: true,
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options',            value: 'DENY' },
          { key: 'X-Content-Type-Options',      value: 'nosniff' },
          { key: 'Strict-Transport-Security',   value: 'max-age=31536000; includeSubDomains' },
          { key: 'Referrer-Policy',             value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
