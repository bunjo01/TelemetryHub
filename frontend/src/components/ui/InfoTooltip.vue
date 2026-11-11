<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, useId } from "vue";
import BaseIconButton from "./BaseIconButton.vue";

defineProps({
  label: { type: String, required: true },
  text: { type: String, required: true },
});

const tooltipId = useId();
const root = ref(null);
const content = ref(null);
const isOpen = ref(false);
const position = ref({});
let isPinned = false;
let isHovered = false;
let positionRevision = 0;

async function open() {
  const revision = ++positionRevision;
  const bounds = root.value.getBoundingClientRect();
  const viewportMargin = 16;
  const availableWidth = window.innerWidth - viewportMargin * 2;
  const availableHeight = window.innerHeight - viewportMargin * 2;
  const width = Math.min(256, availableWidth);
  const rightmostLeft = window.innerWidth - width - viewportMargin;
  const left = Math.max(
    viewportMargin,
    Math.min(bounds.right - width, rightmostLeft),
  );

  position.value = {
    width: `${width}px`,
    maxHeight: `${availableHeight}px`,
    left: `${left}px`,
    top: `${viewportMargin}px`,
    visibility: "hidden",
  };
  isOpen.value = true;

  await nextTick();
  if (!isOpen.value || revision !== positionRevision) return;

  const height = content.value.getBoundingClientRect().height;
  const hasSpaceAbove = bounds.top - height >= viewportMargin;
  const preferredTop = hasSpaceAbove ? bounds.top - height : bounds.bottom;
  const lowestTop = window.innerHeight - height - viewportMargin;

  position.value = {
    ...position.value,
    top: `${Math.max(viewportMargin, Math.min(preferredTop, lowestTop))}px`,
    visibility: "visible",
  };
}

function close() {
  positionRevision += 1;
  isOpen.value = false;
  isPinned = false;
}

function toggle() {
  if (isPinned) {
    close();
  } else {
    isPinned = true;
    open();
  }
}

function enter(event) {
  if (event.pointerType === "touch") return;
  isHovered = true;
  open();
}

function leave() {
  isHovered = false;
  if (!isPinned && !root.value.contains(document.activeElement)) close();
}

function blur() {
  if (!isHovered) close();
}

function dismissOutside(event) {
  if (!root.value.contains(event.target)) close();
}

function handleKeydown(event) {
  if (event.key === "Escape" && isOpen.value) {
    event.preventDefault();
    close();
  }
}

function handleScroll(event) {
  const isInsideTooltip =
    event.target instanceof Node && content.value?.contains(event.target);

  if (!isInsideTooltip) close();
}

onMounted(() => {
  document.addEventListener("pointerdown", dismissOutside);
  document.addEventListener("keydown", handleKeydown);
  window.addEventListener("resize", close);
  window.addEventListener("scroll", handleScroll, true);
});

onBeforeUnmount(() => {
  close();
  document.removeEventListener("pointerdown", dismissOutside);
  document.removeEventListener("keydown", handleKeydown);
  window.removeEventListener("resize", close);
  window.removeEventListener("scroll", handleScroll, true);
});
</script>

<template>
  <span
    ref="root"
    class="info-tooltip"
    @pointerenter="enter"
    @pointerleave="leave"
  >
    <BaseIconButton
      :label="label"
      :aria-describedby="tooltipId"
      @focus="open"
      @blur="blur"
      @click="toggle"
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
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6" />
        <circle cx="12" cy="7" r="1" fill="currentColor" stroke="none" />
      </svg>
    </BaseIconButton>
    <span
      v-show="isOpen"
      ref="content"
      :id="tooltipId"
      class="info-tooltip__content"
      role="tooltip"
      :style="position"
    >
      {{ text }}
    </span>
  </span>
</template>

<style scoped lang="scss">
.info-tooltip {
  display: inline-flex;
  flex-shrink: 0;
}

.info-tooltip__content {
  position: fixed;
  z-index: 10;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--line);
  border-radius: 0.5rem;
  background: #09121e;
  color: var(--text);
  font-size: 0.8rem;
  font-weight: 400;
  line-height: 1.5;
  overflow-wrap: anywhere;
  overflow-y: auto;
  box-shadow: 0 0.5rem 1.5rem #0004;
}
</style>
