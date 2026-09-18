import axios from 'axios'

// Centralised API client (NFR-5): every frontend HTTP call goes through this instance.
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  withCredentials: true,
})

export const authApi = {
  signup: (payload) => apiClient.post('/api/auth/signup', payload),
  sendOtp: (payload) => apiClient.post('/api/auth/send-otp', payload),
  verifyOtp: (payload) => apiClient.post('/api/auth/verify-otp', payload),
  setPassword: (payload) => apiClient.post('/api/auth/set-password', payload),
  login: (payload) => apiClient.post('/api/auth/login', payload),
  logout: () => apiClient.post('/api/auth/logout'),
}

export const studentApi = {
  dashboard: () => apiClient.get('/api/student/dashboard'),
}

export const applicationApi = {
  start: () => apiClient.post('/api/app/start'),
  getDraft: (applicationId) => apiClient.get(`/api/app/draft/${applicationId}`),
  saveDraftStep: (applicationId, stepNumber, data) =>
    apiClient.patch(`/api/app/draft/${applicationId}/step/${stepNumber}`, data),
  uploadDocument: (applicationId, docType, formData) =>
    apiClient.post(`/api/app/upload/${applicationId}/${docType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  createPaymentOrder: () => apiClient.post('/api/app/payment/create-order'),
  confirmPayment: (payload) => apiClient.post('/api/app/payment/confirm', payload),
  paymentFailed: (payload) => apiClient.post('/api/app/payment/failed', payload),
  getReceipt: (applicationId) => apiClient.get(`/api/app/receipt/${applicationId}`),
}

export const adminApi = {
  login: (payload) => apiClient.post('/api/admin/login', payload),
  logout: () => apiClient.post('/api/admin/logout'),
  listStudents: (params) => apiClient.get('/api/admin/students', { params }),
  getStudent: (studentId) => apiClient.get(`/api/admin/students/${studentId}`),
  deleteStudent: (studentId) => apiClient.delete(`/api/admin/students/${studentId}`),
}
