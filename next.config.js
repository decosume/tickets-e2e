/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  compiler: {
    styledComponents: true,
  },
  typescript: {
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Enable static exports for deployment
  trailingSlash: true,
  // Configure environment variables
  env: {
    NEXT_PUBLIC_AWS_REGION: process.env.AWS_REGION || 'us-west-2',
    NEXT_PUBLIC_AWS_PROFILE: process.env.AWS_PROFILE || 'AdministratorAccess12hr-100142810612',
  },
};

module.exports = nextConfig;
