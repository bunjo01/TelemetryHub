<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { inviteMember, inviteOwner } from "../api/invitations.api.js";
import { useAuthStore } from "../stores/auth.js";
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
const router = useRouter();
const dialog = ref(null);
const emailInput = ref(null);
const companyPicker = ref(null);
const email = ref("");
const selected = ref(null);
const isSaving = ref(false);
const error = ref("");
const invitation = ref(null);
const copyMessage = ref("");
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
  try {
    await navigator.clipboard.writeText(invitationLink.value);
    if (!isDisposed) copyMessage.value = copySuccessMessage;
  } catch {
    if (!isDisposed) copyMessage.value = copyFailureMessage;
  }
}
let invitationRequest;
let isDisposed = false;

onMounted(() => {
  dialog.value.showModal();
  emailInput.value.focus();
});

onBeforeUnmount(() => {
  isDisposed = true;
  invitationRequest?.abort();
});
async function handleFailure(failure, destination) {
  if (failure.status === 401) {
    auth.logout();
    await router.replace({ name: "login", query: { expired: "1" } });
  } else destination.value = failure.message;
}
function handlePickerUnauthorized(failure) {
  return handleFailure(failure, error);
}
function clearError() {
  error.value = "";
}
function close() {
  if (isSaving.value) return;
  dialog.value.close();
  emit("close");
}
async function submit() {
  if (isSaving.value) return;
  error.value = "";
  if (isOwnerInvitation.value && !selected.value) {
    error.value = "Choose a company from the dropdown.";
    companyPicker.value.open();
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
    await nextTick();
    dialog.value.querySelector(".invitation-result")?.focus();
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed)
      await handleFailure(failure, error);
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    class="panel owner-dialog"
    aria-labelledby="invitation-title"
    @cancel.prevent="close"
  >
    <div class="dialog-heading">
      <h2 id="invitation-title">
        {{ isOwnerInvitation ? "Invite company owner" : "Invite member" }}
      </h2>
      <button
        class="close-button"
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
      <p class="message success" role="status">
        Invitation created for {{ invitation.email
        }}<template v-if="isOwnerInvitation"> at {{ selected.name }}</template>.
      </p>
      <p class="muted">
        No email was sent. Share this invitation link with the {{ recipient }}.
        It is only available here until you close this popup.
      </p>
      <label for="invitation-link">Invitation link</label>
      <textarea
        id="invitation-link"
        :value="invitationLink"
        readonly
        rows="3"
        spellcheck="false"
      />
      <div class="copy-actions">
        <BaseButton
          class="secondary"
          variant="secondary"
          type="button"
          @click="copyLink"
        >
          Copy link
        </BaseButton>
        <div class="copy-feedback">
          <span class="copy-placeholder" aria-hidden="true">{{
            copySuccessMessage
          }}</span>
          <span class="copy-placeholder" aria-hidden="true">{{
            copyFailureMessage
          }}</span>
          <p role="status" aria-live="polite" aria-atomic="true">
            {{ copyMessage }}
          </p>
        </div>
      </div>
      <p class="muted">
        Expires {{ new Date(invitation.expiresAt).toLocaleString() }}.
      </p>
    </section>
    <form v-else @submit.prevent="submit" :aria-busy="isSaving">
      <label for="invitation-email">{{
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
        :aria-describedby="error ? 'invitation-error' : undefined"
      />
      <CompanyPicker
        v-if="isOwnerInvitation"
        ref="companyPicker"
        v-model="selected"
        :disabled="isSaving"
        @update:model-value="clearError"
        @unauthorized="handlePickerUnauthorized"
      />
      <p v-if="error" id="invitation-error" class="message error" role="alert">
        {{ error }}
      </p>
      <BaseButton
        class="primary"
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
.owner-dialog { width: min(480px, calc(100% - 2rem)); max-height: calc(100svh - 2rem); padding: 1.75rem; color: var(--text); overflow: visible; }
.owner-dialog::backdrop { background: #030810b8; backdrop-filter: blur(5px); }
.dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.75rem; }
h2 { font-size: 1.4rem; font-weight: 500; margin: 0; }
.close-button { display: grid; place-items: center; width: 2.75rem; height: 2.75rem; flex-shrink: 0; padding: 0; border: 1px solid var(--line); border-radius: .5rem; background: transparent; color: var(--muted); font-size: 1.5rem; }
form { display: grid; gap: .75rem; }
form > .primary { margin-top: .75rem; }
textarea { display: block; width: 100%; margin: .5rem 0 1rem; background: #09121e; color: var(--text); border: 1px solid var(--line); border-radius: .5rem; padding: .75rem; resize: vertical; font: inherit; }
.invitation-result { overflow-wrap: anywhere; }
.copy-actions { display: grid; grid-template-columns: max-content minmax(0, 1fr); align-items: center; gap: .75rem; }
.copy-feedback { display: grid; min-width: 0; color: var(--muted); font-size: .8rem; line-height: 1.5; overflow-wrap: anywhere; }
.copy-feedback > * { grid-area: 1 / 1; margin: 0; align-self: center; }
// Reserve the space required by either outcome, even before the first copy attempt.
.copy-placeholder { visibility: hidden; }
// This section receives focus to announce the result; controls retain their focus rings.
.invitation-result:focus { outline: none; }
</style>
