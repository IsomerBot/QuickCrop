/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: { domains: ['localhost'] },
  // Build a static site so FastAPI can serve it directly.
  output: 'export',
  // No rewrites needed: the browser will call /api/v1/* on the same origin,
  // which FastAPI serves.
  typescript: { ignoreBuildErrors: true }, // keep while types settle
};

module.exports = nextConfig;