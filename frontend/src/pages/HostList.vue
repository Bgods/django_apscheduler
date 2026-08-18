<template>
  <div class="page-container">
    <div class="page-header">
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索 IP / 标签" clearable style="width: 250px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterActive" placeholder="状态" clearable style="width: 110px;" @change="fetchData">
          <el-option label="已启用" value="true" />
          <el-option label="已停用" value="false" />
        </el-select>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <div class="action-bar">
        <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 添加机器</el-button>
        <el-button type="success" @click="handleBatchEnable" :disabled="!selectedRows.length">启用选中</el-button>
        <el-button type="warning" @click="handleBatchDisable" :disabled="!selectedRows.length">停用选中</el-button>
        <el-button type="danger" @click="handleBatchDelete" :disabled="!selectedRows.length">删除选中</el-button>
        <span v-if="selectedRows.length" class="selected-info">选中了 {{ selectedRows.length }} 个机器</span>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table :data="hosts" stripe v-loading="loading" height="100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="ip" label="IP 地址" width="160" />
        <el-table-column prop="label" label="标签" min-width="160" show-overflow-tooltip />
        <el-table-column prop="is_active" label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="handleUpdate(row)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
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
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑机器' : '添加机器'" width="450px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item label="IP 地址" required>
          <el-input v-model="form.ip" placeholder="如 192.168.1.100" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.label" placeholder="如 生产机A" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHosts, createHost, updateHost, deleteHost } from '../api'

const hosts = ref([])
const loading = ref(false)
const search = ref('')
const filterActive = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const selectedRows = ref([])
const form = ref({ ip: '', label: '', is_active: true })

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (filterActive.value) params.is_active = filterActive.value
    const res = await getHosts(params)
    hosts.value = res.data.results || res.data
    total.value = res.data.count || hosts.value.length
  } finally { loading.value = false }
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const openDialog = (host) => {
  if (host) {
    editing.value = host
    form.value = { ip: host.ip, label: host.label, is_active: host.is_active }
  } else {
    editing.value = null
    form.value = { ip: '', label: '', is_active: true }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.ip) return ElMessage.warning('请输入 IP 地址')
  saving.value = true
  try {
    if (editing.value) {
      const { data } = await updateHost(editing.value.id, form.value)
      Object.assign(editing.value, data)
      ElMessage.success('更新成功')
    } else {
      await createHost(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.ip?.[0] || e.message))
  } finally { saving.value = false }
}

const handleUpdate = async (row) => {
  try {
    await updateHost(row.id, { is_active: row.is_active })
  } catch { row.is_active = !row.is_active }
}

const handleDelete = async (id) => {
  try {
    await deleteHost(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch { ElMessage.error('删除失败') }
}

const handleBatchEnable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateHost(row.id, { is_active: true })
    }
    ElMessage.success(`已启用 ${selectedRows.value.length} 个机器`)
    selectedRows.value = []
    fetchData()
  } catch { ElMessage.error('批量启用失败') }
}

const handleBatchDisable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateHost(row.id, { is_active: false })
    }
    ElMessage.success(`已停用 ${selectedRows.value.length} 个机器`)
    selectedRows.value = []
    fetchData()
  } catch { ElMessage.error('批量停用失败') }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 个机器？`, '警告', { type: 'warning' })
    for (const row of selectedRows.value) {
      await deleteHost(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    fetchData()
  } catch {}
}

onMounted(fetchData)
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
.filter-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.action-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.selected-info {
  color: #606266;
  font-size: 13px;
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
