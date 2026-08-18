<template>
  <div class="page-container">
    <!-- 顶部筛选栏 -->
    <div class="page-header">
      <div class="filter-bar">
        <el-select v-model="filterLastResult" placeholder="最近执行状态" clearable style="width: 140px;" @change="fetchData">
          <el-option label="成功" value="SUCCESS" />
          <el-option label="失败" value="FAILED" />
          <el-option label="超时" value="TIMEOUT" />
          <el-option label="中断" value="INTERRUPTED" />
          <el-option label="执行中" value="RUNNING" />
        </el-select>
        <el-input v-model="search" placeholder="任务名称" clearable style="width: 180px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterGroup" placeholder="分组" clearable style="width: 140px;" @change="fetchData">
          <el-option v-for="g in groupOptions" :key="g" :label="g" :value="g" />
        </el-select>
        <el-select v-model="filterType" placeholder="任务类型" clearable style="width: 120px;" @change="fetchData">
          <el-option label="Python" value="python" />
          <el-option label="SQL" value="sql" />
        </el-select>
        <el-select v-model="filterHost" placeholder="分配机器" clearable style="width: 150px;" @change="fetchData">
          <el-option v-for="h in hostOptions" :key="h" :label="h" :value="h" />
        </el-select>
        <el-select v-model="filterActive" placeholder="状态" clearable style="width: 110px;" @change="fetchData">
          <el-option label="已启用" value="true" />
          <el-option label="已停用" value="false" />
        </el-select>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <div class="action-bar">
        <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 增加</el-button>
        <el-button type="danger" @click="handleBatchDelete" :disabled="!selectedRows.length">删除</el-button>
        <el-button type="success" @click="handleBatchEnable" :disabled="!selectedRows.length">启用选中任务</el-button>
        <el-button type="warning" @click="handleBatchDisable" :disabled="!selectedRows.length">停用选中任务</el-button>
        <el-button type="primary" @click="handleBatchExecute" :disabled="!selectedRows.length">立即执行选中任务</el-button>
        <el-button @click="openBatchAssignDialog" :disabled="!selectedRows.length">批量修改分配机器</el-button>
        <span v-if="selectedRows.length" class="selected-info">选中了 {{ selectedRows.length }} 个任务</span>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="table-wrapper">
      <el-table :data="tasks" stripe v-loading="loading" row-key="id" height="100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="group" label="分组" width="100" show-overflow-tooltip />
        <el-table-column prop="task_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.task_type === 'python' ? 'primary' : 'success'" size="small">
              {{ row.task_type === 'python' ? 'Python' : 'SQL' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分配机器" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span :style="{ color: row.hosts_display?.startsWith('*') ? '#999' : '#606266', fontSize: '12px' }">
              {{ row.hosts_display }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="定时规则" width="160">
          <template #default="{ row }">
            <code style="color:#fff;background:#909399;padding:1px 6px;border-radius:3px;font-size:12px;display:inline-block;width:120px;">{{ row.cron_expression || '-' }}</code>
            <div style="color:#666;font-size:12px;">{{ row.cron_description }}</div>
          </template>
        </el-table-column>
        <el-table-column label="执行脚本" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span :style="{ fontSize: '12px', color: row.task_type === 'sql' ? '#52c41a' : '#606266' }">
              {{ row.script_display || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleActive(row)" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="后续执行" width="100">
          <template #default="{ row }">
            <template v-if="Array.isArray(row.next_runs)">
              <div v-for="(t, i) in row.next_runs" :key="i" style="font-size:12px;white-space:nowrap;">{{ t }}</div>
            </template>
            <span v-else style="color:#999;font-size:12px;">{{ row.next_runs }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最近执行" width="140">
          <template #default="{ row }">
            <template v-if="row.last_execution">
              <el-link type="primary" :underline="false" @click="goLogs(row.id)">
                <div style="font-size:12px;">{{ row.last_execution.start_time }}</div>
              </el-link>
              <div style="display:flex;align-items:center;gap:4px;margin-top:2px;">
                <el-tag :type="resultTagType(row.last_execution.result)" size="small">{{ row.last_execution.result_display }}</el-tag>
                <span v-if="row.last_execution.duration != null" :style="{ fontSize: '12px', color: row.last_execution.duration < 60 ? '#999' : row.last_execution.duration < 600 ? '#f56c6c' : '#e4393c' }">
                  {{ row.last_execution.duration }}s
                </span>
              </div>
            </template>
            <span v-else style="color:#999;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleExecute(row)">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleCopy(row)">复制</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 底部分页 -->
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

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingTask ? '编辑任务' : '新建任务'" width="680px" destroy-on-close>
      <el-form :model="form" label-width="100px" label-position="right">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务名称" required>
              <el-input v-model="form.name" placeholder="输入任务名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分组">
              <el-input v-model="form.group" placeholder="如：数据同步" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="任务类型">
              <el-select v-model="form.task_type" style="width: 100%;">
                <el-option label="Python 脚本" value="python" />
                <el-option label="SQL 脚本" value="sql" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="form.timeout_seconds" :min="0" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Python 任务配置 -->
        <template v-if="form.task_type === 'python'">
          <el-form-item label="项目路径">
            <el-input v-model="form.project_path" placeholder="如 D:/projects/myapp" />
          </el-form-item>
          <el-form-item label="执行脚本">
            <el-input v-model="form.script_path" placeholder="如 同步数据.py" />
          </el-form-item>
          <el-form-item label="执行器路径">
            <el-input v-model="form.executor_path" placeholder="留空使用系统默认 Python" />
          </el-form-item>
        </template>

        <!-- SQL 任务配置 -->
        <template v-if="form.task_type === 'sql'">
          <el-form-item label="目标数据库">
            <el-select v-model="form.database" style="width: 100%;" placeholder="选择数据库">
              <el-option v-for="db in databases" :key="db.id" :label="`${db.label} (${db.db_type})`" :value="db.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="SQL 内容">
            <SqlEditor v-model="form.sql_content" placeholder="输入 SQL 语句" />
          </el-form-item>
        </template>

        <el-form-item label="Cron 表达式">
          <el-input v-model="form.cron_expression" placeholder="分 时 日 月 周，留空=手动触发">
            <template #append>
              <el-popover placement="bottom" :width="320" trigger="click">
                <template #reference>
                  <el-button>快捷</el-button>
                </template>
                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                  <el-button v-for="p in cronPresets" :key="p[1]" size="small" @click="form.cron_expression = p[1]">{{ p[0] }}</el-button>
                </div>
              </el-popover>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="分配机器">
          <el-select v-model="form.host_ids" multiple style="width: 100%;" placeholder="留空=任意机器">
            <el-option v-for="h in hosts" :key="h.id" :label="h.label ? `${h.label} (${h.ip})` : h.ip" :value="h.id" />
          </el-select>
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

    <!-- 批量修改分配机器弹窗 -->
    <el-dialog v-model="batchAssignVisible" title="批量修改分配机器" width="500px">
      <el-form label-width="100px">
        <el-form-item label="选择机器">
          <el-select v-model="batchAssignHostIds" multiple style="width: 100%;" placeholder="选择要分配的机器">
            <el-option v-for="h in hosts" :key="h.id" :label="h.label ? `${h.label} (${h.ip})` : h.ip" :value="h.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作方式">
          <el-radio-group v-model="batchAssignMode">
            <el-radio label="replace">替换</el-radio>
            <el-radio label="append">追加</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchAssignVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchAssign" :loading="batchAssignLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTasks, createTask, updateTask, deleteTask, executeTask, getHosts, getDatabases } from '../api'
import SqlEditor from '../components/SqlEditor.vue'

const route = useRoute()

const resultTagType = (result) => {
  const map = { SUCCESS: 'success', FAILED: 'danger', TIMEOUT: 'warning', INTERRUPTED: 'info', RUNNING: '' }
  return map[result] || ''
}

const goLogs = (taskId) => {
  window.open(`/app/logs?task=${taskId}`, '_blank')
}

const cronPresets = [
  ['每天 00:00', '0 0 * * *'], ['每天 09:00', '0 9 * * *'],
  ['每天 18:00', '0 18 * * *'], ['每周一 09:00', '0 9 * * 1'],
  ['每月1号 09:00', '0 9 1 * *'], ['每小时', '0 * * * *'],
  ['每30分钟', '*/30 * * * *'], ['每10分钟', '*/10 * * * *'],
]

const tasks = ref([])
const loading = ref(false)
const search = ref('')
const filterType = ref('')
const filterActive = ref('')
const filterGroup = ref('')
const filterHost = ref('')
const filterLastResult = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const groupOptions = ref([])
const hostOptions = ref([])
const selectedRows = ref([])

const dialogVisible = ref(false)
const editingTask = ref(null)
const saving = ref(false)
const hosts = ref([])
const databases = ref([])

const batchAssignVisible = ref(false)
const batchAssignHostIds = ref([])
const batchAssignMode = ref('replace')
const batchAssignLoading = ref(false)

const defaultForm = () => ({
  name: '', group: '', task_type: 'python', is_active: true,
  project_path: '', executor_path: '', script_path: '',
  sql_content: '', cron_expression: '', timeout_seconds: 0,
  database: null, host_ids: [],
})
const form = ref(defaultForm())

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (filterType.value) params.task_type = filterType.value
    if (filterActive.value) params.is_active = filterActive.value
    if (filterGroup.value) params.group = filterGroup.value
    if (filterHost.value) params.host = filterHost.value
    if (filterLastResult.value) params.last_result = filterLastResult.value
    const res = await getTasks(params)
    tasks.value = res.data.results || res.data
    total.value = res.data.count || tasks.value.length
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const openDialog = async (task) => {
  if (!hosts.value.length) {
    const hRes = await getHosts()
    hosts.value = hRes.data.results || hRes.data
  }
  if (!databases.value.length) {
    const dRes = await getDatabases()
    databases.value = dRes.data.results || dRes.data
  }
  if (task) {
    editingTask.value = task
    form.value = {
      name: task.name, group: task.group, task_type: task.task_type,
      is_active: task.is_active, project_path: task.project_path || '',
      executor_path: task.executor_path || '', script_path: task.script_path || '',
      sql_content: task.sql_content || '', cron_expression: task.cron_expression || '',
      timeout_seconds: task.timeout_seconds, database: task.database,
      host_ids: task.hosts || [],
    }
  } else {
    editingTask.value = null
    form.value = defaultForm()
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name) return ElMessage.warning('请输入任务名称')
  saving.value = true
  try {
    const data = { ...form.value }
    if (editingTask.value) {
      await updateTask(editingTask.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await createTask(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    const detail = e.response?.data
    if (detail) {
      const msg = Object.values(detail).flat().join('; ')
      ElMessage.error(msg)
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

const toggleActive = async (row) => {
  try {
    await updateTask(row.id, { is_active: row.is_active })
    ElMessage.success(row.is_active ? '已启用' : '已停用')
  } catch {
    row.is_active = !row.is_active
  }
}

const handleExecute = async (row) => {
  try {
    await executeTask(row.id)
    ElMessage.success(`任务 "${row.name}" 已触发执行`)
  } catch (e) {
    ElMessage.error('触发失败: ' + (e.response?.data?.message || e.message))
  }
}

const handleCopy = async (row) => {
  if (!hosts.value.length) {
    const hRes = await getHosts()
    hosts.value = hRes.data.results || hRes.data
  }
  if (!databases.value.length) {
    const dRes = await getDatabases()
    databases.value = dRes.data.results || dRes.data
  }
  editingTask.value = null
  form.value = {
    name: row.name + ' - 副本', group: row.group, task_type: row.task_type,
    is_active: row.is_active, project_path: row.project_path || '',
    executor_path: row.executor_path || '', script_path: row.script_path || '',
    sql_content: row.sql_content || '', cron_expression: row.cron_expression || '',
    timeout_seconds: row.timeout_seconds, database: row.database,
    host_ids: row.hosts || [],
  }
  dialogVisible.value = true
}

const handleDelete = async (id) => {
  try {
    await deleteTask(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    ElMessage.error('删除失败')
  }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 个任务？`, '警告', {
      type: 'warning',
    })
    for (const row of selectedRows.value) {
      await deleteTask(row.id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    fetchData()
  } catch {}
}

const handleBatchEnable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateTask(row.id, { is_active: true })
    }
    ElMessage.success(`已启用 ${selectedRows.value.length} 个任务`)
    selectedRows.value = []
    fetchData()
  } catch {
    ElMessage.error('批量启用失败')
  }
}

const handleBatchDisable = async () => {
  try {
    for (const row of selectedRows.value) {
      await updateTask(row.id, { is_active: false })
    }
    ElMessage.success(`已停用 ${selectedRows.value.length} 个任务`)
    selectedRows.value = []
    fetchData()
  } catch {
    ElMessage.error('批量停用失败')
  }
}

const handleBatchExecute = async () => {
  try {
    for (const row of selectedRows.value) {
      await executeTask(row.id)
    }
    ElMessage.success(`已触发 ${selectedRows.value.length} 个任务执行`)
    selectedRows.value = []
  } catch {
    ElMessage.error('批量执行失败')
  }
}

const openBatchAssignDialog = async () => {
  if (!hosts.value.length) {
    const hRes = await getHosts()
    hosts.value = hRes.data.results || hRes.data
  }
  batchAssignHostIds.value = []
  batchAssignMode.value = 'replace'
  batchAssignVisible.value = true
}

const handleBatchAssign = async () => {
  if (!batchAssignHostIds.value.length) {
    return ElMessage.warning('请至少选择一台机器')
  }
  batchAssignLoading.value = true
  try {
    for (const row of selectedRows.value) {
      if (batchAssignMode.value === 'replace') {
        await updateTask(row.id, { host_ids: batchAssignHostIds.value })
      } else {
        const currentHosts = row.hosts || []
        const newHosts = [...new Set([...currentHosts, ...batchAssignHostIds.value])]
        await updateTask(row.id, { host_ids: newHosts })
      }
    }
    ElMessage.success(`已为 ${selectedRows.value.length} 个任务更新分配机器`)
    batchAssignVisible.value = false
    selectedRows.value = []
    fetchData()
  } catch {
    ElMessage.error('批量修改失败')
  } finally {
    batchAssignLoading.value = false
  }
}

onMounted(async () => {
  const q = route.query
  if (q.task_type) filterType.value = q.task_type
  if (q.is_active) filterActive.value = q.is_active
  if (q.group) filterGroup.value = q.group
  try {
    const { getTaskGroups } = await import('../api')
    const res = await getTaskGroups()
    groupOptions.value = res.data || []
  } catch {}
  try {
    const hRes = await getHosts()
    const hostList = hRes.data.results || hRes.data
    hostOptions.value = [...new Set(hostList.map(h => h.ip))]
    hosts.value = hostList
  } catch {}
  fetchData()
})
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
