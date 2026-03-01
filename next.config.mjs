/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/login',
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
