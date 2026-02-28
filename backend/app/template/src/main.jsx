import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// ── Conjure contract ────────────────────────────────────────────────────────
const APP_ID = import.meta.env.VITE_APP_ID || 'dev'
const STORAGE_KEY = `conjure_${APP_ID}`
const SYNC_URL = `/api/apps/${APP_ID}/sync`

function readStore() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

function writeStore(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

function syncToServer() {
  try {
    const data = window.__conjure.getData()
    navigator.sendBeacon(SYNC_URL, JSON.stringify(data))
  } catch {
    // silent
  }
}

window.__conjure = {
  getData() {
    return readStore()
  },
  setData(data) {
    writeStore(data)
    syncToServer()
  },
  getSchema() {
    if (window.__conjure._schemaCache) return window.__conjure._schemaCache
    try {
      const xhr = new XMLHttpRequest()
      xhr.open('GET', `/apps/${APP_ID}/schema.json`, false)
      xhr.send()
      if (xhr.status === 200) {
        window.__conjure._schemaCache = JSON.parse(xhr.responseText)
        return window.__conjure._schemaCache
      }
    } catch {
      // fall through
    }
    return { app_id: APP_ID, name: 'App', capabilities: [], data_shape: {}, actions: {} }
  },
  _schemaCache: null,
}

// ── Sync on visibility change & beforeunload ────────────────────────────────
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') syncToServer()
})
window.addEventListener('beforeunload', syncToServer)

// ── Service Worker registration ─────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register(`/apps/${APP_ID}/sw.js`).catch(() => {})
}

// ── Initial sync ────────────────────────────────────────────────────────────
syncToServer()

// ── Render ──────────────────────────────────────────────────────────────────
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
