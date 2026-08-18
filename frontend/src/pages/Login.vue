<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <div class="login-header">
        <el-icon :size="40" color="#409eff"><Timer /></el-icon>
        <h2 class="login-title">任务调度平台</h2>
        <p class="login-subtitle">Django APScheduler 分布式任务调度</p>
      </div>
      <el-form :model="form" size="large" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" clearable>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%;" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = ref({ username: '', password: '' })

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    return ElMessage.warning('请输入用户名和密码')
  }
  loading.value = true
  try {
    const res = await login(form.value)
    localStorage.setItem('user', JSON.stringify(res.data))
    ElMessage.success(`欢迎回来，${res.data.username}`)
    router.push(route.query.redirect || '/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #304156 0%, #1f2d3d 100%);
}
.login-card {
  width: 380px;
  border-radius: 8px;
  padding: 8px 12px;
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
}
.login-title {
  margin: 12px 0 4px;
  color: #303133;
  font-weight: 600;
}
.login-subtitle {
  margin: 0;
  color: #909399;
  font-size: 13px;
}
</style>