<template>
  <el-container style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" style="transition: width 0.3s; background: #304156;">
      <div class="logo" @click="$router.push('/dashboard')">
        <el-icon :size="22"><Timer /></el-icon>
        <span v-show="!isCollapse">任务调度</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        :collapse="isCollapse"
        router
        :collapse-transition="false"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-sub-menu index="task-group">
          <template #title>
            <el-icon><List /></el-icon>
            <span>任务调度</span>
          </template>
          <el-menu-item index="/tasks">
            <el-icon><Setting /></el-icon>
            <span>任务配置</span>
          </el-menu-item>
          <el-menu-item index="/hosts">
            <el-icon><Monitor /></el-icon>
            <span>执行机器</span>
          </el-menu-item>
          <el-menu-item index="/databases">
            <el-icon><Coin /></el-icon>
            <span>数据库配置</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>执行日志</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="user.is_superuser || user.is_staff" index="system-group">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/groups">
            <el-icon><Avatar /></el-icon>
            <span>分组管理</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部栏 -->
      <el-header style="display: flex; align-items: center; background: #fff; box-shadow: 0 1px 4px rgba(0,21,41,.08); padding: 0 20px; z-index: 1;">
        <el-icon
          :size="20"
          style="cursor: pointer; margin-right: 16px;"
          @click="isCollapse = !isCollapse"
        >
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div style="flex: 1;"></div>
        <el-dropdown trigger="click" @command="handleUserCommand">
          <span class="user-trigger">
            <el-icon :size="18" color="#409eff"><UserFilled /></el-icon>
            <span class="user-name">{{ user.username || '未登录' }}</span>
            <el-icon :size="12"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon> 查看用户信息
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon> 注销登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <!-- 主内容区 -->
      <el-main style="background: #f0f2f5; padding: 0; overflow: hidden; position: relative;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { logout } from '../api'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || '首页')

const handleUserCommand = async (command) => {
  if (command === 'profile') {
    router.push('/profile')
    return
  }
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确认注销当前账号？', '提示', { type: 'warning' })
    } catch {
      return
    }
    try {
      await logout()
    } catch {
      // 注销接口失败也继续清理本地状态
    }
    localStorage.removeItem('user')
    user.value = {}
    ElMessage.success('已注销登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,.1);
}
.el-menu {
  border-right: none;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #303133;
  outline: none;
}
.user-name {
  font-size: 14px;
}
</style>
