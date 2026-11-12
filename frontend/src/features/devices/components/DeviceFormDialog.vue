<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useId } from "vue";
import { useRouter } from "vue-router";
import { createDevice, updateDevice } from "../../../api/devices.api.js";
import BaseButton from "../../../components/ui/BaseButton.vue";
import BaseDialog from "../../../components/ui/BaseDialog.vue";
import BaseInput from "../../../components/ui/BaseInput.vue";
import BaseSelect from "../../../components/ui/BaseSelect.vue";
import BaseTextarea from "../../../components/ui/BaseTextarea.vue";
import { useAuthStore } from "../../../stores/auth.js";
import { deviceTypeLabels } from "../device-types.js";

const props = defineProps({
  mode: {
    type: String,
    default: "create",
    validator: (value) => ["create", "edit"].includes(value),
  },
  device: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "created", "updated"]);
const isEditing = computed(() => props.mode === "edit");
const auth = useAuthStore();
const router = useRouter();
const formId = useId();

const name = ref(props.device?.name ?? "");
const deviceType = ref(props.device?.deviceType ?? "");
const description = ref(props.device?.description ?? "");
const nameInput = ref(null);
const typeInput = ref(null);
const descriptionInput = ref(null);
const errors = ref({});
const submissionError = ref("");
const isSaving = ref(false);

const changes = computed(() => {
  if (!isEditing.value) return {};

  const result = {};
  const trimmedName = name.value.trim();

  if (trimmedName !== props.device.name) {
    result.name = trimmedName;
  }

  if (description.value !== (props.device.description ?? "")) {
    result.description = description.value || null;
  }

  return result;
});

const hasChanges = computed(() => Object.keys(changes.value).length > 0);

const submitLabel = computed(() => {
  if (isSaving.value) return isEditing.value ? "Saving…" : "Adding…";

  return isEditing.value ? "Save changes" : "Add device";
});

const typeOptions = Object.entries(deviceTypeLabels).map(([value, label]) => ({
  value,
  label,
}));

let pendingRequest;
let isDisposed = false;
let isValidating = false;

function focusName() {
  nameInput.value?.focus({ preventScroll: true });
}

function clearError(field) {
  delete errors.value[field];
}

async function validate() {
  const nextErrors = {};
  const trimmedName = name.value.trim();

  if (!trimmedName) {
    nextErrors.name = "Enter a device name.";
  } else if (trimmedName.length > 100) {
    nextErrors.name = "Use 100 characters or fewer.";
  }

  if (!isEditing.value && !Object.hasOwn(deviceTypeLabels, deviceType.value)) {
    nextErrors.deviceType = "Choose a device type.";
  }

  if (description.value.length > 1000) {
    nextErrors.description = "Use 1,000 characters or fewer.";
  }

  errors.value = nextErrors;

  if (!Object.keys(nextErrors).length) return true;

  await nextTick();

  if (isDisposed) return false;

  if (nextErrors.name) nameInput.value?.focus();
  else if (nextErrors.deviceType) typeInput.value?.focus();
  else descriptionInput.value?.focus();

  return false;
}

async function submit() {
  if (
    isSaving.value ||
    isValidating ||
    (isEditing.value && !hasChanges.value)
  ) {
    return;
  }

  isValidating = true;
  const isValid = await validate();
  isValidating = false;
  if (!isValid || isDisposed) return;

  isSaving.value = true;
  submissionError.value = "";
  const controller = new AbortController();
  pendingRequest = controller;

  try {
    const device = isEditing.value
      ? await updateDevice(
          props.device.id,
          changes.value,
          auth.token,
          controller.signal,
        )
      : await createDevice(
          {
            name: name.value.trim(),
            deviceType: deviceType.value,
            description: description.value || null,
          },
          auth.token,
          controller.signal,
        );

    if (isDisposed || controller.signal.aborted) return;

    if (isEditing.value) emit("updated", device);
    else emit("created", device);
  } catch (failure) {
    if (isDisposed || controller.signal.aborted) return;

    if (failure.status === 401) {
      auth.logout();
      await router.replace({
        name: "login",
        query: { expired: "1" },
      });
      return;
    }

    if (!failure.status || failure.status >= 500) {
      submissionError.value = isEditing.value
        ? "We could not confirm whether your changes were saved. Check the device details before trying again."
        : "We could not confirm whether the device was created. Check the device list before trying again.";
    } else {
      submissionError.value = failure.message;
    }
  } finally {
    if (pendingRequest === controller) pendingRequest = undefined;
    if (!isDisposed) isSaving.value = false;
  }
}

onBeforeUnmount(() => {
  isDisposed = true;
  pendingRequest?.abort();
});
</script>

<template>
  <BaseDialog
    v-slot="{ close }"
    :title="isEditing ? 'Edit device' : 'Add device'"
    :close-disabled="isSaving"
    :initial-focus="focusName"
    @close="emit('close')"
  >
    <form
      class="device-form"
      novalidate
      :aria-busy="isSaving"
      @submit.prevent="submit"
    >
      <div class="device-form__field">
        <label class="device-form__label" :for="`${formId}-name`">
          Device name
        </label>
        <BaseInput
          :id="`${formId}-name`"
          ref="nameInput"
          v-model="name"
          name="name"
          required
          maxlength="100"
          autocomplete="off"
          placeholder="e.g. Freezer sensor 01"
          :readonly="isSaving"
          :aria-invalid="errors.name ? true : undefined"
          :aria-describedby="errors.name ? `${formId}-name-error` : undefined"
          @update:model-value="clearError('name')"
        />
        <p
          v-if="errors.name"
          :id="`${formId}-name-error`"
          class="message message--error device-form__message"
        >
          {{ errors.name }}
        </p>
      </div>

      <div class="device-form__field">
        <label class="device-form__label" :for="`${formId}-type`">
          Device type
        </label>
        <BaseInput
          v-if="isEditing"
          :id="`${formId}-type`"
          :model-value="deviceTypeLabels[deviceType]"
          disabled
          :aria-describedby="`${formId}-type-hint`"
        />
        <BaseSelect
          v-else
          :id="`${formId}-type`"
          ref="typeInput"
          v-model="deviceType"
          label="Device type"
          placeholder="Choose a device type"
          :options="typeOptions"
          :disabled="isSaving"
          aria-required="true"
          :aria-invalid="errors.deviceType ? true : undefined"
          :aria-describedby="
            errors.deviceType
              ? `${formId}-type-hint ${formId}-type-error`
              : `${formId}-type-hint`
          "
          @update:model-value="clearError('deviceType')"
        />
        <p
          :id="`${formId}-type-hint`"
          class="supporting-text device-form__hint"
        >
          Device type cannot be changed after creation.
        </p>
        <p
          v-if="errors.deviceType"
          :id="`${formId}-type-error`"
          class="message message--error device-form__message"
        >
          {{ errors.deviceType }}
        </p>
      </div>

      <div class="device-form__field">
        <label class="device-form__label" :for="`${formId}-description`">
          Description (optional)
        </label>
        <BaseTextarea
          :id="`${formId}-description`"
          ref="descriptionInput"
          v-model="description"
          name="description"
          rows="4"
          maxlength="1000"
          placeholder="Where is this device and what does it monitor?"
          :readonly="isSaving"
          :aria-invalid="errors.description ? true : undefined"
          :aria-describedby="
            errors.description
              ? `${formId}-description-hint ${formId}-description-error`
              : `${formId}-description-hint`
          "
          @update:model-value="clearError('description')"
        />
        <p
          :id="`${formId}-description-hint`"
          class="supporting-text device-form__hint"
        >
          Up to 1,000 characters.
        </p>
        <p
          v-if="errors.description"
          :id="`${formId}-description-error`"
          class="message message--error device-form__message"
        >
          {{ errors.description }}
        </p>
      </div>

      <p v-if="!isEditing" class="supporting-text device-form__hint">
        New devices start active.
      </p>

      <p
        v-if="submissionError"
        class="message message--error device-form__message"
        role="alert"
      >
        {{ submissionError }}
      </p>

      <div class="device-form__actions">
        <BaseButton :disabled="isSaving" @click="close"> Cancel </BaseButton>
        <BaseButton
          variant="primary"
          type="submit"
          :disabled="isSaving || (isEditing && !hasChanges)"
        >
          {{ submitLabel }}
        </BaseButton>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped lang="scss">
.device-form {
  display: grid;
  gap: 1.25rem;
}

.device-form__field {
  display: grid;
  gap: 0.5rem;
  min-width: 0;
}

.device-form__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.device-form__hint,
.device-form__message {
  margin: 0;
}

.device-form__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.25rem;
}
</style>
