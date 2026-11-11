<script setup>
defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => ["active", "inactive"].includes(value),
  },
});
</script>

<template>
  <span
    class="device-status"
    :class="{
      'device-status--active': status === 'active',
      'device-status--inactive': status === 'inactive',
    }"
  >
    {{ status === "active" ? "Active" : "Inactive" }}
  </span>
</template>

<style scoped lang="scss">
.device-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--line);
  border-radius: 0.35rem;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}

.device-status--active {
  background: #8ae7d60d;
  border-color: #8ae7d629;
  color: var(--accent);
}

.device-status--inactive {
  background: var(--panel);
  color: var(--muted);
}
</style>
