import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextCoreWebVitals,
  { rules: { "@next/next/no-html-link-for-pages": "off" } },
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
];

export default config;