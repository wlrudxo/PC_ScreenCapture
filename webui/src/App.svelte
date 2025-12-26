<script>
  import Router from 'svelte-spa-router';
  import Layout from './lib/components/Layout.svelte';

  import Dashboard from './pages/Dashboard.svelte';
  import Timeline from './pages/Timeline.svelte';
  import TagManagement from './pages/TagManagement.svelte';
  import Notification from './pages/Notification.svelte';
  import Focus from './pages/Focus.svelte';
  import Settings from './pages/Settings.svelte';

  const routes = {
    '/': Dashboard,
    '/timeline': Timeline,
    '/tags': TagManagement,
    '/notification': Notification,
    '/focus': Focus,
    '/settings': Settings
  };
</script>

<Layout>
  <Router {routes} />
</Layout>
