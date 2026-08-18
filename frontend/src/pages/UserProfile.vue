<template>
  <div class="page-container">
    <div class="page-header">
      <div class="profile-title">
        <el-icon :size="24" color="#409eff"><UserFilled /></el-icon>
        <span>用户信息</span>
      </div>
    </div>

    <div class="table-wrapper">
      <el-row :gutter="20">
        <el-col :xs="24" :md="14">
          <el-card shadow="never" header="基本信息">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
              <el-descriptions-item label="姓名">{{ user.first_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ user.email || '-' }}</el-descriptions-item>
              <el-descriptions-item label="角色">
                <el-tag v-if="user.is_superuser" type="danger" size="small">超级管理员</el-tag>
                <el-tag v-else-if="user.is_staff" type="warning" size="small">管理员</el-tag>
                <el-tag v-else type="info" size="small">普通用户</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="账号状态">
                <el-tag :type="user.is_active ? 'success' : 'danger'" size="small">
                  {{ user.is_active ? '正常' : '停用' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <el-button type="primary" style="margin-top: 16px;" @click="editVisible = true">
              编辑资料
            </el-button>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="10">
          <el-card shadow="never" header="修改密码">
            <el-form :model="pwdForm" label-width="80px">
              <el-form-item label="原密码">
                <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入原密码" />
              </el-form-item>
              <el-form-item label="新密码">
                <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 6 位" />
              </el-form-item>
              <el-form-item label="确认密码">
                <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="pwdSaving" @click="handleChangePwd">确认修改</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-dialog v-model="editVisible" title="编辑资料" width="450px" destroy-on-close>
      <el-form :model="profileForm" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="profileForm.first_name" maxlength="30" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="profileSaving" @click="handleSaveProfile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMe, updateProfile, changePassword } from '../api'

const user = ref({})
const editVisible = ref(false)
const profileSaving = ref(false)
const pwdSaving = ref(false)

const profileForm = reactive({ first_name: '', email: '' })
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const loadUser = async () => {
  try {
    const res = await getMe()
    user.value = res.data
    profileForm.first_name = res.data.first_name || ''
    profileForm.email = res.data.email || ''
    localStorage.setItem('user', JSON.stringify(res.data))
  } catch {
    ElMessage.error('获取用户信息失败')
  }
}

const handleSaveProfile = async () => {
  profileSaving.value = true
  try {
    const res = await updateProfile({ first_name: profileForm.first_name, email: profileForm.email })
    user.value = res.data
    localStorage.setItem('user', JSON.stringify(res.data))
    editVisible.value = false
    ElMessage.success('资料已更新')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.email?.[0] || e.message))
  } finally { profileSaving.value = false }
}

const handleChangePwd = async () => {
  if (!pwdForm.old_password || !pwdForm.new_password) return ElMessage.warning('请填写完整')
  if (pwdForm.new_password.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (pwdForm.new_password !== pwdForm.confirm_password) return ElMessage.warning('两次输入的新密码不一致')
  pwdSaving.value = true
  try {
    await changePassword({ ...pwdForm })
    ElMessage.success('密码修改成功')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.old_password?.[0] || e.response?.data?.confirm_password?.[0] || '修改失败')
  } finally { pwdSaving.value = false }
}

onMounted(loadUser)
</script>

<style scoped>
.page-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}
.page-header {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.profile-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.table-wrapper {
  flex: 1;
  overflow: auto;
  padding: 20px;
}
</style>