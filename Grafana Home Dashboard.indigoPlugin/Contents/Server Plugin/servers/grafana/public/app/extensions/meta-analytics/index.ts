import { registerEchoBackend, featureEnabled, config } from '@grafana/runtime';
import { contextSrv } from 'app/core/services/context_srv';

import { initAnalyticsDrawer } from './AnalyticsDrawer/AnalyticsDashNav';
import { MetaAnalyticsBackend } from './MetaAnalyticsBackend';
import { initPresenceIndicators } from './PresenceIndicators';

export const initMetaAnalytics = () => {
  if (featureEnabled('analytics')) {
    registerEchoBackend(new MetaAnalyticsBackend({ url: '/api/ma/events' }));

    const user = contextSrv.user;
    if (user.isSignedIn) {
      initPresenceIndicators();
      initAnalyticsDrawer();
    }
  } else if (config.featureToggles.featureHighlights) {
    initAnalyticsDrawer();
  }
};
