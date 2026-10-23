<script setup>
import { ref } from "vue";

const model = defineModel({
  type: String,
  required: true,
});
const input = ref(null);

function focus(options) {
  input.value?.focus(options);
}

defineExpose({ focus });
</script>

<template>
  <input ref="input" v-model="model" class="input">
</template>

<style scoped lang="scss">
.input {
  min-height: 3rem;
  min-width: 0;
  padding: 0.8rem 1rem;
  font: inherit;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
  color: var(--text);
}

.input::placeholder {
  color: #7e90a3;
}

.input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}
</style>
