<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { roleLabels } from "../api/auth.api.js";
import { createCompany } from "../api/companies.api.js";
import { useAuthStore } from "../stores/auth.js";

const auth = useAuthStore();
const router = useRouter();
const isAdmin = computed(() => auth.user?.role === "system_admin");
const isOwner = computed(() => auth.user?.role === "company_owner");
const companyDialog = ref(null);
const name = ref("");
const nameInput = ref(null);
const createButton = ref(null);
const isSaving = ref(false);
const error = ref("");
const success = ref("");
let pendingRequest;
onBeforeUnmount(() => pendingRequest?.abort());

function openCompanyDialog() {
  error.value = "";
  success.value = "";
  name.value = "";
  companyDialog.value.showModal();
  nameInput.value?.focus();
}
async function closeCompanyDialog() {
  if (isSaving.value) return;
  companyDialog.value.close();
  await nextTick();
  createButton.value?.focus();
}
async function submitCompany() {
  if (isSaving.value) return;
  error.value = "";
  success.value = "";
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
    success.value = `${company.name} was created successfully.`;
    name.value = "";
    isSaving.value = false;
    closeCompanyDialog();
  } catch (failure) {
    if (controller.signal.aborted) return;
    if (failure.status === 401) {
      auth.logout();
      await router.replace({ name: "login", query: { expired: "1" } });
    } else {
      error.value = failure.message;
    }
  } finally {
    isSaving.value = false;
    if (pendingRequest === controller) pendingRequest = undefined;
  }
}
</script>

<template>
  <main v-if="auth.user" id="main" class="profile-layout">
    <div class="page-heading">
      <p class="eyebrow">YOUR PERSONAL ORBIT</p>
      <h1 tabindex="-1">Welcome to your space.</h1>
      <p class="muted">
        Your profile and the tools to bring your team together.
      </p>
    </div>
    <div class="profile-grid">
      <section class="panel identity" aria-labelledby="profile-title">
        <div class="avatar" aria-hidden="true">
          {{ auth.user.email.charAt(0).toUpperCase() }}<span>✧</span>
        </div>
        <p class="eyebrow">CONNECTED TO TELEMETRYHUB</p>
        <h2 id="profile-title">Your profile</h2>
        <dl>
          <div>
            <dt>Email address</dt>
            <dd>{{ auth.user.email }}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>
              <span class="role-badge">{{ roleLabels[auth.user.role] }}</span>
            </dd>
          </div>
        </dl>
      </section>
      <section class="panel workspace" aria-labelledby="workspace-title">
        <div class="workspace-heading">
          <span class="section-icon" aria-hidden="true">⌘</span
          ><span class="eyebrow">MISSION CONTROL</span>
        </div>
        <h2 id="workspace-title">
          {{
            isAdmin || isOwner ? "Build your connected world." : "You're part of the crew."
          }}
        </h2>
        <p class="muted workspace-description">
          {{
            isAdmin
              ? "Create a home for a new team. Company owners will help take it from there."
              : isOwner
                ? "Great things start with a connected team. This is where yours comes together."
                : "Your account is ready. Device monitoring and more will arrive here as your workspace grows."
          }}
        </p>
        <div v-if="isAdmin || isOwner" class="actions">
          <button
            v-if="isAdmin"
            ref="createButton"
            type="button"
            class="button primary"
            :disabled="isSaving"
            aria-haspopup="dialog"
            aria-controls="company-dialog"
            @click="openCompanyDialog"
          >
            <span aria-hidden="true">＋</span>
            Create company
          </button>
          <button
            class="button secondary"
            type="button"
            disabled
            aria-describedby="invitation-note"
          >
            {{ isAdmin ? "Invite owner" : "Invite member" }}
            <span aria-hidden="true">↗</span>
          </button>
        </div>
        <p v-if="isAdmin || isOwner" id="invitation-note" class="coming-soon">
          Invitations are coming soon.
        </p>
        <p v-if="success" class="message success" role="status">
          {{ success }}
        </p>
        <div class="workspace-art" aria-hidden="true">
          <div class="ring ring-one"></div>
          <div class="ring ring-two"></div>
          <span>✧</span><i></i>
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
      <div class="dialog-heading">
        <h2 id="company-dialog-title">Create company</h2>
        <button
          type="button"
          class="close-button"
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
        <label for="company-name">Company name</label>
        <input
          id="company-name"
          ref="nameInput"
          v-model="name"
          required
          maxlength="200"
          autocomplete="organization"
          placeholder="e.g. Orbital Labs"
          :readonly="isSaving"
          :aria-describedby="error ? 'company-error' : undefined"
        >
        <p v-if="error" id="company-error" class="message error" role="alert">
          {{ error }}
        </p>
        <button class="button primary" type="submit" :disabled="isSaving">
          {{ isSaving ? "Creating…" : "Create" }}
        </button>
      </form>
    </dialog>
  </main>
</template>

<style scoped lang="scss">
.profile-layout { width: min(1100px, 90%); margin: 0 auto; padding: 4rem 0 5rem; }
.page-heading { margin-bottom: 2.8rem; }
h1 { font-size: clamp(2rem, 4vw, 3rem); font-weight: 450; letter-spacing: -.045em; margin: .8rem 0; }
h2 { font-size: 1.5rem; font-weight: 500; letter-spacing: -.025em; }
.profile-grid { display: grid; grid-template-columns: .85fr 1.4fr; gap: 1.5rem; }
.identity, .workspace { padding: 2.25rem; }
.avatar { height: 5rem; width: 5rem; display: grid; place-items: center; position: relative; color: var(--accent); font-size: 2rem; border-radius: 50%; border: 1px solid #8ae7d644; background: radial-gradient(at top left, #355e61, #12212c); margin-bottom: 2rem; }
.avatar span { position: absolute; bottom: -.2rem; right: -.2rem; background: #10232c; border: 1px solid var(--line); width: 1.7rem; height: 1.7rem; border-radius: 50%; font-size: 1rem; text-align: center; }
dl { margin: 2rem 0 0; } dl > div { padding: 1.3rem 0; border-top: 1px solid var(--line); } dt { color: var(--muted); font-size: .8rem; margin-bottom: .6rem; } dd { margin: 0; overflow-wrap: anywhere; font-size: .95rem; }
.role-badge { display: inline-block; border-radius: .35rem; background: #8ae7d60d; border: 1px solid #8ae7d629; padding: .3rem .6rem; color: var(--accent); font-size: .8rem; }
.workspace { position: relative; overflow: hidden; min-height: 420px; }
.workspace-heading { display: flex; align-items: center; gap: .7rem; }
.section-icon { font-size: 1.4rem; color: var(--accent); }
.workspace-description { max-width: 27rem; line-height: 1.8; }
.actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.5rem; }
.coming-soon { font-size: .75rem; color: var(--muted); }
.company-dialog { width: min(440px, calc(100% - 2rem)); max-height: calc(100svh - 2rem); padding: 1.75rem; color: var(--text); }
.company-dialog::backdrop { background: #030810b8; backdrop-filter: blur(5px); }
.dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.75rem; }
.dialog-heading h2 { margin: 0; }
.close-button { display: grid; place-items: center; width: 2.75rem; height: 2.75rem; flex-shrink: 0; padding: 0; border: 1px solid var(--line); border-radius: .5rem; background: transparent; color: var(--muted); font-size: 1.5rem; }
.close-button:hover:not(:disabled) { color: var(--text); background: #223547; }
.company-form { display: grid; gap: .75rem; }
.company-form .primary { margin-top: .75rem; }
.company-form .message { margin: 0; }
.workspace-art { position: relative; height: 130px; opacity: .55; pointer-events: none; margin-top: 2rem; } .ring { position: absolute; border: 1px solid #72b5bb44; width: 320px; height: 140px; border-radius: 50%; right: -60px; top: 20px; transform: rotate(-25deg); } .ring-two { transform: rotate(25deg); border-style: dashed; } .workspace-art > span { position: absolute; right: 60px; top: 35px; font-size: 3rem; color: var(--accent); } .workspace-art i { position: absolute; right: 220px; top: 105px; border-radius: 50%; width: 6px; height: 6px; background: var(--accent); box-shadow: 0 0 20px var(--accent); }
@media (max-width: 700px) { .profile-grid { grid-template-columns: 1fr; } .profile-layout { padding-top: 2.5rem; } .identity, .workspace { padding: 1.5rem; } }
</style>
