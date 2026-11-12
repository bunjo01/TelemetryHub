<script setup>
import { ref } from "vue";

const model = defineModel({
  type: String,
  required: true,
});
const textarea = ref(null);

function focus(options) {
  textarea.value?.focus(options);
}

defineExpose({ focus });
</script>

<template>
  <textarea ref="textarea" v-model="model" class="textarea" />
</template>

<style scoped lang="scss">
.textarea {
  display: block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  padding: 0.8rem 1rem;
  font: inherit;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
  color: var(--text);
  resize: vertical;
}

.textarea::placeholder {
  color: #7e90a3;
}

.textarea:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.textarea:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
