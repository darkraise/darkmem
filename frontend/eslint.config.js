import js from "@eslint/js"
import globals from "globals"
import tseslint from "typescript-eslint"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"
import prettier from "eslint-config-prettier"

export default tseslint.config(
  { ignores: ["dist", "src/routeTree.gen.ts"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  prettier,
  {
    // Downgraded error -> warn by T1.58 (retire demo mode as the default):
    // 82 files still import src/demo/ (70 production, 12 test), and each
    // binding task (T1.59, T1.60, T1.63, ...) removes its own surface's
    // imports rather than this task absorbing all of them at once. T1.64
    // is expected to flip this back to error once the last binding task lands.
    files: [
      "src/routes/**/*.tsx",
      "src/features/**/*.{ts,tsx}",
      "src/hooks/**/*.ts",
      "src/lib/**/*.ts",
      "src/components/**/*.{ts,tsx}",
    ],
    rules: {
      "no-restricted-imports": [
        "warn",
        {
          patterns: [
            { group: ["@/demo/*", "../demo/*", "../../demo/*"], message: "Production code may not import from src/demo/ — that path is for Storybook and demo-mode Playwright specs only." },
          ],
        },
      ],
    },
  },
)
