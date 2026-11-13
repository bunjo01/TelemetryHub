<script setup>
import { useId } from "vue";
import { RouterLink } from "vue-router";
import { deviceTypeLabels } from "../device-types.js";
import DeviceStatus from "./DeviceStatus.vue";
import DeviceStatusControl from "./DeviceStatusControl.vue";

defineProps({
  device: {
    type: Object,
    required: true,
  },
  to: {
    type: [String, Object],
    required: true,
  },
  canManage: { type: Boolean, default: false },
});
defineEmits(["updated"]);

const nameId = `${useId()}-name`;
</script>

<template>
  <li class="device-list-item">
    <RouterLink
      :to="to"
      class="device-list-item__link"
      :aria-labelledby="nameId"
    >
      <span class="device-list-item__summary">
        <span :id="nameId" class="device-list-item__name">
          {{ device.name }}
        </span>

        <span v-if="device.description" class="device-list-item__description">
          {{ device.description }}
        </span>
      </span>

      <span class="device-list-item__type">
        {{ deviceTypeLabels[device.deviceType] }}
      </span>
    </RouterLink>
    <div class="device-list-item__status">
      <DeviceStatusControl
        v-if="canManage"
        :device="device"
        @updated="$emit('updated', $event)"
      />
      <DeviceStatus v-else :status="device.status" />
    </div>
  </li>
</template>

<style scoped lang="scss">
.device-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 12rem;
  align-items: center;
  gap: 1.5rem;
  min-width: 0;
  list-style: none;
  padding-right: 1.25rem;
  border: 1px solid var(--line);
  border-radius: 0.5rem;
  background-color: var(--panel);
  transition: background-color 0.15s;
}

.device-list-item:hover,
.device-list-item:focus-within {
  background-color: #162331;
}

.device-list-item__link {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 10rem;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem;
  border-radius: 0.5rem;
  color: var(--text);
  text-decoration: none;
}

.device-list-item__link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.device-list-item__summary {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
}

.device-list-item__name {
  font-size: 1rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.device-list-item__link:hover .device-list-item__name,
.device-list-item__link:focus-visible .device-list-item__name {
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.device-list-item__description {
  overflow: hidden;
  color: var(--muted);
  font-size: 0.85rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-list-item__type {
  color: var(--muted);
  font-size: 0.85rem;
  overflow-wrap: anywhere;
}

.device-list-item__status {
  min-width: 0;
  padding-block: 1rem;
  justify-self: end;
}

@media (max-width: 700px) {
  .device-list-item {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
    padding-right: 0;
  }

  .device-list-item__link {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.85rem 1rem;
    padding: 1rem;
  }

  .device-list-item__summary {
    grid-column: 1 / -1;
  }

  .device-list-item__status {
    padding: 0 1rem 1rem;
    justify-self: start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .device-list-item {
    transition: none;
  }
}
</style>
