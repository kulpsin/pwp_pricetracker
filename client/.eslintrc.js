module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: "eslint:recommended",
  parserOptions: {
    ecmaVersion: 12,
    sourceType: "module",
  },
  ignorePatterns: ["**/*.min.js"],
  rules: {
    "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "no-console": "warn",
    "no-var": "error",
    "prefer-const": "error",
    "eqeqeq": ["error", "always"],
    "curly": ["error", "all"],
    "no-with": "error",
    "no-throw-literal": "error",
    "prefer-arrow-callback": "warn",
  },
};
