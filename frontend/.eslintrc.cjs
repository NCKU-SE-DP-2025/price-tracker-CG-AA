module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
    "vue/setup-compiler-macros": true,
  },
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "espree",
    ecmaVersion: 13,
    sourceType: "module",
    extraFileExtensions: [".vue"],
  },
  extends: [
    "plugin:vue/vue3-recommended",
    "eslint:recommended",
    "prettier", // turns off stylistic rules; ESLint won't nag about spaces/newlines
  ],
  rules: {
    // Ban Options API; only allow <script setup> and Composition API
    "vue/component-api-style": ["error", ["script-setup", "composition"]],
  },
};
