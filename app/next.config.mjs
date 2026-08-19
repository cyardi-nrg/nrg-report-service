/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: { bodySizeLimit: '25mb' }, // real scanned documents/photos run large
  },
};

export default nextConfig;
