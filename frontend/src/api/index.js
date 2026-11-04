import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v2',
  timeout: 30000,
})

// 请求拦截器：添加 CSRF Token
api.interceptors.request.use(config => {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  if (match) {
    config.headers['X-CSRFToken'] = match[1]
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    const status = error.response?.status
    const msg = error.response?.data?.detail || error.response?.data?.error || error.message
    if (status === 401 || status === 403) {
      // 未登录或登录失效：清理本地状态并跳转登录页
      if (!window.location.pathname.endsWith('/login')) {
        localStorage.removeItem('user')
        const current = window.location.pathname.replace(/^\/app/, '') || '/'
        window.location.href = `/app/login?redirect=${encodeURIComponent(current)}`
      }
    }
    console.error('API Error:', msg)
    return Promise.reject(error)
  }
)

// ===== Tasks =====
export const getTasks = (params) => api.get('/tasks/', { params })
export const getTaskOptions = () => api.get('/tasks/options/')
export const getTask = (id) => api.get(`/tasks/${id}/`)
export const createTask = (data) => api.post('/tasks/', data)
export const updateTask = (id, data) => api.patch(`/tasks/${id}/`, data)
export const deleteTask = (id) => api.delete(`/tasks/${id}/`)
export const executeTask = (id) => api.post(`/tasks/${id}/execute/`)
export const copyTask = (id) => api.post(`/tasks/${id}/copy/`)
export const getTaskGroups = () => api.get('/tasks/groups/')

// ===== Hosts =====
export const getHosts = (params) => api.get('/hosts/', { params })
export const createHost = (data) => api.post('/hosts/', data)
export const updateHost = (id, data) => api.patch(`/hosts/${id}/`, data)
export const deleteHost = (id) => api.delete(`/hosts/${id}/`)

// ===== Databases =====
export const getDatabases = (params) => api.get('/databases/', { params })
export const createDatabase = (data) => api.post('/databases/', data)
export const updateDatabase = (id, data) => api.patch(`/databases/${id}/`, data)
export const deleteDatabase = (id) => api.delete(`/databases/${id}/`)
export const testDbConnection = (data) => api.post('/databases/test_connection/', data)

// ===== Dashboard =====
export const getDashboardStats = () => api.get('/dashboard/')

// ===== Logs =====
export const getLogs = (params) => api.get('/logs/', { params })
export const getLog = (id) => api.get(`/logs/${id}/`)

// ===== Auth =====
export const login = (data) => api.post('/auth/login/', data)
export const logout = () => api.post('/auth/logout/')
export const getMe = () => api.get('/auth/me/')
export const changePassword = (data) => api.post('/auth/change_password/', data)
export const updateProfile = (data) => api.patch('/auth/update_profile/', data)

// ===== Users 管理 =====
export const getUsers = (params) => api.get('/users/', { params })
export const createUser = (data) => api.post('/users/', data)
export const updateUser = (id, data) => api.patch(`/users/${id}/`, data)
export const deleteUser = (id) => api.delete(`/users/${id}/`)
export const resetUserPassword = (id, data) => api.post(`/users/${id}/reset_password/`, data)

// ===== Groups 管理 =====
export const getGroups = (params) => api.get('/groups/', { params })
export const createGroup = (data) => api.post('/groups/', data)
export const updateGroup = (id, data) => api.patch(`/groups/${id}/`, data)
export const deleteGroup = (id) => api.delete(`/groups/${id}/`)
export const getPermissions = (params) => api.get('/permissions/', { params })

export default api
