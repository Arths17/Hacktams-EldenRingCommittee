/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In production (Vercel), API routes are handled by vercel.json routing
    // In development, proxy to local FastAPI server
    const isDev = process.env.NODE_ENV !== 'production';
    
    if (!isDev) {
      return [];
    }
    
    return [
      {
        source: '/api/login',
        destination: 'http://localhost:8000/login',
      },
      {
        source: '/login',
        destination: 'http://localhost:8000/login',
      },
      {
        source: '/api/signup',
        destination: 'http://localhost:8000/api/signup',
      },
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
