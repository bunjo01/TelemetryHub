<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  onUnmounted,
  ref,
  useId,
} from "vue";
import { useNotificationStore } from "../../stores/notifications.js";
import BaseIconButton from "./BaseIconButton.vue";

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  closeDisabled: {
    type: Boolean,
    default: false,
  },
  initialFocus: {
    type: Function,
    default: null,
  },
});

const emit = defineEmits(["close"]);
const notifications = useNotificationStore();
const titleId = useId();
const dialog = ref(null);
const heading = ref(null);

let opener;
let notificationTarget;
let isUnmounting = false;

function requestClose() {
  if (props.closeDisabled || isUnmounting) return;

  emit("close");
}

function handleNativeClose() {
  if (isUnmounting) return;

  emit("close");
}

onMounted(() => {
  opener = document.activeElement;
  dialog.value.showModal();

  notificationTarget = dialog.value;
  notifications.registerTarget(notificationTarget);

  if (props.initialFocus) {
    props.initialFocus();
  } else {
    heading.value.focus({ preventScroll: true });
  }
});

onBeforeUnmount(() => {
  isUnmounting = true;
  notifications.unregisterTarget(notificationTarget);
  dialog.value.close();
});

onUnmounted(async () => {
  await nextTick();

  if (
    document.activeElement !== document.body &&
    document.activeElement?.isConnected
  ) {
    return;
  }

  if (
    opener instanceof HTMLElement &&
    opener.isConnected &&
    !opener.matches(":disabled") &&
    !opener.closest("[inert], dialog:not([open])")
  ) {
    opener.focus({ preventScroll: true });
  }

  if (document.activeElement === document.body) {
    document.querySelector("main h1[tabindex]")?.focus({
      preventScroll: true,
    });
  }
});
</script>

<template>
  <dialog
    ref="dialog"
    class="panel base-dialog"
    :aria-labelledby="titleId"
    @cancel.prevent="requestClose"
    @close="handleNativeClose"
  >
    <header class="base-dialog__heading">
      <h2 :id="titleId" ref="heading" class="base-dialog__title" tabindex="-1">
        {{ title }}
      </h2>

      <BaseIconButton
        :label="`Close ${title}`"
        :disabled="closeDisabled"
        @click="requestClose"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          aria-hidden="true"
        >
          <path d="m6 6 12 12M6 18 18 6" />
        </svg>
      </BaseIconButton>
    </header>

    <slot :close="requestClose" />
  </dialog>
</template>

<style scoped lang="scss">
.base-dialog {
  width: min(480px, calc(100% - 2rem));
  max-height: calc(100svh - 2rem);
  padding: 1.75rem;
  color: var(--text);
  overflow-y: auto;
}

.base-dialog::backdrop {
  background: #030810b8;
  backdrop-filter: blur(5px);
}

.base-dialog__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.base-dialog__title {
  min-width: 0;
  margin: 0;
  font-size: 1.4rem;
  font-weight: 500;
  overflow-wrap: anywhere;
}

@media (max-width: 700px) {
  .base-dialog {
    padding: 1.25rem;
  }
}
</style>
