const config = {
  distDir: process.env.ORBIT_BUILD_DIR || '.next',
  poweredByHeader: false,
  output: 'standalone',
  generateBuildId: async () => process.env.ORBIT_RELEASE_SHA || 'local-development',
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'no-referrer' }
        ]
      }
    ];
  }
};
export default config;
