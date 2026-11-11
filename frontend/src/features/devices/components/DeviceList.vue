<script setup>
import DeviceListItem from "./DeviceListItem.vue";

defineProps({
  devices: {
    type: Array,
    required: true,
  },
  listQuery: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="device-list">
    <div class="device-list__heading" aria-hidden="true">
      <span>Name / description</span>
      <span>Type</span>
      <span>Status</span>
    </div>

    <ul class="device-list__items" aria-label="Devices">
      <DeviceListItem
        v-for="device in devices"
        :key="device.id"
        :device="device"
        :to="{
          path: `/devices/${device.id}`,
          query: listQuery,
        }"
      />
    </ul>
  </div>
</template>

<style scoped lang="scss">
.device-list {
  min-width: 0;
}

.device-list__heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 12rem 6rem;
  gap: 1.5rem;
  padding: 0 calc(1.25rem + 1px);
  margin-bottom: 0.75rem;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 500;
}

.device-list__items {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

@media (max-width: 700px) {
  .device-list__heading {
    display: none;
  }
}
</style>
