import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'
import Dashboard from '../pages/Dashboard.vue'
import TaskList from '../pages/TaskList.vue'
import HostList from '../pages/HostList.vue'
import DatabaseList from '../pages/DatabaseList.vue'
import ExecutionLog from '../pages/ExecutionLog.vue'
import UserProfile from '../pages/UserProfile.vue'
import UserManage from '../pages/UserManage.vue'
import GroupManage from '../pages/GroupManage.vue'
import Login from '../pages/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: Dashboard, meta: { title: '仪表盘' } },
      { path: 'tasks', name: 'TaskList', component: TaskList, meta: { title: '任务配置' } },
      { path: 'hosts', name: 'HostList', component: HostList, meta: { title: '执行机器' } },
      { path: 'databases', name: 'DatabaseList', component: DatabaseList, meta: { title: '数据库配置' } },
      { path: 'logs', name: 'ExecutionLog', component: ExecutionLog, meta: { title: '执行日志' } },
      { path: 'profile', name: 'UserProfile', component: UserProfile, meta: { title: '用户信息' } },
      { path: 'users', name: 'UserManage', component: UserManage, meta: { title: '用户管理' } },
      { path: 'groups', name: 'GroupManage', component: GroupManage, meta: { title: '分组管理' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory('/app/'),
  routes,
})

// 登录守卫：未登录跳转登录页
router.beforeEach((to) => {
  if (to.meta.public) return true
  const user = localStorage.getItem('user')
  if (!user) {
    return { path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  return true
})

export default router