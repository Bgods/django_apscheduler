<template>
  <div class="page-container">
    <div class="page-header">
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索用户名 / 姓名" clearable style="width: 250px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <div class="action-bar">
        <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 添加用户</el-button>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table :data="users" stripe v-loading="loading" height="100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="first_name" label="姓名" min-width="100">
          <template #default="{ row }">{{ row.first_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="150">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="danger" size="small">超管</el-tag>
            <el-tag v-else-if="row.is_staff" type="warning" size="small">管理员</el-tag>
            <el-tag v-else type="info" size="small">普通用户</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="所属分组" min-width="140">
          <template #default="{ row }">
            <template v-if="row.groups_display && row.groups_display.length">
              <el-tag v-for="g in row.groups_display" :key="g" size="small" style="margin-right: 4px;">{{ g }}</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">{{ row.date_joined || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="openReset(row)">重置密码</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-footer">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '添加用户'" width="520px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!editing" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item v-if="!editing" label="初始密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.first_name" maxlength="30" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="role">
            <el-checkbox label="is_staff">管理员</el-checkbox>
            <el-checkbox label="is_superuser">超级管理员</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="所属分组">
          <el-select v-model="form.groups" multiple clearable style="width: 100%;" placeholder="选择分组">
            <el-option v-for="g in allGroups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="420px" destroy-on-close>
      <p style="margin: 0 0 12px; color: #606266;">为账号 <b>{{ resetTarget?.username }}</b> 设置新密码</p>
      <el-input v-model="resetPwd" type="password" show-password placeholder="新密码（至少 6 位）" @keyup.enter="handleResetPwd" />
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="handleResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser, resetUserPassword, getGroups } from '../api'

const users = ref([])
const allGroups = ref([])
const loading = ref(false)
const search = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const role = ref([])
const resetVisible = ref(false)
const resetTarget = ref(null)
const resetPwd = ref('')
const resetting = ref(false)
const form = ref({ username: '', password: '', first_name: '', email: '', groups: [], is_active: true })

const fetchGroups = async () => {
  try {
    const res = await getGroups({ page_size: 1000 })
    allGroups.value = res.data.results || res.data || []
  } catch {}
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const res = await getUsers(params)
    users.value = res.data.results || res.data
    total.value = res.data.count || users.value.length
  } finally { loading.value = false }
}

const openDialog = (user) => {
  if (user) {
    editing.value = user
    role.value = []
    if (user.is_superuser) role.value.push('is_superuser')
    if (user.is_staff) role.value.push('is_staff')
    form.value = {
      username: user.username,
      password: '',
      first_name: user.first_name || '',
      email: user.email || '',
      groups: user.groups || [],
      is_active: user.is_active,
    }
  } else {
    editing.value = null
    role.value = []
    form.value = { username: '', password: '', first_name: '', email: '', groups: [], is_active: true }
  }
  dialogVisible.value = true
}

const buildPayload = () => {
  const payload = { ...form.value }
  payload.is_superuser = role.value.includes('is_superuser')
  payload.is_staff = role.value.includes('is_staff')
  return payload
}

const handleSave = async () => {
  if (!form.value.username) return ElMessage.warning('请输入用户名')
  if (!editing.value && (!form.value.password || form.value.password.length < 6)) {
    return ElMessage.warning('初始密码至少 6 位')
  }
  saving.value = true
  try {
    if (editing.value) {
      const { data } = await updateUser(editing.value.id, buildPayload())
      if (data.id === JSON.parse(localStorage.getItem('user') || '{}').id) {
        localStorage.setItem('user', JSON.stringify(data))
      }
      ElMessage.success('更新成功')
    } else {
      await createUser(buildPayload())
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    const err = e.response?.data
    ElMessage.error(err?.username?.[0] || err?.email?.[0] || err?.detail || '保存失败')
  } finally { saving.value = false }
}

const openReset = (user) => {
  resetTarget.value = user
  resetPwd.value = ''
  resetVisible.value = true
}

const handleResetPwd = async () => {
  if (!resetPwd.value || resetPwd.value.length < 6) return ElMessage.warning('新密码至少 6 位')
  resetting.value = true
  try {
    await resetUserPassword(resetTarget.value.id, { new_password: resetPwd.value })
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch { ElMessage.error('重置失败') }
  finally { resetting.value = false }
}

const handleDelete = async (row) => {
  try {
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    const err = e.response?.data
    ElMessage.error(err?.detail || err?.username?.[0] || '删除失败')
  }
}

onMounted(() => { fetchGroups(); fetchData() })
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
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.filter-bar, .action-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.table-wrapper {
  flex: 1;
  overflow: hidden;
  padding: 0 20px;
}
.page-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}
</style>