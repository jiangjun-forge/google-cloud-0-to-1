/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Apps Script Mock Runtime for Node.js
 * 로컬 Node.js 환경에서 Apps Script 9대 코어 모듈을 100% 가상 실행하고
 * 단위 테스트할 수 있도록 지원하는 초경량 메모리 모의 객체 런타임이다.
 */

const crypto = require("crypto");

class MockRange {
  constructor(sheet, startRow, startCol, numRows = 1, numCols = 1) {
    this.sheet = sheet;
    this.startRow = startRow;
    this.startCol = startCol;
    this.numRows = numRows;
    this.numCols = numCols;
    this.background = "";
    this.fontWeight = "";
    this.horizontalAlignment = "";
    this.verticalAlignment = "";
    this.wrapStrategy = "";
    this.numberFormat = "";
    this.richText = null;
  }

  getValue() {
    return this.sheet.getCellValue(this.startRow, this.startCol);
  }

  getValues() {
    const res = [];
    for (let r = 0; r < this.numRows; r++) {
      const row = [];
      for (let c = 0; c < this.numCols; c++) {
        row.push(this.sheet.getCellValue(this.startRow + r, this.startCol + c));
      }
      res.push(row);
    }
    return res;
  }

  setValue(val) {
    this.sheet.setCellValue(this.startRow, this.startCol, val);
    return this;
  }

  setValues(matrix) {
    for (let r = 0; r < matrix.length; r++) {
      for (let c = 0; c < matrix[r].length; c++) {
        this.sheet.setCellValue(this.startRow + r, this.startCol + c, matrix[r][c]);
      }
    }
    return this;
  }

  setBackground(color) {
    this.background = color;
    for (let r = 0; r < this.numRows; r++) {
      for (let c = 0; c < this.numCols; c++) {
        this.sheet.setCellStyle(this.startRow + r, this.startCol + c, "background", color);
      }
    }
    return this;
  }

  setFontWeight(weight) {
    this.fontWeight = weight;
    for (let r = 0; r < this.numRows; r++) {
      for (let c = 0; c < this.numCols; c++) {
        this.sheet.setCellStyle(this.startRow + r, this.startCol + c, "fontWeight", weight);
      }
    }
    return this;
  }

  setHorizontalAlignment(align) {
    this.horizontalAlignment = align;
    for (let r = 0; r < this.numRows; r++) {
      for (let c = 0; c < this.numCols; c++) {
        this.sheet.setCellStyle(this.startRow + r, this.startCol + c, "horizontalAlignment", align);
      }
    }
    return this;
  }

  setVerticalAlignment(align) {
    this.verticalAlignment = align;
    for (let r = 0; r < this.numRows; r++) {
      for (let c = 0; c < this.numCols; c++) {
        this.sheet.setCellStyle(this.startRow + r, this.startCol + c, "verticalAlignment", align);
      }
    }
    return this;
  }

  setWrapStrategy(strategy) {
    this.wrapStrategy = strategy;
    for (let r = 0; r < this.numRows; r++) {
      for (let c = 0; c < this.numCols; c++) {
        this.sheet.setCellStyle(this.startRow + r, this.startCol + c, "wrapStrategy", strategy);
      }
    }
    return this;
  }

  setNumberFormat(fmt) {
    this.numberFormat = fmt;
    return this;
  }

  setRichTextValue(richText) {
    this.richText = richText;
    this.sheet.setCellValue(this.startRow, this.startCol, richText.text);
    return this;
  }

  breakApart() {
    return this;
  }

  clearFormat() {
    this.background = "";
    this.fontWeight = "";
    this.horizontalAlignment = "";
    this.verticalAlignment = "";
    this.wrapStrategy = "";
    return this;
  }
}

class MockSheet {
  constructor(name, spreadsheet) {
    this.name = name;
    this.spreadsheet = spreadsheet;
    this.grid = {}; // 'r,c' -> value
    this.cellStyles = {}; // 'r,c' -> { background, horizontalAlignment, ... }
    this.columnWidths = {};
    this.frozenRows = 0;
    this.ranges = [];
  }

  setCellStyle(r, c, prop, val) {
    const key = `${r},${c}`;
    if (!this.cellStyles[key]) this.cellStyles[key] = {};
    this.cellStyles[key][prop] = val;
  }

  getCellStyle(r, c, prop) {
    const key = `${r},${c}`;
    return this.cellStyles[key] ? this.cellStyles[key][prop] : undefined;
  }

  getName() {
    return this.name;
  }

  setName(newName) {
    this.name = newName;
    return this;
  }

  getCellValue(r, c) {
    const key = `${r},${c}`;
    return this.grid[key] !== undefined ? this.grid[key] : "";
  }

  setCellValue(r, c, val) {
    const key = `${r},${c}`;
    this.grid[key] = val;
  }

  getLastRow() {
    let maxR = 0;
    for (const key of Object.keys(this.grid)) {
      const [r] = key.split(",").map(Number);
      if (r > maxR) maxR = r;
    }
    return maxR;
  }

  getLastColumn() {
    let maxC = 0;
    for (const key of Object.keys(this.grid)) {
      const [, c] = key.split(",").map(Number);
      if (c > maxC) maxC = c;
    }
    return maxC;
  }

  getRange(a1OrRow, col, numRows, numCols) {
    if (typeof a1OrRow === "string") {
      // Simple A1 parser
      const a1 = a1OrRow.toUpperCase();
      if (a1.includes(":")) {
        const [p1, p2] = a1.split(":");
        const c1 = p1.charCodeAt(0) - 64;
        const r1 = parseInt(p1.slice(1), 10);
        const c2 = p2.charCodeAt(0) - 64;
        const r2 = parseInt(p2.slice(1), 10);
        const rng = new MockRange(this, r1, c1, r2 - r1 + 1, c2 - c1 + 1);
        this.ranges.push(rng);
        return rng;
      }
      const c = a1.charCodeAt(0) - 64;
      const r = parseInt(a1.slice(1), 10);
      const rng = new MockRange(this, r, c, 1, 1);
      this.ranges.push(rng);
      return rng;
    }
    const rng = new MockRange(this, a1OrRow, col, numRows || 1, numCols || 1);
    this.ranges.push(rng);
    return rng;
  }

  setColumnWidth(col, width) {
    this.columnWidths[col] = width;
    return this;
  }

  setFrozenRows(n) {
    this.frozenRows = n;
    return this;
  }

  appendRow(rowValues) {
    const nextRow = this.getLastRow() + 1;
    for (let c = 0; c < rowValues.length; c++) {
      this.setCellValue(nextRow, c + 1, rowValues[c]);
    }
  }

  clearFormats() {
    return this;
  }
}

class MockSpreadsheet {
  constructor() {
    this.name = "마케팅 콘텐츠 컨트롤 타워";
    this.sheets = [new MockSheet("Sheet1", this)];
    this.activeSheet = this.sheets[0];
  }

  getName() {
    return this.name;
  }

  setName(n) {
    this.name = n;
    return this;
  }

  getId() {
    return "spreadsheet_mock_123";
  }

  getSheets() {
    return this.sheets;
  }

  getSheetByName(name) {
    return this.sheets.find(s => s.getName() === name) || null;
  }

  insertSheet(name, index) {
    const sheet = new MockSheet(name, this);
    if (index !== undefined) {
      this.sheets.splice(index, 0, sheet);
    } else {
      this.sheets.push(sheet);
    }
    return sheet;
  }

  setActiveSheet(sheet) {
    this.activeSheet = sheet;
    return sheet;
  }

  getActiveSheet() {
    return this.activeSheet;
  }
}

class MockFile {
  constructor(name, content = "", mimeType = "application/octet-stream") {
    this.id = "file_" + Math.random().toString(36).substring(2, 9);
    this.name = name;
    this.content = content;
    this.mimeType = mimeType;
  }

  getId() { return this.id; }
  getName() { return this.name; }
  getUrl() { return `https://drive.google.com/open?id=${this.id}`; }
  getMimeType() { return this.mimeType; }
  isTrashed() { return false; }
  getSize() { return Buffer.byteLength(this.content, "utf8"); }
  getBlob() {
    return {
      getDataAsString: () => this.content,
      getBytes: () => Buffer.from(this.content),
      getContentType: () => this.mimeType,
      getName: () => this.name
    };
  }
  setContent(c) { this.content = c; return this; }
  makeCopy(name, destination) {
    const copy = new MockFile(name, this.content, this.mimeType);
    if (destination) destination.files.push(copy);
    return copy;
  }
}

class MockIterator {
  constructor(items) {
    this.items = [...items];
    this.idx = 0;
  }
  hasNext() { return this.idx < this.items.length; }
  next() { return this.items[this.idx++]; }
}

class MockFolder {
  constructor(name, parent = null, folderRegistry = null, fileRegistry = null) {
    this.id = "folder_" + Math.random().toString(36).substring(2, 9);
    this.name = name;
    this.parent = parent;
    this.folderRegistry = folderRegistry || (parent ? parent.folderRegistry : null);
    this.fileRegistry = fileRegistry || (parent ? parent.fileRegistry : null);
    this.folders = [];
    this.files = [];

    if (this.folderRegistry) {
      this.folderRegistry[this.id] = this;
    }
  }

  getId() { return this.id; }
  getName() { return this.name; }
  getUrl() { return `https://drive.google.com/drive/folders/${this.id}`; }
  isTrashed() { return false; }

  createFolder(name) {
    const sub = new MockFolder(name, this, this.folderRegistry, this.fileRegistry);
    this.folders.push(sub);
    return sub;
  }

  createFile(name, content, mimeType) {
    const f = new MockFile(name, content, mimeType);
    this.files.push(f);
    if (this.fileRegistry) {
      this.fileRegistry[f.getId()] = f;
    }
    return f;
  }

  getFolders() { return new MockIterator(this.folders); }
  getFiles() { return new MockIterator(this.files); }

  getFoldersByName(name) {
    return new MockIterator(this.folders.filter(f => f.getName() === name));
  }

  getFilesByName(name) {
    return new MockIterator(this.files.filter(f => f.getName() === name));
  }

  getFilesByType(mimeType) {
    return new MockIterator(this.files.filter(f => f.getMimeType() === mimeType));
  }
}

class MockDocument {
  constructor(name) {
    this.id = "doc_" + Math.random().toString(36).substring(2, 9);
    this.name = name;
    this.bodyText = "";
  }
  getId() { return this.id; }
  getName() { return this.name; }
  getUrl() { return `https://docs.google.com/document/d/${this.id}/edit`; }
  getBody() {
    return {
      getText: () => this.bodyText,
      appendParagraph: (text) => {
        this.bodyText += (this.bodyText ? "\n" : "") + text;
        return {
          setHeading: () => {},
          setFontFamily: () => {}
        };
      },
      appendTable: () => {},
      replaceText: (search, rep) => {
        this.bodyText = this.bodyText.replaceAll(new RegExp(search, "g"), rep);
      },
      clear: () => { this.bodyText = ""; }
    };
  }
  saveAndClose() {}
}

class MockProperties {
  constructor() {
    this.store = {};
  }
  getProperty(k) { return this.store[k] !== undefined ? this.store[k] : null; }
  setProperty(k, v) { this.store[k] = String(v); }
  deleteProperty(k) { delete this.store[k]; }
  getProperties() { return { ...this.store }; }
  setProperties(obj) { Object.assign(this.store, obj); }
}

function createGasMockEnvironment() {
  const spreadsheet = new MockSpreadsheet();
  const folderRegistry = {};
  const fileRegistry = {};
  const rootFolder = new MockFolder("root", null, folderRegistry, fileRegistry);
  folderRegistry[rootFolder.getId()] = rootFolder;
  const docRegistry = {};

  const userProps = new MockProperties();
  const scriptProps = new MockProperties();
  const docProps = new MockProperties();

  const cacheStore = {};

  const logs = [];
  const fetchCalls = [];

  const MimeType = {
    GOOGLE_DOCS: "application/vnd.google-apps.document",
    GOOGLE_SHEETS: "application/vnd.google-apps.spreadsheet",
    GOOGLE_FORMS: "application/vnd.google-apps.form",
    FOLDER: "application/vnd.google-apps.folder",
    PLAIN_TEXT: "text/plain",
    JPEG: "image/jpeg",
    PNG: "image/png",
    PDF: "application/pdf"
  };

  const env = {
    MimeType,
    SpreadsheetApp: {
      getActiveSpreadsheet: () => spreadsheet,
      WrapStrategy: { WRAP: "WRAP", OVERFLOW: "OVERFLOW", CLIP: "CLIP" },
      flush: () => {},
      getUi: () => ({
        showSidebar: () => {},
        showModalDialog: () => {},
        alert: () => {},
        prompt: () => ({ getResponseText: () => "" }),
        createMenu: (menuName) => {
          const builder = {
            addItem: () => builder,
            addSeparator: () => builder,
            addToUi: () => {}
          };
          return builder;
        }
      }),
      newRichTextValue: () => {
        let t = "", u = "";
        return {
          setText: (text) => { t = text; return this; },
          setLinkUrl: (url) => { u = url; return this; },
          build: () => ({ text: t, linkUrl: u })
        };
      }
    },
    DriveApp: {
      getRootFolder: () => rootFolder,
      getFolderById: (id) => folderRegistry[id] || null,
      getFileById: (id) => fileRegistry[id] || null,
      getFoldersByName: (name) => rootFolder.getFoldersByName(name),
      getFilesByName: (name) => rootFolder.getFilesByName(name),
      createFolder: (name) => rootFolder.createFolder(name),
      createFile: (name, content, mime) => rootFolder.createFile(name, content, mime)
    },
    DocumentApp: {
      create: (name) => {
        const d = new MockDocument(name);
        docRegistry[d.getId()] = d;
        // create a corresponding file in root for Drive discovery
        const f = rootFolder.createFile(name, "", "application/vnd.google-apps.document");
        f.id = d.getId();
        return d;
      },
      openById: (id) => docRegistry[id] || null,
      openByUrl: (url) => {
        const m = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
        if (m && docRegistry[m[1]]) return docRegistry[m[1]];
        return null;
      }
    },
    PropertiesService: {
      getUserProperties: () => userProps,
      getScriptProperties: () => scriptProps,
      getDocumentProperties: () => docProps
    },
    Session: {
      getActiveUser: () => ({ getEmail: () => "test-marketer@example.com" })
    },
    Utilities: {
      DigestAlgorithm: {
        MD5: "MD5",
        SHA_1: "SHA_1",
        SHA_256: "SHA_256"
      },
      computeDigest: (algo, val) => {
        const hash = crypto.createHash("sha256").update(String(val)).digest();
        return Array.from(hash).map(b => (b > 127 ? b - 256 : b));
      },
      formatDate: (date, tz, fmt) => {
        const d = date instanceof Date ? date : new Date(date);
        return d.toISOString().replace("T", " ").substring(0, 19);
      },
      sleep: () => {},
      base64Encode: (str) => Buffer.from(str).toString("base64"),
      newBlob: (content, mime, name) => ({
        getDataAsString: () => content,
        getBytes: () => Buffer.from(content),
        getContentType: () => mime,
        getName: () => name
      })
    },
    CacheService: {
      getScriptCache: () => ({
        get: (k) => cacheStore[k] || null,
        put: (k, v) => { cacheStore[k] = v; },
        remove: (k) => { delete cacheStore[k]; }
      }),
      getUserCache: () => ({
        get: (k) => cacheStore[k] || null,
        put: (k, v) => { cacheStore[k] = v; },
        remove: (k) => { delete cacheStore[k]; }
      }),
      getDocumentCache: () => ({
        get: (k) => cacheStore[k] || null,
        put: (k, v) => { cacheStore[k] = v; },
        remove: (k) => { delete cacheStore[k]; }
      })
    },
    UrlFetchApp: {
      fetch: (url, opt) => {
        fetchCalls.push({ url, opt });
        return {
          getResponseCode: () => 200,
          getContentText: () => JSON.stringify({ candidates: [{ content: { parts: [{ text: "Mock response" }] } }] })
        };
      }
    },
    HtmlService: {
      createHtmlOutput: (html) => {
        const out = {
          setTitle: () => out,
          setWidth: () => out,
          setHeight: () => out,
          getContent: () => html
        };
        return out;
      },
      createTemplate: (html) => ({
        evaluate: () => {
          const out = {
            setTitle: () => out,
            setWidth: () => out,
            setHeight: () => out,
            getContent: () => html
          };
          return out;
        }
      })
    },
    Logger: {
      log: (msg) => { logs.push(String(msg)); }
    },
    // Internals for inspection
    _internals: {
      spreadsheet,
      rootFolder,
      folderRegistry,
      docRegistry,
      userProps,
      scriptProps,
      logs,
      fetchCalls
    }
  };

  return env;
}

module.exports = {
  createGasMockEnvironment,
  MockSheet,
  MockFolder,
  MockFile,
  MockDocument
};
