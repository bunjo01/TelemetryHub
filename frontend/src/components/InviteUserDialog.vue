<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { inviteMember, inviteOwner } from "../api/invitations.api.js";
import { useAuthStore } from "../stores/auth.js";
import { useNotificationStore } from "../stores/notifications.js";
import BaseButton from "./BaseButton.vue";
import BaseInput from "./BaseInput.vue";
import CompanyPicker from "./CompanyPicker.vue";

const props = defineProps({
  recipient: {
    type: String,
    required: true,
    validator: (value) => ["owner", "member"].includes(value),
  },
});
const isOwnerInvitation = computed(() => props.recipient === "owner");
const emit = defineEmits(["close"]);
const auth = useAuthStore();
const notifications = useNotificationStore();
let notificationTarget;
const router = useRouter();
const dialog = ref(null);
const emailInput = ref(null);
const companyPicker = ref(null);
const email = ref("");
const selected = ref(null);
const isSaving = ref(false);
const error = ref("");
const invitation = ref(null);
const copySuccessMessage = "Invitation link copied.";
const copyFailureMessage =
  "Unable to copy automatically. Select the link and copy it manually.";
const invitationLink = computed(() => {
  if (!invitation.value) return "";
  const href = router.resolve({
    name: "register",
    hash: `#token=${invitation.value.token}`,
  }).href;
  return new URL(href, window.location.origin).href;
});
async function copyLink() {
  notifications.remove("invitation-copy");
  try {
    await navigator.clipboard.writeText(invitationLink.value);
    if (!isDisposed)
      notifications.show({
        key: "invitation-copy",
        variant: "success",
        message: copySuccessMessage,
      });
  } catch {
    if (!isDisposed)
      notifications.show({
        key: "invitation-copy",
        variant: "error",
        message: copyFailureMessage,
      });
  }
}
let invitationRequest;
let isDisposed = false;

onMounted(() => {
  dialog.value.showModal();
  notificationTarget = dialog.value;
  notifications.registerTarget(notificationTarget);
  emailInput.value.focus();
});

onBeforeUnmount(() => {
  isDisposed = true;
  invitationRequest?.abort();
  notifications.unregisterTarget(notificationTarget);
  notifications.remove("invitation-copy");
  notifications.remove("invitation-submit");
});
async function handleFailure(failure, origin) {
  if (failure.status === 401) {
    auth.logout();
    await router.replace({ name: "login", query: { expired: "1" } });
  } else
    notifications.show({
      key: "invitation-submit",
      variant: "error",
      message: failure.message,
      origin,
    });
}
function handlePickerUnauthorized(failure) {
  return handleFailure(failure);
}
function clearError() {
  error.value = "";
}
function close() {
  if (isSaving.value) return;
  notifications.unregisterTarget(notificationTarget);
  dialog.value.close();
  emit("close");
}
async function submit() {
  if (isSaving.value) return;
  const origin = document.activeElement;
  error.value = "";
  notifications.remove("invitation-submit");
  if (isOwnerInvitation.value && !selected.value) {
    error.value = "Choose a company.";
    companyPicker.value.focus();
    return;
  }
  isSaving.value = true;
  const controller = new AbortController();
  invitationRequest = controller;
  try {
    const createInvitation = isOwnerInvitation.value
      ? inviteOwner
      : inviteMember;
    const result = await createInvitation(
      isOwnerInvitation.value ? selected.value.id : auth.user.companyId,
      email.value,
      auth.token,
      controller.signal,
    );
    if (controller.signal.aborted || isDisposed) return;
    invitation.value = result;
    notifications.show({
      key: "invitation-submit",
      variant: "success",
      message: "Invitation created.",
    });
    await nextTick();
    dialog.value.querySelector(".invitation-result")?.focus();
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed)
      await handleFailure(failure, origin);
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    class="panel invitation-dialog"
    aria-labelledby="invitation-title"
    @cancel.prevent="close"
  >
    <div class="invitation-dialog__heading">
      <h2 id="invitation-title" class="invitation-dialog__title">
        {{ isOwnerInvitation ? "Invite company owner" : "Invite member" }}
      </h2>
      <button
        class="invitation-dialog__close"
        type="button"
        :aria-label="`Close invite ${recipient}`"
        :disabled="isSaving"
        @click="close"
      >
        ×
      </button>
    </div>
    <section
      v-if="invitation"
      class="invitation-result"
      tabindex="-1"
      aria-label="Invitation created"
    >
      <p class="invitation-result__summary">
        Invitation created for {{ invitation.email
        }}<template v-if="isOwnerInvitation"> at {{ selected.name }}</template>.
      </p>
      <p class="supporting-text">
        No email was sent. Share this invitation link with the {{ recipient }}.
        It is only available here until you close this popup.
      </p>
      <label class="invitation-result__label" for="invitation-link"
        >Invitation link</label
      >
      <textarea
        id="invitation-link"
        class="invitation-result__link"
        :value="invitationLink"
        readonly
        rows="3"
        spellcheck="false"
      />
      <div class="invitation-result__actions">
        <BaseButton variant="secondary" type="button" @click="copyLink">
          Copy link
        </BaseButton>
      </div>
      <p class="supporting-text">
        Expires {{ new Date(invitation.expiresAt).toLocaleString() }}.
      </p>
    </section>
    <form
      v-else
      class="invitation-form"
      @submit.prevent="submit"
      :aria-busy="isSaving"
    >
      <label class="invitation-form__label" for="invitation-email">{{
        isOwnerInvitation ? "Owner email address" : "Member email address"
      }}</label>
      <BaseInput
        id="invitation-email"
        ref="emailInput"
        v-model="email"
        type="email"
        required
        maxlength="254"
        autocomplete="email"
        :placeholder="`${recipient}@company.com`"
        :readonly="isSaving"
      />
      <CompanyPicker
        v-if="isOwnerInvitation"
        ref="companyPicker"
        v-model="selected"
        :disabled="isSaving"
        :error-message="error"
        @update:model-value="clearError"
        @unauthorized="handlePickerUnauthorized"
      />
      <BaseButton
        class="invitation-form__submit"
        variant="primary"
        type="submit"
        :disabled="isSaving"
      >
        {{ isSaving ? "Creating invitation…" : `Invite ${recipient}` }}
      </BaseButton>
    </form>
  </dialog>
</template>

<style scoped lang="scss">
.invitation-dialog {
  width: min(480px, calc(100% - 2rem));
  max-height: calc(100svh - 2rem);
  padding: 1.75rem;
  color: var(--text);
  overflow-y: auto;
}

.invitation-dialog::backdrop {
  background: #030810b8;
  backdrop-filter: blur(5px);
}

.invitation-dialog__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.invitation-dialog__title {
  font-size: 1.4rem;
  font-weight: 500;
  margin: 0;
}

.invitation-dialog__close {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 0.5rem;
  background: transparent;
  color: var(--muted);
  font-size: 1.5rem;
}

.invitation-form {
  display: grid;
  gap: 0.75rem;
}

.invitation-form__label,
.invitation-result__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.invitation-form__submit {
  margin-top: 0.75rem;
}

.invitation-result {
  overflow-wrap: anywhere;
}

.invitation-result:focus {
  outline: none;
}

.invitation-result__link {
  display: block;
  width: 100%;
  margin: 0.5rem 0 1rem;
  background: #09121e;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 0.5rem;
  padding: 0.75rem;
  resize: vertical;
  font: inherit;
}

.invitation-result__actions {
  display: flex;
  align-items: center;
}
</style>
