<script lang="ts">
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<svelte:head>
  <title>radbrain · workspace</title>
  <meta name="description" content="Your private radiology study workspace." />
</svelte:head>

<section class="hero">
  <p class="eyebrow">Radiology Brain OS</p>
  <h1>A focused workspace for your next exam.</h1>
  <p class="lede">
    radbrain keeps sources, figures, study plans, and assessments in one private,
    provenance-first home. This initial shell is ready for your library.
  </p>
  {#if data.user}
    <div class="account-card" data-user-subject={data.user.subject}>
      <span class="status-dot"></span>
      <div>
        <strong>Signed in as {data.user.name}</strong>
        <small>{data.user.email ?? data.user.subject} · {data.user.tenantRole}</small>
      </div>
      <form method="POST" action="/auth/logout">
        <button class="button secondary" type="submit">Sign out</button>
      </form>
    </div>
  {:else if data.authEnabled}
    <a class="button" href="/auth/login">Sign in with Keycloak <span aria-hidden="true">→</span></a>
  {:else}
    <div class="notice">
      <strong>Authentication is not configured.</strong>
      <span>Set the OIDC variables in <code>apps/web/.env</code> to enable sign-in.</span>
    </div>
  {/if}
  {#if data.authError}
    <p class="error" role="alert">Sign-in was not completed ({data.authError}). Please try again.</p>
  {/if}
</section>

<section class="grid" aria-label="Workspace status">
  <article class="card">
    <span class="card-icon" aria-hidden="true">◈</span>
    <h2>Library</h2>
    <p>Upload and organize source material with page-level provenance.</p>
    <span class="coming">Coming next</span>
  </article>
  <article class="card">
    <span class="card-icon" aria-hidden="true">⌁</span>
    <h2>Study plan</h2>
    <p>Turn your exam date into focused, adaptive study sessions.</p>
    <span class="coming">Coming next</span>
  </article>
  <article class="card">
    <span class="card-icon" aria-hidden="true">✓</span>
    <h2>Assessment</h2>
    <p>Practice grounded SBA, image cases, and viva with citations.</p>
    <span class="coming">Coming next</span>
  </article>
</section>

<section class="status-panel">
  <div>
    <p class="eyebrow">System status</p>
    <h2>Ready when you are.</h2>
  </div>
  <div class="status-list">
    <span><i class:ok={data.apiStatus === 'ready'}></i>API {data.apiStatus}</span>
    <span><i class="ok"></i>Web shell online</span>
    <a href="/api/health">View health JSON →</a>
  </div>
</section>
