<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import { useNotificationStore } from "../../stores/notifications.js";
import ToastNotification from "./ToastNotification.vue";

const notifications = useNotificationStore();
function updateVisibility() {
  notifications.setHidden(document.hidden);
}
onMounted(() => {
  updateVisibility();
  document.addEventListener("visibilitychange", updateVisibility);
});
onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", updateVisibility);
  notifications.clear();
});
</script>

<template>
  <Teleport :to="notifications.target">
    <section class="toast-host" aria-label="Notifications">
      <ToastNotification
        v-for="notification in notifications.visible"
        :key="notification.id"
        :notification="notification"
        @dismiss="notifications.dismiss(notification.id, $event)"
        @pause="notifications.pause(notification.id, $event)"
        @resume="notifications.resume(notification.id, $event)"
      />
    </section>
  </Teleport>
</template>

<style scoped lang="scss">
.toast-host {
  position: fixed;
  z-index: 100;
  top: max(1rem, env(safe-area-inset-top));
  right: max(1rem, env(safe-area-inset-right));
  display: grid;
  gap: 0.75rem;
  width: min(24rem, calc(100vw - 2rem));
  max-height: calc(100svh - 2rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  pointer-events: none;
}
</style>
