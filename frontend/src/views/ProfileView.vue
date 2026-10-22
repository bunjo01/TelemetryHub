<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { roleLabels } from "../api/auth.api.js";
import { createCompany } from "../api/companies.api.js";
import BaseButton from "../components/BaseButton.vue";
import BaseInput from "../components/BaseInput.vue";
import InviteUserDialog from "../components/InviteUserDialog.vue";
import { useAuthStore } from "../stores/auth.js";
import { useNotificationStore } from "../stores/notifications.js";

const auth = useAuthStore();
const notifications = useNotificationStore();
let notificationTarget;
const router = useRouter();
const isAdmin = computed(() => auth.user?.role === "system_admin");
const isOwner = computed(() => auth.user?.role === "company_owner");
const companyDialog = ref(null);
const isInvitationOpen = ref(false);
function closeInvitation() {
  isInvitationOpen.value = false;
}
const name = ref("");
const nameInput = ref(null);
const isSaving = ref(false);
const error = ref("");
let pendingRequest;
onBeforeUnmount(() => {
  pendingRequest?.abort();
  notifications.unregisterTarget(notificationTarget);
});

function openCompanyDialog() {
  error.value = "";
  notifications.remove("company-create");
  name.value = "";
  companyDialog.value.showModal();
  notificationTarget = companyDialog.value;
  notifications.registerTarget(notificationTarget);
  nameInput.value?.focus();
}
function closeCompanyDialog() {
  if (isSaving.value) return;
  notifications.unregisterTarget(notificationTarget);
  companyDialog.value.close();
}
async function submitCompany() {
  if (isSaving.value) return;
  const origin = document.activeElement;
  error.value = "";
  notifications.remove("company-create");
  if (!name.value.trim()) {
    error.value = "Enter a company name.";
    nameInput.value?.focus();
    return;
  }
  isSaving.value = true;
  const controller = new AbortController();
  pendingRequest = controller;
  try {
    const company = await createCompany(
      name.value.trim(),
      auth.token,
      controller.signal,
    );
    if (controller.signal.aborted) return;
    notifications.show({
      key: "company-create",
      variant: "success",
      message: `${company.name} was created successfully.`,
    });
    name.value = "";
    isSaving.value = false;
    closeCompanyDialog();
  } catch (failure) {
    if (controller.signal.aborted) return;
    if (failure.status === 401) {
      auth.logout();
      await router.replace({ name: "login", query: { expired: "1" } });
    } else {
      notifications.show({
        key: "company-create",
        variant: "error",
        message: failure.message,
        origin,
      });
    }
  } finally {
    isSaving.value = false;
    if (pendingRequest === controller) pendingRequest = undefined;
  }
}
</script>

<template>
  <main v-if="auth.user" id="main" class="profile-layout">
    <div class="profile-layout__heading">
      <p class="eyebrow">YOUR PERSONAL ORBIT</p>
      <h1 class="profile-layout__title" tabindex="-1">
        Welcome to your space.
      </h1>
      <p class="supporting-text">
        Your profile and the tools to bring your team together.
      </p>
    </div>
    <div class="profile-layout__grid">
      <section class="panel profile-card" aria-labelledby="profile-title">
        <div class="profile-card__avatar" aria-hidden="true">
          {{ auth.user.email.charAt(0).toUpperCase()
          }}<span class="profile-card__avatar-mark">✧</span>
        </div>
        <p class="eyebrow">CONNECTED TO TELEMETRYHUB</p>
        <h2 id="profile-title" class="profile-card__title">Your profile</h2>
        <dl class="profile-card__details">
          <div class="profile-card__detail">
            <dt class="profile-card__label">Email address</dt>
            <dd class="profile-card__value">{{ auth.user.email }}</dd>
          </div>
          <div class="profile-card__detail">
            <dt class="profile-card__label">Role</dt>
            <dd class="profile-card__value">
              <span class="profile-card__role">{{
                roleLabels[auth.user.role]
              }}</span>
            </dd>
          </div>
        </dl>
      </section>
      <section class="panel workspace" aria-labelledby="workspace-title">
        <div class="workspace__heading">
          <span class="workspace__icon" aria-hidden="true">⌘</span
          ><span class="eyebrow">MISSION CONTROL</span>
        </div>
        <h2 id="workspace-title" class="workspace__title">
          {{
            isAdmin || isOwner ? "Build your connected world." : "You're part of the crew."
          }}
        </h2>
        <p class="supporting-text workspace__description">
          {{
            isAdmin
              ? "Create a home for a new team. Company owners will help take it from there."
              : isOwner
                ? "Great things start with a connected team. This is where yours comes together."
                : "Your account is ready. Device monitoring and more will arrive here as your workspace grows."
          }}
        </p>
        <div v-if="isAdmin || isOwner" class="workspace__actions">
          <BaseButton
            v-if="isAdmin"
            variant="primary"
            type="button"
            :disabled="isSaving"
            aria-haspopup="dialog"
            aria-controls="company-dialog"
            @click="openCompanyDialog"
          >
            <span aria-hidden="true">＋</span>
            Create company
          </BaseButton>
          <BaseButton
            v-if="isAdmin"
            variant="secondary"
            type="button"
            aria-haspopup="dialog"
            @click="isInvitationOpen = true"
          >
            Invite owner <span aria-hidden="true">↗</span>
          </BaseButton>
          <BaseButton
            v-else
            variant="secondary"
            type="button"
            aria-haspopup="dialog"
            @click="isInvitationOpen = true"
          >
            Invite member
            <span aria-hidden="true">↗</span>
          </BaseButton>
        </div>
        <div class="workspace__art" aria-hidden="true">
          <div class="workspace__ring"></div>
          <div class="workspace__ring workspace__ring--crossed"></div>
          <span class="workspace__star">✧</span><i class="workspace__node"></i>
        </div>
      </section>
    </div>
    <dialog
      v-if="isAdmin"
      id="company-dialog"
      ref="companyDialog"
      class="panel company-dialog"
      aria-labelledby="company-dialog-title"
      @cancel.prevent="closeCompanyDialog"
    >
      <div class="company-dialog__heading">
        <h2 id="company-dialog-title" class="company-dialog__title">
          Create company
        </h2>
        <button
          type="button"
          class="company-dialog__close"
          aria-label="Close create company"
          :disabled="isSaving"
          @click="closeCompanyDialog"
        >
          ×
        </button>
      </div>
      <form
        class="company-form"
        :aria-busy="isSaving"
        @submit.prevent="submitCompany"
      >
        <label class="company-form__label" for="company-name"
          >Company name</label
        >
        <BaseInput
          id="company-name"
          ref="nameInput"
          v-model="name"
          required
          maxlength="200"
          autocomplete="organization"
          placeholder="e.g. Orbital Labs"
          :readonly="isSaving"
          :aria-invalid="error ? true : undefined"
          @update:model-value="error = ''"
          :aria-describedby="error ? 'company-error' : undefined"
        />
        <p
          v-if="error"
          id="company-error"
          class="message message--error company-form__message"
          role="alert"
        >
          {{ error }}
        </p>
        <BaseButton
          class="company-form__submit"
          variant="primary"
          type="submit"
          :disabled="isSaving"
        >
          {{ isSaving ? "Creating…" : "Create" }}
        </BaseButton>
      </form>
    </dialog>
    <InviteUserDialog
      v-if="(isAdmin || isOwner) && isInvitationOpen"
      :recipient="isAdmin ? 'owner' : 'member'"
      @close="closeInvitation"
    />
  </main>
</template>

<style scoped lang="scss">
.profile-layout {
  width: min(1100px, 90%);
  margin: 0 auto;
  padding: clamp(1.5rem, 4svh, 4rem) 0;
}

.profile-layout__heading {
  margin-bottom: 2.8rem;
}

.profile-layout__title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 450;
  letter-spacing: -0.045em;
  margin: 0.8rem 0;
}

.profile-card__title,
.workspace__title,
.company-dialog__title {
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: -0.025em;
}

.profile-layout__grid {
  display: grid;
  grid-template-columns: 0.85fr 1.4fr;
  gap: 1.5rem;
}

.profile-card,
.workspace {
  padding: 2.25rem;
}

.profile-card__avatar {
  height: 5rem;
  width: 5rem;
  display: grid;
  place-items: center;
  position: relative;
  color: var(--accent);
  font-size: 2rem;
  border-radius: 50%;
  border: 1px solid #8ae7d644;
  background: radial-gradient(at top left, #355e61, #12212c);
  margin-bottom: 2rem;
}

.profile-card__avatar-mark {
  position: absolute;
  bottom: -0.2rem;
  right: -0.2rem;
  background: #10232c;
  border: 1px solid var(--line);
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  font-size: 1rem;
  text-align: center;
}

.profile-card__details {
  margin: 2rem 0 0;
}

.profile-card__detail {
  padding: 1.3rem 0;
  border-top: 1px solid var(--line);
}

.profile-card__label {
  color: var(--muted);
  font-size: 0.8rem;
  margin-bottom: 0.6rem;
}

.profile-card__value {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 0.95rem;
}

.profile-card__role {
  display: inline-block;
  border-radius: 0.35rem;
  background: #8ae7d60d;
  border: 1px solid #8ae7d629;
  padding: 0.3rem 0.6rem;
  color: var(--accent);
  font-size: 0.8rem;
}

.workspace {
  position: relative;
  overflow: hidden;
  min-height: 420px;
}

.workspace__heading {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.workspace__icon {
  font-size: 1.4rem;
  color: var(--accent);
}

.workspace__description {
  max-width: 27rem;
  line-height: 1.8;
}

.workspace__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.workspace__art {
  position: relative;
  height: 130px;
  opacity: 0.55;
  pointer-events: none;
  margin-top: 2rem;
}

.workspace__ring {
  position: absolute;
  border: 1px solid #72b5bb44;
  width: 320px;
  height: 140px;
  border-radius: 50%;
  right: -60px;
  top: 20px;
  transform: rotate(-25deg);
}

.workspace__ring--crossed {
  transform: rotate(25deg);
  border-style: dashed;
}

.workspace__star {
  position: absolute;
  right: 60px;
  top: 35px;
  font-size: 3rem;
  color: var(--accent);
}

.workspace__node {
  position: absolute;
  right: 220px;
  top: 105px;
  border-radius: 50%;
  width: 6px;
  height: 6px;
  background: var(--accent);
  box-shadow: 0 0 20px var(--accent);
}

.company-dialog {
  width: min(440px, calc(100% - 2rem));
  max-height: calc(100svh - 2rem);
  padding: 1.75rem;
  color: var(--text);
}

.company-dialog::backdrop {
  background: #030810b8;
  backdrop-filter: blur(5px);
}

.company-dialog__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.company-dialog__title {
  margin: 0;
}

.company-dialog__close {
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

.company-dialog__close:hover:not(:disabled) {
  color: var(--text);
  background: #223547;
}

.company-form {
  display: grid;
  gap: 0.75rem;
}

.company-form__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.company-form__submit {
  margin-top: 0.75rem;
}

.company-form__message {
  margin: 0;
}

@media (max-width: 700px) {
  .profile-layout__grid {
    grid-template-columns: 1fr;
  }

  .profile-layout {
    padding-top: 2.5rem;
  }

  .profile-card,
  .workspace {
    padding: 1.5rem;
  }
}

@media (min-width: 701px) and (max-height: 900px) {
  .profile-layout {
    margin-block: auto;
    padding-block: 1.25rem;
  }

  .profile-layout__heading {
    margin-bottom: 1.5rem;
  }

  .profile-layout__title {
    font-size: 2.25rem;
    margin-block: 0.5rem;
  }

  .profile-card,
  .workspace {
    padding: 1.5rem;
  }

  .profile-card__avatar {
    width: 4rem;
    height: 4rem;
    margin-bottom: 1rem;
  }

  .profile-card__details {
    margin-top: 1.25rem;
  }

  .profile-card__detail {
    padding-block: 1rem;
  }

  .workspace {
    min-height: 0;
  }

  .workspace__art {
    height: 85px;
    margin-top: 1rem;
  }
}
</style>
