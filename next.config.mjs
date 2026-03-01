/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const fallbackBackendUrl = process.env.VERCEL
      ? 'https://campusfuel-production.up.railway.app'
      : 'http://localhost:8000';
    const rawBackendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || fallbackBackendUrl;
    const backendUrlWithProtocol = /^https?:\/\//i.test(rawBackendUrl)
      ? rawBackendUrl
      : `https://${rawBackendUrl}`;
    const backendUrl = backendUrlWithProtocol.replace(/\/+$/, '');
    return [
      {
        source: '/api/login',
        destination: `${backendUrl}/login`,
      },
      {
        source: '/api/signup',
        destination: `${backendUrl}/api/signup`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
