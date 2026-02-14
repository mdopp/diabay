import axios, { AxiosError } from 'axios'

/**
 * Axios client for API requests
 */

// Use relative URL (same host) or environment variable
// This allows accessing from any device on the network
const API_URL = import.meta.env.VITE_API_URL ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://localhost:8000')

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth headers here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const message = (error.response.data as { error?: string })?.error || error.message

      if (status >= 500) {
        console.error('Server error:', message)
      } else if (status === 404) {
        console.warn('Resource not found:', error.config?.url)
      } else if (status === 400) {
        console.warn('Bad request:', message)
      }
    } else if (error.request) {
      // Request made but no response
      console.error('No response from server')
    } else {
      // Error setting up request
      console.error('Request error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient
