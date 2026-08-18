<template>
  <div class="page-container">
    <div class="page-header">
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索名称 / 主机" clearable style="width: 250px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterType" placeholder="数据库类型" clearable style="width: 140px;" @change="fetchData">
          <el-option v-for="t in dbTypes" :key="t[0]" :label="t[1]" :value="t[0]" />
        </el-select>
        <el-select v-model="filterActive" placeholder="状态" clearable style="width: 110px;" @change="fetchData">
          <el-option label="已启用" value="true" />
          <el-option label="已停用" value="false" />
        </el-select>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <div class="action-bar">
        <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 添加数据库</el-button>
        <el-button type="success" @click="handleBatchEnable" :disabled="!selectedRows.length">启用选中</el-button>
        <el-button type="warning" @click="handleBatchDisable" :disabled="!selectedRows.length">停用选中</el-button>
        <el-button type="danger" @click="handleBatchDelete" :disabled="!selectedRows.length">删除选中</el-button>
        <span v-if="selectedRows.length" class="selected-info">选中了 {{ selectedRows.length }} 个数据库</span>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table :data="databases" stripe v-loading="loading" height="100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="label" label="配置名称" width="140" />
        <el-table-column prop="db_type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.db_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" width="140" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="database" label="数据库名" width="140" />
        <el-table-column prop="is_active" label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="success" size="small" @click="handleTest(row)" :loading="row._testing">测试</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑数据库' : '添加数据库'" width="700px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="配置名称" required>
          <el-input v-model="form.label" placeholder="如 生产库" />
        </el-form-item>
        <el-form-item label="数据库类型">
          <el-select v-model="form.db_type" style="width: 100%;">
            <el-option v-for="t in dbTypes" :key="t[0]" :label="t[1]" :value="t[0]" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="15">
            <el-form-item label="主机">
              <el-input v-model="form.host" placeholder="localhost" />
            </el-form-item>
          </el-col>
          <el-col :span="9">
            <el-form-item label="端口">
              <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="数据库名" required>
          <el-input v-model="form.database" placeholder="数据库名称" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用户名">
              <el-input v-model="form.username" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码">
              <el-input v-model="form.password" type="password" show-password />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="额外参数">
          <el-input v-model="form.extra_params" placeholder="如 charset=utf8mb4" />
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
import { getDatabases, createDatabase, updateDatabase, deleteDatabase, testDbConnection } from '../api'

const dbTypes = [
  ['mysql', 'MySQL'], ['postgresql', 'PostgreSQL'],
  ['sqlserver', 'SQL Server'], ['oracle', 'Oracle'], ['sqlite', 'SQLite'],
]

const databases = ref([])
const loading = ref(false)
const search = ref('')
const filterType = ref('')
const filterActive = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const selectedRows = ref([])
const form = ref({
  label: '', db_type: 'mysql', host: 'localhost', port: 3306,
  database: '', username: '', password: '', extra_params: '', is_active: true,
})

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (filterType.value) params.db_type = filterType.value
    if (filterActive.value) params.is_active = filterActive.value
    const res = await getDatabases(params)
    databases.value = (res.data.results || res.data).map(d => ({ ...d, _testing: false }))
    total.value = res.data.count || databases.value.length
  } finally { loading.value = false }
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const openDialog = (db) => {
  if (db) {
    editing.value = db
    form.value = { ...db }
  } else {
    editing.value = null
    form.value = {
      label: '', db_type: 'mysql', host: 'localhost', port: 3306,
      database: '', username: '', password: '', extra_params: '', is_active: true,
    }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.label || !form.value.database) return ElMessage.warning('请填写必要字段')
  saving.value = true
  try {
    if (editing.value) {
      await updateDatabase(editing.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createDatabase(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally { saving.value = false }
}

const handleTest = async (row) => {
  row._testing = true
  try {
    const res = await testDbConnection({
      db_type: row.db_type, host: row.host, port: row.port,
      database: row.database, username: row.username, password: row.password,
    })
    if (res.data.ok) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error('连接失败: ' + res.data.error)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  } finally { row._testing = false }
}

const handleDelete = async (id) => {
  try {
    await deleteDatabase(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch { ElMessage.error('删除失败') }
}

const handleBatchEnable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateDatabase(row.id, { is_active: true })
    }
    ElMessage.success(`已启用 ${selectedRows.value.length} 个数据库`)
    selectedRows.value = []
    fetchData()
  } catch { ElMessage.error('批量启用失败') }
}

const handleBatchDisable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateDatabase(row.id, { is_active: false })
    }
    ElMessage.success(`已停用 ${selectedRows.value.length} 个数据库`)
    selectedRows.value = []
    fetchData()
  } catch { ElMessage.error('批量停用失败') }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 个数据库？`, '警告', { type: 'warning' })
    for (const row of selectedRows.value) {
      await deleteDatabase(row.id)
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
