<template>
  <div ref="editorContainer" class="sql-editor"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, placeholder } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { highlightActiveLineGutter, highlightSpecialChars, drawSelection, highlightActiveLine, dropCursor, rectangularSelection, crosshairCursor, lineNumbers } from '@codemirror/view'
import { bracketMatching, foldGutter, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { sql } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '输入 SQL 语句'
  }
})

const emit = defineEmits(['update:modelValue'])

const editorContainer = ref(null)
let editorView = null

const createEditor = () => {
  if (!editorContainer.value) return

  if (editorView) {
    editorView.destroy()
  }

  const state = EditorState.create({
    doc: props.modelValue,
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightSpecialChars(),
      history(),
      foldGutter(),
      drawSelection(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
      indentOnInput(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      bracketMatching(),
      highlightActiveLine(),
      keymap.of([...defaultKeymap, ...historyKeymap]),
      placeholder(props.placeholder),
      sql(),
      oneDark,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          emit('update:modelValue', update.state.doc.toString())
        }
      }),
      EditorView.lineWrapping,
    ]
  })

  editorView = new EditorView({
    state,
    parent: editorContainer.value
  })
}

onMounted(() => {
  nextTick(() => {
    createEditor()
  })
})

onBeforeUnmount(() => {
  if (editorView) {
    editorView.destroy()
  }
})

watch(() => props.modelValue, (newVal) => {
  if (editorView && newVal !== editorView.state.doc.toString()) {
    editorView.dispatch({
      changes: { from: 0, to: editorView.state.doc.length, insert: newVal }
    })
  }
})
</script>

<style scoped>
.sql-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  min-height: 200px;
}

.sql-editor :deep(.cm-editor) {
  height: 300px;
  font-size: 14px;
}

.sql-editor :deep(.cm-scroller) {
  overflow: auto;
}

.sql-editor :deep(.cm-focused) {
  outline: none;
}
</style>
