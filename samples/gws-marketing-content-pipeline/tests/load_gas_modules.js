/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Apps Script Module Loader for Testing
 * apps-scripts/ 디렉터리의 9개 모듈을 가상 Apps Script 글로벌 스코프에 순차 로드한다.
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { createGasMockEnvironment } = require("./gas_mock");

const APPS_SCRIPTS_DIR = path.resolve(__dirname, "../apps-scripts");

const MODULE_FILES = [
  "Code_Config.js",
  "Code_Gemini.js",
  "Code_Prompts.js",
  "Code_Utils.js",
  "Code_Workspace.js",
  "Code_Content.js",
  "Code_Feedback.js",
  "Code_Sidebar.js",
  "Code_Menu.js"
];

function loadGasModules(customEnv = null) {
  const env = customEnv || createGasMockEnvironment();

  // Create Node vm context
  const sandbox = {
    ...env,
    console: console,
    JSON: JSON,
    Math: Math,
    Date: Date,
    parseInt: parseInt,
    parseFloat: parseFloat,
    isNaN: isNaN,
    isFinite: isFinite,
    encodeURIComponent: encodeURIComponent,
    decodeURIComponent: decodeURIComponent,
    RegExp: RegExp,
    Array: Array,
    Object: Object,
    String: String,
    Number: Number,
    Boolean: Boolean,
    Buffer: Buffer
  };

  const context = vm.createContext(sandbox);

  for (const file of MODULE_FILES) {
    const filePath = path.join(APPS_SCRIPTS_DIR, file);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Apps Script module not found: ${filePath}`);
    }
    const code = fs.readFileSync(filePath, "utf8");
    try {
      vm.runInContext(code, context, { filename: file });
    } catch (err) {
      throw new Error(`Failed to load ${file} into GAS test context: ${err.message}`);
    }
  }

  return { context, env };
}

module.exports = {
  loadGasModules,
  MODULE_FILES
};
